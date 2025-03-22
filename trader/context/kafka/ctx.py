import asyncio
import json
import typing as t
from decimal import Decimal
from select import select

import aiokafka
from sqlalchemy.exc import SQLAlchemyError

from trader.context.base import Context
from trader.context.kafka.model import Data
from trader.globals import transaction, sql
from trader.order.model import (
    Order,
    OrderStatus,
    OrderHistory,
    OrderType,
    Transaction
)
from trader.portfolio.model import Portfolio
from trader.stock.model import Stock, StockPrice
from trader.user.model import (
    User,
    AccountTransaction,
    TransactionType
)

ENCODING = "utf-8"


class KafkaProducerContext(Context):
    _producer: t.Optional[aiokafka.AIOKafkaProducer]

    def __init__(
            self,
            config,
            producer=None):
        self._producer = producer
        self.config = config

    @classmethod
    def init(
            cls,
            config,
            **kwargs
    ):
        producer = aiokafka.AIOKafkaProducer(
            bootstrap_servers=config.KAFKA.HOSTS,
            value_serializer=lambda m: m.json(ensure_ascii=False).encode(ENCODING),
            client_id="order_service",
            acks="1",
            compression_type="gzip",
            max_request_size=1048576,
            request_timeout_ms=5000,
            retry_backoff_ms=100

        )
        ctx = KafkaProducerContext(
            config=config,
            producer=producer
        )
        ctx.register("producer", ctx)
        return ctx

    async def start(self):
        await self._producer.start()

    async def shutdown(self):
        await self._producer.stop()

    async def send(
            self,
            topic: str,
            data: Data,
            key: t.Optional[str] = None,
            chunk_size: t.Optional[int] = 0,
            headers: t.Optional[t.List[t.Tuple]] = None
    ):
        if headers is None:
            headers = []

        async for chunk in data.chunk(chunk_size=chunk_size):
            await self._producer.send_and_wait(
                topic=topic,
                key=key.encode('utf-8'),
                value=json.dumps(chunk.dict()).encode('utf-8'),
                headers=headers
            )


