from sqlalchemy import (
    Column,
    String,
    ForeignKey,
    Enum,
    Boolean,
    DateTime,
    Numeric,
    BigInteger,
    Integer,
    Index,
    Text,
    CheckConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
import uuid

from trader.globals import Base


# TODO: User 테이블과 연결(Auth 생기고 나서)

class OrderStatus(enum.Enum):
    INITIAL = "initial"  # 초기 상태
    PENDING = "pending"  # 주문 처리 중
    SUCCESS = "success"  # 주문 성공
    FAILED = "failed"  # 주문 실패
    RETRYING = "retrying"  # 재시도 중
    CANCELLED = "cancelled"  # 주문 취소


class OrderType(enum.Enum):
    BUY = "buy"
    SELL = "sell"


class Order(Base):
    __tablename__ = 'orders'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    stock_id = Column(String(10), ForeignKey('stocks.id'), nullable=False)
    order_type = Column(Enum(OrderType), nullable=False)
    status = Column(Enum(OrderStatus), nullable=False, default=OrderStatus.INITIAL)
    price = Column(Numeric(16, 2), nullable=False)  # 주문 가격
    quantity = Column(Integer, nullable=False)  # 주문 수량
    filled_quantity = Column(Integer, nullable=False, default=0)  # 체결된 수량
    total_amount = Column(Numeric(24, 2), nullable=False)  # 총 주문 금액 (price * quantity)
    retry_count = Column(Integer, nullable=False, default=0)  # 재시도 횟수
    created_dt = Column(DateTime, nullable=False, server_default=func.now())
    updated_dt = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # user = relationship("User", back_populates="orders")
    stock = relationship("Stock", back_populates="orders")
    order_history = relationship("OrderHistory", back_populates="order")
    transactions = relationship("Transaction", back_populates="order")

    __table_args__ = (
        CheckConstraint('quantity > 0', name='chk_positive_quantity'),
        CheckConstraint('price > 0', name='chk_positive_price'),
        CheckConstraint('total_amount >= 0', name='chk_non_negative_total'),
        CheckConstraint('filled_quantity >= 0 AND filled_quantity <= quantity', name='chk_valid_filled_quantity'),
        Index('ix_orders_user_id', user_id),
        Index('ix_orders_stock_id', stock_id),
        Index('ix_orders_status', status),
        Index('ix_orders_created_dt', created_dt),
    )


class OrderHistory(Base):
    __tablename__ = 'order_history'

    id = Column(BigInteger, primary_key=True)
    order_id = Column(String(36), ForeignKey('orders.id'), nullable=False)
    previous_status = Column(Enum(OrderStatus), nullable=True)  # 이전 상태 (최초 생성시 NULL)
    current_status = Column(Enum(OrderStatus), nullable=False)  # 현재 상태
    note = Column(Text, nullable=True)  # 상태 변경 사유
    created_dt = Column(DateTime, nullable=False, server_default=func.now())

    order = relationship("Order", back_populates="order_history")

    __table_args__ = (
        Index('ix_order_history_order_id', order_id),
        Index('ix_order_history_current_status', current_status),
    )


class Transaction(Base):
    __tablename__ = 'transactions'

    id = Column(BigInteger, primary_key=True)
    order_id = Column(String(36), ForeignKey('orders.id'), nullable=False)
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    stock_id = Column(String(10), ForeignKey('stocks.id'), nullable=False)
    transaction_type = Column(Enum(OrderType), nullable=False)  # 매수/매도
    price = Column(Numeric(16, 2), nullable=False)  # 체결 가격
    quantity = Column(Integer, nullable=False)  # 체결 수량
    amount = Column(Numeric(24, 2), nullable=False)  # 체결 금액 (price * quantity)
    is_complete = Column(Boolean, nullable=False, default=False)  # 주문 완전 체결 여부
    transaction_dt = Column(DateTime, nullable=False, server_default=func.now())
    created_dt = Column(DateTime, nullable=False, server_default=func.now())

    order = relationship("Order", back_populates="transactions")
    # user = relationship("User")
    stock = relationship("Stock")

    __table_args__ = (
        CheckConstraint('quantity > 0', name='chk_positive_tx_quantity'),
        CheckConstraint('price > 0', name='chk_positive_tx_price'),
        CheckConstraint('amount > 0', name='chk_positive_tx_amount'),
        Index('ix_transactions_order_id', order_id),
        Index('ix_transactions_user_id', user_id),
        Index('ix_transactions_stock_id', stock_id),
        Index('ix_transactions_transaction_dt', transaction_dt),
    )
