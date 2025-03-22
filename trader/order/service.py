import typing as t
import uuid
from decimal import Decimal
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError
from aiokafka.errors import KafkaError

from trader.exceptions import (
    InvalidOrderError,
    InsufficientBalanceError,
    InsufficientStockError,
    InvalidStockError,
    OrderProcessingError,
    MessageQueueError
)
from trader.service import ServiceBase, Service
from trader.globals import sql, transaction, producer
from trader.stock.model import Stock, StockPrice
from trader.user.model import User, AccountTransaction, TransactionType
from trader.order.model import (
    Order,
    OrderStatus,
    OrderType,
    OrderHistory,
    Transaction
)

from trader.portfolio.model import Portfolio

from trader.order.schema import (
    OrderCreateRequest,
    OrderResponse,
    OrderHistoryResponse,
    TransactionResponse,
    OrderDetailResponse,
    OrderUpdateRequest
)


class OrderServiceBase(ServiceBase):
    config: t.Any

    async def configuration(self, config):
        self.config = config


class OrderService(OrderServiceBase):

    async def check_stock_validity(self, stock_id: str) -> t.Tuple[Stock, StockPrice]:
        try:
            stmt = select(Stock, StockPrice) \
                .join(StockPrice, Stock.id == StockPrice.stock_id) \
                .filter(Stock.id == stock_id, Stock.is_active == True)

            result = await sql.session.execute(stmt)
            result_row = result.first()

            if not result_row:
                raise InvalidStockError(
                    "Stock not found or not active",
                    {"stock_id": stock_id}
                )

            return result_row
        except SQLAlchemyError as e:
            raise OrderProcessingError(
                "Database error while checking stock",
                {"stock_id": stock_id, "error": str(e)}
            )

    async def check_user_balance(self, user_id: str, required_amount: Decimal) -> User:
        try:
            stmt = select(User).filter(User.id == user_id)
            result = await sql.session.execute(stmt)
            user = result.scalars().first()

            if not user:
                raise InvalidOrderError(
                    "User not found",
                    {"user_id": user_id}
                )

            # 잔액 확인
            if user.balance < required_amount:
                raise InsufficientBalanceError(
                    "Insufficient balance for order",
                    {
                        "user_id": user_id,
                        "current_balance": float(user.balance),
                        "required_amount": float(required_amount)
                    }
                )

            return user
        except SQLAlchemyError as e:
            raise OrderProcessingError(
                "Database error while checking balance",
                {"user_id": user_id, "error": str(e)}
            )

    async def check_user_holdings(self, user_id: str, stock_id: str, quantity: int) -> Portfolio:
        try:
            stmt = select(Portfolio).filter(
                Portfolio.user_id == user_id,
                Portfolio.stock_id == stock_id
            )
            result = await sql.session.execute(stmt)
            portfolio = result.scalars().first()

            if not portfolio:
                raise InsufficientStockError(
                    "Stock not found in portfolio",
                    {"user_id": user_id, "stock_id": stock_id}
                )

            # 매도 가능 수량 확인 (보유 수량 - 매도 보류 수량)
            available_quantity = portfolio.quantity - portfolio.hold_quantity

            if available_quantity < quantity:
                raise InsufficientStockError(
                    "Insufficient stock quantity for sell order",
                    {
                        "user_id": user_id,
                        "stock_id": stock_id,
                        "available_quantity": available_quantity,
                        "requested_quantity": quantity
                    }
                )

            return portfolio
        except SQLAlchemyError as e:
            raise OrderProcessingError(
                "Database error while checking holdings",
                {"user_id": user_id, "stock_id": stock_id, "error": str(e)}
            )

    @transaction
    async def create_buy_order(self, user_id: str, request: OrderCreateRequest) -> OrderResponse:
        try:
            # 주식 유효성 확인
            stock, price = await self.check_stock_validity(request.stock_id)

            # 주문 금액 계산
            order_amount = Decimal(str(request.price)) * request.quantity

            # 사용자 잔액 확인
            user = await self.check_user_balance(user_id, order_amount)

            order_id = str(uuid.uuid4())

            # 주문 생성
            order = Order(
                id=order_id,
                user_id=user_id,
                stock_id=request.stock_id,
                order_type=OrderType.BUY,
                status=OrderStatus.INITIAL,
                price=request.price,
                quantity=request.quantity,
                filled_quantity=0,
                total_amount=order_amount,
                retry_count=0
            )
            sql.session.add(order)

            # 주문 히스토리 생성
            order_history = OrderHistory(
                order_id=order_id,
                previous_status=None,
                current_status=OrderStatus.INITIAL,
                note="Buy order created"
            )
            sql.session.add(order_history)

            # 사용자 잔액 차감
            user.balance -= order_amount

            # 계좌 트랜잭션 기록
            account_transaction = AccountTransaction(
                user_id=user_id,
                type=TransactionType.ORDER_PAYMENT,
                amount=-float(order_amount),
                balance_after=user.balance,
                description=f"Payment for buy order {order_id} ({stock.company_name})",
                related_order_id=order_id
            )
            sql.session.add(account_transaction)

            # 주문 상태 업데이트
            order.status = OrderStatus.PENDING

            # 주문 히스토리 업데이트
            order_history = OrderHistory(
                order_id=order_id,
                previous_status=OrderStatus.INITIAL,
                current_status=OrderStatus.PENDING,
                note="Buy order queued for processing"
            )
            sql.session.add(order_history)

            # Kafka로 주문 처리 요청 보내기
            await self.send_to_order_queue(order_id)

            order_response = OrderResponse(
                id=order.id,
                user_id=order.user_id,
                stock_id=order.stock_id,
                stock_name=stock.company_name,
                order_type=order.order_type.value,
                status=order.status.value,
                price=float(order.price),
                quantity=order.quantity,
                filled_quantity=order.filled_quantity,
                total_amount=float(order.total_amount),
                created_at=order.created_dt.isoformat()
            )

            return order_response

        except (InvalidStockError, InsufficientBalanceError) as e:
            raise e
        except SQLAlchemyError as e:
            raise OrderProcessingError(
                "Database error while creating buy order",
                {"error": str(e)}
            )
        except MessageQueueError as e:
            raise OrderProcessingError(
                "Failed to queue buy order for processing",
                {"error": str(e)}
            )
        except Exception as e:
            raise OrderProcessingError(
                "Error creating buy order",
                {"error": str(e)}
            )

    @transaction
    async def create_sell_order(self, user_id: str, request: OrderCreateRequest) -> OrderResponse:
        try:
            # 주식 유효성 확인
            stock, price = await self.check_stock_validity(request.stock_id)

            # 주문 금액 계산
            order_amount = Decimal(str(request.price)) * request.quantity

            # 주식 보유량 확인
            portfolio = await self.check_user_holdings(user_id, request.stock_id, request.quantity)

            order_id = str(uuid.uuid4())

            # 주문 생성
            order = Order(
                id=order_id,
                user_id=user_id,
                stock_id=request.stock_id,
                order_type=OrderType.SELL,
                status=OrderStatus.INITIAL,
                price=request.price,
                quantity=request.quantity,
                filled_quantity=0,
                total_amount=order_amount,
                retry_count=0
            )
            sql.session.add(order)

            # 주문 히스토리 생성
            order_history = OrderHistory(
                order_id=order_id,
                previous_status=None,
                current_status=OrderStatus.INITIAL,
                note="Sell order created"
            )
            sql.session.add(order_history)

            # 매도 보류 수량 설정
            portfolio.hold_quantity += request.quantity

            # 주문 상태 업데이트
            order.status = OrderStatus.PENDING

            # 주문 히스토리 업데이트
            order_history = OrderHistory(
                order_id=order_id,
                previous_status=OrderStatus.INITIAL,
                current_status=OrderStatus.PENDING,
                note="Sell order queued for processing"
            )
            sql.session.add(order_history)

            # Kafka로 주문 처리 요청 보내기
            await self.send_to_order_queue(order_id)

            order_response = OrderResponse(
                id=order.id,
                user_id=order.user_id,
                stock_id=order.stock_id,
                stock_name=stock.company_name,
                order_type=order.order_type.value,
                status=order.status.value,
                price=float(order.price),
                quantity=order.quantity,
                filled_quantity=order.filled_quantity,
                total_amount=float(order.total_amount),
                created_at=order.created_dt.isoformat()
            )

            return order_response

        except (InvalidStockError, InsufficientStockError) as e:
            raise e
        except SQLAlchemyError as e:
            raise OrderProcessingError(
                "Database error while creating sell order",
                {"error": str(e)}
            )
        except MessageQueueError as e:
            raise OrderProcessingError(
                "Failed to queue sell order for processing",
                {"error": str(e)}
            )
        except Exception as e:
            raise OrderProcessingError(
                "Error creating sell order",
                {"error": str(e)}
            )

    async def get_order(self, order_id: str, user_id: str = None) -> OrderDetailResponse:
        try:
            # 주문 기본 정보 조회
            query = select(Order, Stock).join(Stock, Order.stock_id == Stock.id).filter(Order.id == order_id)

            if user_id:
                query = query.filter(Order.user_id == user_id)

            result = await sql.session.execute(query)
            order_data = result.first()

            if not order_data:
                raise InvalidOrderError(
                    "Order not found",
                    {"order_id": order_id}
                )

            order, stock = order_data

            history_query = select(OrderHistory).filter(
                OrderHistory.order_id == order_id
            ).order_by(OrderHistory.created_dt)

            history_result = await sql.session.execute(history_query)
            history_data = history_result.scalars().all()

            transaction_query = select(Transaction).filter(
                Transaction.order_id == order_id
            ).order_by(Transaction.transaction_dt)

            transaction_result = await sql.session.execute(transaction_query)
            transaction_data = transaction_result.scalars().all()

            history_responses = [
                OrderHistoryResponse(
                    previous_status=h.previous_status.value if h.previous_status else None,
                    current_status=h.current_status.value,
                    note=h.note,
                    created_at=h.created_dt.isoformat()
                ) for h in history_data
            ]

            transaction_responses = [
                TransactionResponse(
                    id=t.id,
                    transaction_type=t.transaction_type.value,
                    price=float(t.price),
                    quantity=t.quantity,
                    amount=float(t.amount),
                    is_complete=t.is_complete,
                    transaction_at=t.transaction_dt.isoformat()
                ) for t in transaction_data
            ]

            detail_response = OrderDetailResponse(
                id=order.id,
                user_id=order.user_id,
                stock_id=order.stock_id,
                stock_name=stock.company_name,
                order_type=order.order_type.value,
                status=order.status.value,
                price=float(order.price),
                quantity=order.quantity,
                filled_quantity=order.filled_quantity,
                total_amount=float(order.total_amount),
                retry_count=order.retry_count,
                created_at=order.created_dt.isoformat(),
                updated_at=order.updated_dt.isoformat(),
                history=history_responses,
                transactions=transaction_responses
            )

            return detail_response

        except InvalidOrderError as e:
            raise e
        except SQLAlchemyError as e:
            raise OrderProcessingError(
                "Database error while fetching order",
                {"order_id": order_id, "error": str(e)}
            )

    async def get_user_orders(
            self,
            user_id: str,
            order_type: str = None,
            status: str = None,
            start_date: datetime = None,
            end_date: datetime = None,
            page: int = 1,
            size: int = 20
    ) -> t.Tuple[t.List[OrderResponse], int]:
        try:
            query = select(Order, Stock).join(Stock, Order.stock_id == Stock.id).filter(Order.user_id == user_id)

            if order_type:
                query = query.filter(Order.order_type == OrderType[order_type.upper()])

            if status:
                query = query.filter(Order.status == OrderStatus[status.upper()])

            if start_date:
                query = query.filter(Order.created_dt >= start_date)

            if end_date:
                query = query.filter(Order.created_dt <= end_date)

            # 정렬 (최신순)
            query = query.order_by(Order.created_dt.desc())

            # 총 개수 쿼리
            count_query = select(func.count()).select_from(query.subquery())
            count_result = await sql.session.execute(count_query)
            total_count = count_result.scalar_one()

            # 페이지네이션 적용
            offset = (page - 1) * size
            query = query.offset(offset).limit(size)

            # 쿼리 실행
            result = await sql.session.execute(query)
            orders_data = result.all()

            order_responses = [
                OrderResponse(
                    id=order.id,
                    user_id=order.user_id,
                    stock_id=order.stock_id,
                    stock_name=stock.company_name,
                    order_type=order.order_type.value,
                    status=order.status.value,
                    price=float(order.price),
                    quantity=order.quantity,
                    filled_quantity=order.filled_quantity,
                    total_amount=float(order.total_amount),
                    created_at=order.created_dt.isoformat()
                ) for order, stock in orders_data
            ]

            return order_responses, total_count

        except SQLAlchemyError as e:
            raise OrderProcessingError(
                "Database error while fetching user orders",
                {"user_id": user_id, "error": str(e)}
            )

    @transaction
    async def cancel_order(self, order_id: str, user_id: str) -> OrderResponse:
        try:
            query = select(Order, Stock).join(Stock, Order.stock_id == Stock.id).filter(
                Order.id == order_id,
                Order.user_id == user_id
            )

            result = await sql.session.execute(query)
            order_data = result.first()

            if not order_data:
                raise InvalidOrderError(
                    "Order not found or not owned by user",
                    {"order_id": order_id, "user_id": user_id}
                )

            order, stock = order_data

            # 취소 가능한 상태인지 확인
            cancelable_statuses = [OrderStatus.INITIAL, OrderStatus.PENDING, OrderStatus.FAILED,
                                   OrderStatus.RETRYING]

            if order.status not in cancelable_statuses:
                raise InvalidOrderError(
                    "Order cannot be cancelled in its current state",
                    {"order_id": order_id, "current_status": order.status.value}
                )

            # 이전 상태 저장
            previous_status = order.status

            # 주문 취소 처리
            if order.order_type == OrderType.BUY:
                # 매수 주문 취소: 잔액 환불
                # 미체결 수량에 대한 금액만 환불
                refund_quantity = order.quantity - order.filled_quantity
                refund_amount = Decimal(str(order.price)) * refund_quantity

                # 사용자 잔액 업데이트
                user_query = select(User).filter(User.id == user_id)
                user_result = await sql.session.execute(user_query)
                user = user_result.scalars().first()

                if user:
                    user.balance += refund_amount

                    # 환불 트랜잭션 기록
                    refund_transaction = AccountTransaction(
                        user_id=user_id,
                        type=TransactionType.ORDER_REFUND,
                        amount=float(refund_amount),
                        balance_after=user.balance,
                        description=f"Refund for cancelled buy order {order_id} ({stock.company_name})",
                        related_order_id=order_id
                    )
                    sql.session.add(refund_transaction)

            elif order.order_type == OrderType.SELL:
                # 매도 주문 취소: 매도 보류 해제
                # 미체결 수량만큼 보류 해제
                release_quantity = order.quantity - order.filled_quantity

                # 포트폴리오 업데이트
                portfolio_query = select(Portfolio).filter(
                    Portfolio.user_id == user_id,
                    Portfolio.stock_id == order.stock_id
                )
                portfolio_result = await sql.session.execute(portfolio_query)
                portfolio = portfolio_result.scalars().first()

                if portfolio and portfolio.hold_quantity >= release_quantity:
                    portfolio.hold_quantity -= release_quantity

            # 주문 상태 업데이트
            order.status = OrderStatus.CANCELLED

            # 주문 히스토리 생성
            order_history = OrderHistory(
                order_id=order_id,
                previous_status=previous_status,
                current_status=OrderStatus.CANCELLED,
                note=f"Order cancelled by user"
            )
            sql.session.add(order_history)

            order_response = OrderResponse(
                id=order.id,
                user_id=order.user_id,
                stock_id=order.stock_id,
                stock_name=stock.company_name,
                order_type=order.order_type.value,
                status=order.status.value,
                price=float(order.price),
                quantity=order.quantity,
                filled_quantity=order.filled_quantity,
                total_amount=float(order.total_amount),
                created_at=order.created_dt.isoformat()
            )

            # Kafka에 취소 이벤트 발행
            await self.send_cancel_event(order_id)

            return order_response

        except InvalidOrderError as e:
            raise e
        except SQLAlchemyError as e:
            raise OrderProcessingError(
                "Database error while cancelling order",
                {"order_id": order_id, "error": str(e)}
            )

    @transaction
    async def update_order(self, order_id: str, user_id: str, request: OrderUpdateRequest) -> OrderResponse:
        try:
            query = select(Order, Stock).join(Stock, Order.stock_id == Stock.id).filter(
                Order.id == order_id,
                Order.user_id == user_id
            )

            result = await sql.session.execute(query)
            order_data = result.first()

            if not order_data:
                raise InvalidOrderError(
                    "Order not found or not owned by user",
                    {"order_id": order_id, "user_id": user_id}
                )

            order, stock = order_data

            # 수정 가능한 상태인지 확인
            updatable_statuses = [OrderStatus.INITIAL, OrderStatus.PENDING, OrderStatus.FAILED,
                                  OrderStatus.RETRYING]

            if order.status not in updatable_statuses:
                raise InvalidOrderError(
                    "Order cannot be updated in its current state",
                    {"order_id": order_id, "current_status": order.status.value}
                )

            # 이미 체결된 수량이 있는지 확인
            if order.filled_quantity > 0:
                raise InvalidOrderError(
                    "Order with partial fills cannot be updated",
                    {"order_id": order_id, "filled_quantity": order.filled_quantity}
                )

            # 가격 또는 수량 변경 처리
            if request.price is not None or request.quantity is not None:
                # 현재 주문 정보 저장
                old_price = order.price
                old_quantity = order.quantity
                old_total = order.total_amount

                # 새 값 설정
                new_price = request.price if request.price is not None else float(old_price)
                new_quantity = request.quantity if request.quantity is not None else old_quantity
                new_total = Decimal(str(new_price)) * new_quantity

                # 매수 주문인 경우 잔액 확인
                if order.order_type == OrderType.BUY:
                    # 추가 필요 금액 계산 (새 총액 - 기존 총액)
                    additional_amount = new_total - old_total

                    if additional_amount > 0:
                        # 사용자 잔액 확인
                        user_query = select(User).filter(User.id == user_id)
                        user_result = await sql.session.execute(user_query)
                        user = user_result.scalars().first()

                        if not user or user.balance < additional_amount:
                            raise InsufficientBalanceError(
                                "Insufficient balance for order update",
                                {
                                    "user_id": user_id,
                                    "current_balance": float(user.balance) if user else 0,
                                    "additional_amount": float(additional_amount)
                                }
                            )

                        # 잔액 차감
                        user.balance -= additional_amount

                        # 추가 결제 트랜잭션 기록
                        additional_payment = AccountTransaction(
                            user_id=user_id,
                            type=TransactionType.ORDER_PAYMENT,
                            amount=-float(additional_amount),
                            balance_after=user.balance,
                            description=f"Additional payment for updated buy order {order_id} ({stock.company_name})",
                            related_order_id=order_id
                        )
                        sql.session.add(additional_payment)

                    elif additional_amount < 0:
                        # 금액이 감소한 경우 잔액 환불
                        user_query = select(User).filter(User.id == user_id)
                        user_result = await sql.session.execute(user_query)
                        user = user_result.scalars().first()

                        if user:
                            refund_amount = abs(additional_amount)
                            user.balance += refund_amount

                            # 환불 트랜잭션 기록
                            refund_transaction = AccountTransaction(
                                user_id=user_id,
                                type=TransactionType.ORDER_REFUND,
                                amount=float(refund_amount),
                                balance_after=user.balance,
                                description=f"Partial refund for updated buy order {order_id} ({stock.company_name})",
                                related_order_id=order_id
                            )
                            sql.session.add(refund_transaction)

                # 매도 주문인 경우 보유량 확인
                elif order.order_type == OrderType.SELL:
                    if request.quantity is not None:
                        if request.quantity > old_quantity:
                            # 수량 증가: 추가 필요 수량
                            additional_quantity = request.quantity - old_quantity

                            # 포트폴리오 확인
                            portfolio_query = select(Portfolio).filter(
                                Portfolio.user_id == user_id,
                                Portfolio.stock_id == order.stock_id
                            )
                            portfolio_result = await sql.session.execute(portfolio_query)
                            portfolio = portfolio_result.scalars().first()

                            if not portfolio:
                                raise InsufficientStockError(
                                    "Stock not found in portfolio",
                                    {"user_id": user_id, "stock_id": order.stock_id}
                                )

                            # 가용 수량 계산 (보유 수량 - 매도 보류 수량 + 현재 주문의 매도 보류 수량)
                            available_quantity = portfolio.quantity - portfolio.hold_quantity + old_quantity

                            if available_quantity < request.quantity:
                                raise InsufficientStockError(
                                    "Insufficient stock quantity for sell order update",
                                    {
                                        "user_id": user_id,
                                        "stock_id": order.stock_id,
                                        "available_quantity": available_quantity,
                                        "requested_quantity": request.quantity
                                    }
                                )

                            # 매도 보류 수량 업데이트 (증가)
                            portfolio.hold_quantity += additional_quantity

                        elif request.quantity < old_quantity:
                            # 수량 감소: 해제할 보류 수량
                            release_quantity = old_quantity - request.quantity

                            portfolio_query = select(Portfolio).filter(
                                Portfolio.user_id == user_id,
                                Portfolio.stock_id == order.stock_id
                            )
                            portfolio_result = await sql.session.execute(portfolio_query)
                            portfolio = portfolio_result.scalars().first()

                            if portfolio and portfolio.hold_quantity >= release_quantity:
                                # 매도 보류 수량 업데이트 (감소)
                                portfolio.hold_quantity -= release_quantity

                # 주문 정보 업데이트
                order.price = Decimal(str(new_price))
                order.quantity = new_quantity
                order.total_amount = new_total

                # 주문 히스토리 생성
                order_history = OrderHistory(
                    order_id=order_id,
                    previous_status=order.status,
                    current_status=order.status,
                    note=f"Order updated: price={new_price}, quantity={new_quantity}"
                )
                sql.session.add(order_history)

                # Kafka에 주문 업데이트 이벤트 발행
                await self.send_update_event(order_id)

            order_response = OrderResponse(
                id=order.id,
                user_id=order.user_id,
                stock_id=order.stock_id,
                stock_name=stock.company_name,
                order_type=order.order_type.value,
                status=order.status.value,
                price=float(order.price),
                quantity=order.quantity,
                filled_quantity=order.filled_quantity,
                total_amount=float(order.total_amount),
                created_at=order.created_dt.isoformat()
            )

            return order_response

        except (InvalidOrderError, InsufficientBalanceError, InsufficientStockError) as e:
            raise e
        except SQLAlchemyError as e:
            raise OrderProcessingError(
                "Database error while updating order",
                {"order_id": order_id, "error": str(e)}
            )
        except MessageQueueError as e:
            raise OrderProcessingError(
                "Failed to send order update event",
                {"order_id": order_id, "error": str(e)}
            )

    async def send_to_order_queue(self, order_id: str) -> bool:
        try:
            message = {
                "order_id": order_id,
                "event_type": "order.process",
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": str(uuid.uuid4())
            }

            topic = "orders.processing.requests"

            await producer.send_and_wait(
                topic=topic,
                key=order_id,
                data=[message],
                headers=[
                    ("source", b"order_service"),
                    ("event_type", b"order.process")
                ]
            )

            return True

        except KafkaError as e:
            raise MessageQueueError(
                "Failed to send order processing request to queue",
                {"order_id": order_id, "error": str(e)}
            )
        except Exception as e:
            raise MessageQueueError(
                "Unexpected error while sending to order queue",
                {"order_id": order_id, "error": str(e)}
            )

    async def send_cancel_event(self, order_id: str) -> bool:
        try:
            message = {
                "order_id": order_id,
                "event_type": "order.cancel",
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": str(uuid.uuid4())
            }
            topic = "orders.events"

            await producer.send_and_wait(
                topic=topic,
                key=order_id,
                data=[message],
                headers=[
                    ("source", b"order_service"),
                    ("event_type", b"order.cancel")
                ]
            )

            return True

        except Exception as e:
            return False

    async def send_update_event(self, order_id: str) -> bool:
        try:
            message = {
                "order_id": order_id,
                "event_type": "order.update",
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": str(uuid.uuid4())
            }

            topic = "orders.events"

            await producer.send_and_wait(
                topic=topic,
                key=order_id,
                data=[message],
                headers=[
                    ("source", b"order_service"),
                    ("event_type", b"order.update")
                ]
            )

            return True

        except KafkaError as e:
            raise MessageQueueError(
                "Failed to send order update event to queue",
                {"order_id": order_id, "error": str(e)}
            )
        except Exception as e:
            raise MessageQueueError(
                "Unexpected error while sending update event",
                {"order_id": order_id, "error": str(e)}
            )


order_service = Service.add_service(OrderService)
