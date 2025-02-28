from sqlalchemy import (
    Column,
    String,
    ForeignKey,
    Table,
    UniqueConstraint,
    Index,
    Boolean,
    Date,
    DateTime,
    Numeric,
    BigInteger,
    CheckConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from trader.globals import Base

stock_industry_mapping = Table(
    'stock_industry_mapping',
    Base.metadata,
    Column('stock_id', String(10), ForeignKey('stocks.id'), primary_key=True),
    Column('industry_code', String(20), ForeignKey('industries.code'), primary_key=True),
    Column('created_dt', DateTime, nullable=False, server_default=func.now())
)

class Stock(Base):
    __tablename__ = 'stocks'

    id = Column(String(10), primary_key=True)  # 종목코드
    company_name = Column(String(100), nullable=False)
    company_name_en = Column(String(100), nullable=False)
    company_name_initial = Column(String(50), nullable=False)
    listing_date = Column(Date, nullable=False)
    market_type = Column(String(10), nullable=False)
    security_type = Column(String(10), nullable=False)
    industry_code = Column(String(20), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    shares_outstanding = Column(BigInteger, nullable=False)
    created_dt = Column(DateTime, nullable=False, server_default=func.now())
    updated_dt = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    prices = relationship("StockPrice", back_populates="stock")
    price_history = relationship("StockPriceHistory", back_populates="stock")
    industries = relationship("Industry", secondary=stock_industry_mapping, back_populates="stocks")

    __table_args__ = (
        CheckConstraint(market_type.in_(['KOSPI', 'KOSDAQ']), name='chk_market_type'),
        CheckConstraint(security_type.in_(['보통주', '우선주']), name='chk_security_type'),
        Index('ix_stocks_company_name', company_name),
        Index('ix_stocks_company_name_initial', company_name_initial),
        Index('ix_stocks_market_type', market_type)
    )

class StockPrice(Base):
    __tablename__ = 'stock_prices'

    id = Column(BigInteger, primary_key=True)
    stock_id = Column(String(10), ForeignKey('stocks.id'), nullable=False)
    trading_date = Column(Date, nullable=False)
    current_price = Column(Numeric(16,2), nullable=False)
    previous_price = Column(Numeric(16,2), nullable=False)
    open_price = Column(Numeric(16,2), nullable=False)
    high_price = Column(Numeric(16,2), nullable=False)
    low_price = Column(Numeric(16,2), nullable=False)
    volume = Column(BigInteger, nullable=False)
    price_change = Column(Numeric(16,2), nullable=False)
    market_cap = Column(Numeric(24,2), nullable=False)
    created_dt = Column(DateTime, nullable=False, server_default=func.now())
    updated_dt = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    stock = relationship("Stock", back_populates="prices")

    __table_args__ = (
        UniqueConstraint('stock_id', 'trading_date', name='uq_stock_trading_date'),
        Index('ix_stock_prices_trading_date', trading_date),
        Index('ix_stock_prices_stock_id_date', stock_id, trading_date)
    )

class Industry(Base):
    __tablename__ = 'industries'

    code = Column(String(20), primary_key=True)
    name = Column(String(100), nullable=False)
    created_dt = Column(DateTime, nullable=False, server_default=func.now())
    updated_dt = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    stocks = relationship("Stock", secondary=stock_industry_mapping, back_populates="industries")

class StockPriceHistory(Base):
    __tablename__ = 'stock_price_history'

    id = Column(BigInteger, primary_key=True)
    stock_id = Column(String(10), ForeignKey('stocks.id'), nullable=False)
    price = Column(Numeric(16,2), nullable=False)
    volume = Column(BigInteger, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    created_dt = Column(DateTime, nullable=False, server_default=func.now())

    stock = relationship("Stock", back_populates="price_history")

    __table_args__ = (
        Index('ix_price_history_stock_timestamp', stock_id, timestamp),
    )