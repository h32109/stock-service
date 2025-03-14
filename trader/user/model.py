from sqlalchemy import (
    Column,
    String,
    DateTime,
    Numeric,
    Index,
    CheckConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from trader.globals import Base


class User(Base):
    __tablename__ = 'users'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), nullable=False, unique=True)
    email = Column(String(100), nullable=False, unique=True)
    balance = Column(Numeric(24, 2), nullable=False, default=0.0)  # 계좌 잔액
    created_dt = Column(DateTime, nullable=False, server_default=func.now())
    updated_dt = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    orders = relationship("Order", back_populates="user")
    portfolio = relationship("Portfolio", back_populates="user")

    __table_args__ = (
        CheckConstraint('balance >= 0', name='chk_positive_balance'),
        Index('ix_users_username', username),
        Index('ix_users_email', email),
    )