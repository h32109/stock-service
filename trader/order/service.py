import typing as t
import uuid
from decimal import Decimal
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError

from trader.exceptions import (
    InvalidOrderError,
    InsufficientBalanceError,
    InsufficientStockError,
    InvalidStockError,
    OrderProcessingError
)
from trader.service import ServiceBase, Service
from trader.globals import sql
from trader.stock.model import Stock, StockPrice
from trader.order.model import (
    Order,
    OrderStatus,
    OrderType,
    OrderHistory,
    Transaction,
)

from trader.user.model import User
from trader.portfolio.model import Portfolio

from trader.order.schema import (
    OrderCreateRequest,
    OrderResponse,
    OrderHistoryResponse,
    TransactionResponse,
    OrderDetailResponse,
    OrderUpdateRequest
)

from trader.globals import transaction


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
            # 포트폴리오 조회
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

                # 주문 상태 업데이트
                order.status = OrderStatus.PENDING

                # 주문 히스토리 업데이트
                order_history = OrderHistory(
                    order_id=order_id,
                    previous_status=OrderStatus.INITIAL,
                    current_status=OrderStatus.PENDING,
                    note="Processing buy order"
                )
                sql.session.add(order_history)

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
                note="Processing sell order"
            )
            sql.session.add(order_history)

            # message cue
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
        except Exception as e:
            raise OrderProcessingError(
                "Error creating sell order",
                {"error": str(e)}
            )

    async def get_order(self, order_id: str, user_id: str = None) -> OrderDetailResponse:
        try:
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

            # 주문 히스토리 조회
            history_query = select(OrderHistory).filter(
                OrderHistory.order_id == order_id
            ).order_by(OrderHistory.created_dt)

            history_result = await sql.session.execute(history_query)
            history_data = history_result.scalars().all()

            # 주문 거래 내역 조회
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

            query = query.order_by(Order.created_dt.desc())

            # 총 개수 쿼리
            count_query = select(func.count()).select_from(query.subquery())
            count_result = await sql.session.execute(count_query)
            total_count = count_result.scalar_one()

            # 페이지네이션 적용
            offset = (page - 1) * size
            query = query.offset(offset).limit(size)

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

            # 응답 생성
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
                    elif additional_amount < 0:
                        # 금액이 감소한 경우 잔액 환불
                        user_query = select(User).filter(User.id == user_id)
                        user_result = await sql.session.execute(user_query)
                        user = user_result.scalars().first()

                        if user:
                            user.balance -= additional_amount  # 음수이므로 빼기로 처리

                # 매도 주문인 경우 보유량 확인
                elif order.order_type == OrderType.SELL and request.quantity is not None and request.quantity > old_quantity:
                    # 추가 필요 수량
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

                    # 매도 보류 수량 업데이트
                    portfolio.hold_quantity += additional_quantity

                # 주문 정보 업데이트
                order.price = Decimal(str(new_price))
                order.quantity = new_quantity
                order.total_amount = new_total

                # 주문 히스토리 생성
                order_history = OrderHistory(
                    order_id=order_id,
                    previous_status=order.status,
                    current_status=order.status,  # 상태는 변경 없음
                    note=f"Order updated: price={new_price}, quantity={new_quantity}"
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

            return order_response

        except (InvalidOrderError, InsufficientBalanceError, InsufficientStockError) as e:
            raise e
        except SQLAlchemyError as e:
            raise OrderProcessingError(
                "Database error while updating order",
                {"order_id": order_id, "error": str(e)}
            )

    async def send_to_order_queue(self, order_id: str):
        pass

    @transaction
    async def process_order(self, order_id: str) -> OrderResponse:
        try:
            # 주문 정보 조회
            query = select(Order, Stock).join(Stock, Order.stock_id == Stock.id).filter(Order.id == order_id)
            result = await sql.session.execute(query)
            order_data = result.first()

            if not order_data:
                raise InvalidOrderError(
                    "Order not found",
                    {"order_id": order_id}
                )

            order, stock = order_data

            # 처리 가능한 상태인지 확인
            if order.status not in [OrderStatus.PENDING, OrderStatus.RETRYING]:
                raise InvalidOrderError(
                    "Order is not in a processable state",
                    {"order_id": order_id, "current_status": order.status.value}
                )

            # 현재 주식 가격 조회
            price_query = select(StockPrice).filter(StockPrice.stock_id == order.stock_id)
            price_result = await sql.session.execute(price_query)
            price_data = price_result.scalars().first()

            if not price_data:
                # 가격 정보가 없는 경우 실패 처리
                order.status = OrderStatus.FAILED
                order.retry_count += 1

                # 주문 히스토리 생성
                order_history = OrderHistory(
                    order_id=order_id,
                    previous_status=OrderStatus.PENDING if order.retry_count == 1 else OrderStatus.RETRYING,
                    current_status=OrderStatus.FAILED,
                    note=f"Failed to process order: price information not available"
                )
                sql.session.add(order_history)

                # 최대 재시도 횟수 초과 시 취소 처리
                if order.retry_count >= 3:
                    await self.cancel_order(order_id, order.user_id)

            else:
                # 시장 가격과 주문 가격 비교
                current_price = price_data.current_price

                # 매수 주문: 주문 가격이 현재 가격보다 높거나 같으면 체결
                # 매도 주문: 주문 가격이 현재 가격보다 낮거나 같으면 체결
                order_executed = False

                if (order.order_type == OrderType.BUY and order.price >= current_price) or \
                        (order.order_type == OrderType.SELL and order.price <= current_price):
                    # 주문 체결 처리
                    order_executed = True

                    # 체결 수량 (현재는 전체 수량 체결로 가정)
                    executed_quantity = order.quantity - order.filled_quantity
                    execution_price = current_price
                    execution_amount = execution_price * executed_quantity

                    # 거래 내역 생성
                    transaction = Transaction(
                        order_id=order_id,
                        user_id=order.user_id,
                        stock_id=order.stock_id,
                        transaction_type=order.order_type,
                        price=execution_price,
                        quantity=executed_quantity,
                        amount=execution_amount,
                        is_complete=True
                    )
                    sql.session.add(transaction)

                    # 포트폴리오 업데이트
                    portfolio_query = select(Portfolio).filter(
                        Portfolio.user_id == order.user_id,
                        Portfolio.stock_id == order.stock_id
                    )
                    portfolio_result = await sql.session.execute(portfolio_query)
                    portfolio = portfolio_result.scalars().first()

                    if order.order_type == OrderType.BUY:
                        # 매수: 포트폴리오에 주식 추가
                        if not portfolio:
                            # 최초 매수인 경우 포트폴리오 생성
                            portfolio = Portfolio(
                                user_id=order.user_id,
                                stock_id=order.stock_id,
                                quantity=executed_quantity,
                                avg_purchase_price=execution_price,
                                total_purchase_amount=execution_amount,
                                hold_quantity=0
                            )
                            sql.session.add(portfolio)
                        else:
                            # 기존 보유한 경우 평균 매수가 계산 및 수량 증가
                            total_quantity = portfolio.quantity + executed_quantity
                            total_amount = portfolio.total_purchase_amount + execution_amount
                            portfolio.quantity = total_quantity
                            portfolio.total_purchase_amount = total_amount
                            portfolio.avg_purchase_price = total_amount / total_quantity

                    elif order.order_type == OrderType.SELL:
                        # 매도: 포트폴리오에서 주식 차감 및 매도 보류 해제
                        if portfolio:
                            portfolio.quantity -= executed_quantity
                            portfolio.hold_quantity -= executed_quantity

                            # 매도 대금 사용자 계좌에 입금
                            user_query = select(User).filter(User.id == order.user_id)
                            user_result = await sql.session.execute(user_query)
                            user = user_result.scalars().first()

                            if user:
                                user.balance += execution_amount

                    # 주문 정보 업데이트
                    order.filled_quantity += executed_quantity

                    # 완전 체결 여부 확인
                    if order.filled_quantity >= order.quantity:
                        order.status = OrderStatus.SUCCESS

                        # 주문 히스토리 생성
                        order_history = OrderHistory(
                            order_id=order_id,
                            previous_status=order.status,
                            current_status=OrderStatus.SUCCESS,
                            note=f"Order fully executed at price {float(execution_price)}"
                        )
                        sql.session.add(order_history)

                if not order_executed:
                    # 체결 실패 시 재시도 처리
                    order.retry_count += 1

                    if order.retry_count >= 3:
                        # 최대 재시도 횟수 초과 시 취소 처리
                        await self.cancel_order(order_id, order.user_id)
                    else:
                        # 재시도 상태로 변경
                        order.status = OrderStatus.RETRYING

                        # 주문 히스토리 생성
                        order_history = OrderHistory(
                            order_id=order_id,
                            previous_status=OrderStatus.PENDING if order.retry_count == 1 else OrderStatus.RETRYING,
                            current_status=OrderStatus.RETRYING,
                            note=f"Retry {order.retry_count}: Order price {float(order.price)} does not match market price {float(current_price)}"
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

            return order_response

        except InvalidOrderError as e:
            raise e
        except SQLAlchemyError as e:
            raise OrderProcessingError(
                "Database error while processing order",
                {"order_id": order_id, "error": str(e)}
            )


order_service = Service.add_service(OrderService)