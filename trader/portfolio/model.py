from sqlalchemy import (
    Column,
    String,
    DateTime,
    Numeric,
    Index,
    ForeignKey,
    BigInteger,
    Integer,
    CheckConstraint,
    UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from trader.globals import Base


class Portfolio(Base):
    __tablename__ = 'portfolio'

    id = Column(BigInteger, primary_key=True)
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    stock_id = Column(String(10), ForeignKey('stocks.id'), nullable=False)
    quantity = Column(Integer, nullable=False, default=0)  # 보유 수량
    avg_purchase_price = Column(Numeric(16, 2), nullable=False)  # 평균 매수 가격
    total_purchase_amount = Column(Numeric(24, 2), nullable=False)  # 총 매수 금액
    hold_quantity = Column(Integer, nullable=False, default=0)  # 매도 보류 수량
    created_dt = Column(DateTime, nullable=False, server_default=func.now())
    updated_dt = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="portfolio")
    stock = relationship("Stock")

    __table_args__ = (
        CheckConstraint('quantity >= 0', name='chk_non_negative_portfolio_quantity'),
        CheckConstraint('avg_purchase_price >= 0', name='chk_non_negative_avg_price'),
        CheckConstraint('total_purchase_amount >= 0', name='chk_non_negative_purchase_amount'),
        CheckConstraint('hold_quantity >= 0 AND hold_quantity <= quantity', name='chk_valid_hold_quantity'),
        UniqueConstraint('user_id', 'stock_id', name='uq_user_stock_portfolio'),
        Index('ix_portfolio_user_id', user_id),
        Index('ix_portfolio_stock_id', stock_id),
    )