class KafkaConsumerContext(Context):
    _consumer: t.Optional[aiokafka.AIOKafkaConsumer]
    running: bool = False

    def __init__(
            self,
            config,
            consumer=None):
        self._consumer = consumer
        self.config = config

    @classmethod
    def init(
            cls,
            config,
            **kwargs
    ):
        consumer = aiokafka.AIOKafkaConsumer(
            "orders.processing.requests",
            "orders.events",
            bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
            group_id="order_processor",
            auto_offset_reset="earliest",
            enable_auto_commit=False,
            max_poll_records=100,
            max_poll_interval_ms=300000,
            session_timeout_ms=30000,
            heartbeat_interval_ms=10000,
        )
        ctx = KafkaConsumerContext(
            config=config,
            consumer=consumer
        )
        ctx.register("consumer", ctx)
        return ctx

    async def start(self):
        if self.running:
            return

        await self._consumer.start()
        self.running = True

    async def shutdown(self):
        await self._consumer.stop()

    async def run(self):
        if not self.running:
            await self.start()

        try:
            async for message in self._consumer:
                try:
                    value = json.loads(message.value.decode('utf-8'))

                    topic = message.topic
                    headers = {key: value for key, value in message.headers}
                    event_type = headers.get(b'event_type', b'').decode('utf-8')

                    if topic == "orders.processing.requests":
                        await self.handle_processing_request(value)
                    elif topic == "orders.events":
                        if event_type == "order.cancel":
                            await self.handle_cancel_event(value)
                        elif event_type == "order.update":
                            await self.handle_update_event(value)

                    await self._consumer.commit()

                except json.JSONDecodeError as e:
                    await self._consumer.commit()
                    continue
                except Exception as e:
                    # 커밋하지 않고 재시도하도록 함
                    pass

        except Exception as e:
            if self.running:
                await asyncio.sleep(5)
                await self.run()

    async def handle_processing_request(self, message: dict):
        """주문 처리"""
        order_id = message.get('order_id')
        if not order_id:
            return

        await self.process_order(order_id)

    async def handle_cancel_event(self, message: dict):
        """주문 취소"""
        order_id = message.get('order_id')
        if not order_id:
            return


    async def handle_update_event(self, message: dict):
        """주문 업데이트"""
        order_id = message.get('order_id')
        if not order_id:
            return

        # 업데이트된 주문 정보로 처리 상태 재설정
        await self.reset_order_processing(order_id)

    @transaction
    async def reset_order_processing(self, order_id: str):
            try:
                query = select(Order).filter(Order.id == order_id)
                result = await sql.session.execute(query)
                order = result.scalars().first()

                if not order:
                    return

                # 처리 가능한 상태인 경우만 초기화
                if order.status in [OrderStatus.PENDING, OrderStatus.RETRYING]:
                    # 재시도 횟수 초기화
                    order.retry_count = 0

                    # 처리 상태로 변경
                    order.status = OrderStatus.PENDING

                    # 히스토리 기록
                    history = OrderHistory(
                        order_id=order_id,
                        previous_status=OrderStatus.RETRYING if order.status == OrderStatus.RETRYING else OrderStatus.PENDING,
                        current_status=OrderStatus.PENDING,
                        note="Order processing reset after update"
                    )
                    sql.session.add(history)

            except SQLAlchemyError as e:
                raise

    @transaction
    async def process_order(self, order_id: str):
        try:
            query = select(Order, Stock).join(Stock, Order.stock_id == Stock.id).filter(Order.id == order_id)
            result = await sql.session.execute(query)
            order_data = result.first()

            if not order_data:
                return

            order, stock = order_data

            # 처리 가능한 상태인지 확인
            if order.status not in [OrderStatus.PENDING, OrderStatus.RETRYING]:
                return

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
                    await self.auto_cancel_order(order_id)

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

                                # 매도 수익 트랜잭션 기록
                                sell_transaction = AccountTransaction(
                                    user_id=order.user_id,
                                    type=TransactionType.SELL_INCOME,
                                    amount=float(execution_amount),
                                    balance_after=user.balance,
                                    description=f"Income from sell order {order_id} ({stock.company_name})",
                                    related_order_id=order_id
                                )
                                sql.session.add(sell_transaction)

                    # 주문 정보 업데이트
                    order.filled_quantity += executed_quantity

                    # 완전 체결 여부 확인
                    if order.filled_quantity >= order.quantity:
                        order.status = OrderStatus.SUCCESS

                        # 주문 히스토리 생성
                        order_history = OrderHistory(
                            order_id=order_id,
                            previous_status=OrderStatus.PENDING if order.retry_count == 0 else OrderStatus.RETRYING,
                            current_status=OrderStatus.SUCCESS,
                            note=f"Order fully executed at price {float(execution_price)}"
                        )
                        sql.session.add(order_history)

                if not order_executed:
                    # 체결 실패 시 재시도 처리
                    order.retry_count += 1

                    if order.retry_count >= 3:
                        # 최대 재시도 횟수 초과 시 취소 처리
                        await self.auto_cancel_order(order_id)
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

        except SQLAlchemyError as e:
            raise

    async def auto_cancel_order(self, order_id: str):
        try:
            query = select(Order, Stock).join(Stock, Order.stock_id == Stock.id).filter(Order.id == order_id)
            result = await sql.session.execute(query)
            order_data = result.first()

            if not order_data:
                return

            order, stock = order_data

            # 이전 상태 저장
            previous_status = order.status

            # 주문 취소 처리
            if order.order_type == OrderType.BUY:
                # 매수 주문 취소: 잔액 환불
                # 미체결 수량에 대한 금액만 환불
                refund_quantity = order.quantity - order.filled_quantity
                refund_amount = Decimal(str(order.price)) * refund_quantity

                # 사용자 잔액 업데이트
                user_query = select(User).filter(User.id == order.user_id)
                user_result = await sql.session.execute(user_query)
                user = user_result.scalars().first()

                if user:
                    user.balance += refund_amount

                    # 환불 트랜잭션 기록
                    refund_transaction = AccountTransaction(
                        user_id=order.user_id,
                        type=TransactionType.ORDER_REFUND,
                        amount=float(refund_amount),
                        balance_after=user.balance,
                        description=f"Refund for auto-cancelled buy order {order_id} ({stock.company_name})",
                        related_order_id=order_id
                    )
                    sql.session.add(refund_transaction)

            elif order.order_type == OrderType.SELL:
                # 매도 주문 취소: 매도 보류 해제
                # 미체결 수량만큼 보류 해제
                release_quantity = order.quantity - order.filled_quantity

                # 포트폴리오 업데이트
                portfolio_query = select(Portfolio).filter(
                    Portfolio.user_id == order.user_id,
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
                note=f"Order auto-cancelled after maximum retry attempts"
            )
            sql.session.add(order_history)

            await sql.session.commit()

        except SQLAlchemyError as e:
            await sql.session.rollback()
        except Exception as e:
            await sql.session.rollback()
