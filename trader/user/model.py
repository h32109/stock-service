import enum
from sqlalchemy import (
    Column,
    String,
    ForeignKey,
    Boolean,
    Date,
    DateTime,
    Numeric,
    BigInteger,
    Index,
    Text,
    Enum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from trader.globals import Base


class TransactionType(enum.Enum):
    DEPOSIT = "deposit"  # 입금
    WITHDRAWAL = "withdrawal"  # 출금
    ORDER_PAYMENT = "order_payment"  # 주문 결제
    ORDER_REFUND = "order_refund"  # 주문 환불
    SELL_INCOME = "sell_income"  # 매도 수익


class User(Base):
    __tablename__ = 'users'

    id = Column(String(36), primary_key=True)
    username = Column(String(50), nullable=False, unique=True)
    email = Column(String(100), nullable=False, unique=True)
    password = Column(String(100), nullable=False)
    balance = Column(Numeric(24, 2), nullable=False, default=0.0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_dt = Column(DateTime, nullable=False, server_default=func.now())
    updated_dt = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    profile = relationship("UserProfile", back_populates="user", uselist=False)
    sessions = relationship("UserSession", back_populates="user")
    account_transactions = relationship("AccountTransaction", back_populates="user")

    __table_args__ = (
        Index('ix_users_username', username),
        Index('ix_users_email', email),
    )


class UserProfile(Base):
    __tablename__ = 'user_profiles'

    user_id = Column(String(36), ForeignKey('users.id'), primary_key=True)
    full_name = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    address = Column(String(200), nullable=True)
    bio = Column(Text, nullable=True)
    created_dt = Column(DateTime, nullable=False, server_default=func.now())
    updated_dt = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="profile")


class UserSession(Base):
    __tablename__ = 'user_sessions'

    id = Column(BigInteger, primary_key=True)
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    token = Column(String(500), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_dt = Column(DateTime, nullable=False, server_default=func.now())

    user = relationship("User", back_populates="sessions")

    __table_args__ = (
        Index('ix_user_sessions_user_id', user_id),
        Index('ix_user_sessions_token', token, unique=True),
        Index('ix_user_sessions_expires_at', expires_at),
    )


class AccountTransaction(Base):
    __tablename__ = 'account_transactions'

    id = Column(BigInteger, primary_key=True)
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    type = Column(Enum(TransactionType), nullable=False)
    amount = Column(Numeric(24, 2), nullable=False)  # 양수: 입금, 음수: 출금
    balance_after = Column(Numeric(24, 2), nullable=False)  # 거래 후 잔액
    description = Column(Text, nullable=True)  # 거래 설명
    created_dt = Column(DateTime, nullable=False, server_default=func.now())

    user = relationship("User", back_populates="account_transactions")

    __table_args__ = (
        Index('ix_account_transactions_user_id', user_id),
        Index('ix_account_transactions_type', type),
        Index('ix_account_transactions_created_dt', created_dt),
    )