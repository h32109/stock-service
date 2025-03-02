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

stock_large_industry_mapping = Table(
    'stock_large_industry_mapping',
    Base.metadata,
    Column('stock_id', String(10), ForeignKey('stocks.id'), primary_key=True),
    Column('large_industry_code', String(3), ForeignKey('large_industries.code'), primary_key=True),
    Column('created_dt', DateTime, nullable=False, server_default=func.now())
)

stock_medium_industry_mapping = Table(
    'stock_medium_industry_mapping',
    Base.metadata,
    Column('stock_id', String(10), ForeignKey('stocks.id'), primary_key=True),
    Column('medium_industry_code', String(4), ForeignKey('medium_industries.code'), primary_key=True),
    Column('created_dt', DateTime, nullable=False, server_default=func.now())
)

stock_small_industry_mapping = Table(
    'stock_small_industry_mapping',
    Base.metadata,
    Column('stock_id', String(10), ForeignKey('stocks.id'), primary_key=True),
    Column('small_industry_code', String(6), ForeignKey('small_industries.code'), primary_key=True),
    Column('is_primary', Boolean, default=False, nullable=False),
    Column('created_dt', DateTime, nullable=False, server_default=func.now())
)


class LargeIndustry(Base):
    __tablename__ = 'large_industries'

    code = Column(String(3), primary_key=True)
    name = Column(String(100), nullable=False)
    created_dt = Column(DateTime, nullable=False, server_default=func.now())
    updated_dt = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # 관계 설정
    medium_industries = relationship("MediumIndustry", back_populates="large_industry")
    stocks = relationship("Stock", secondary=stock_large_industry_mapping, back_populates="large_industries")


class MediumIndustry(Base):
    __tablename__ = 'medium_industries'

    code = Column(String(4), primary_key=True)
    name = Column(String(100), nullable=False)
    large_industry_code = Column(String(3), ForeignKey('large_industries.code'), nullable=False)
    created_dt = Column(DateTime, nullable=False, server_default=func.now())
    updated_dt = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    large_industry = relationship("LargeIndustry", back_populates="medium_industries")
    small_industries = relationship("SmallIndustry", back_populates="medium_industry")
    stocks = relationship("Stock", secondary=stock_medium_industry_mapping, back_populates="medium_industries")

    __table_args__ = (
        Index('ix_medium_industries_large_code', large_industry_code),
    )


class SmallIndustry(Base):
    __tablename__ = 'small_industries'

    code = Column(String(6), primary_key=True)
    name = Column(String(100), nullable=False)
    medium_industry_code = Column(String(4), ForeignKey('medium_industries.code'), nullable=False)
    created_dt = Column(DateTime, nullable=False, server_default=func.now())
    updated_dt = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    medium_industry = relationship("MediumIndustry", back_populates="small_industries")
    stocks = relationship(
        "Stock",
        secondary=stock_small_industry_mapping,
        back_populates="small_industries",
        primaryjoin="and_(SmallIndustry.code==stock_small_industry_mapping.c.small_industry_code)"
    )

    __table_args__ = (
        Index('ix_small_industries_medium_code', medium_industry_code),
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
    is_active = Column(Boolean, nullable=False, default=True)
    shares_outstanding = Column(BigInteger, nullable=False)
    created_dt = Column(DateTime, nullable=False, server_default=func.now())
    updated_dt = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    prices = relationship("StockPrice", back_populates="stock")
    price_history = relationship("StockPriceHistory", back_populates="stock")

    large_industries = relationship("LargeIndustry", secondary=stock_large_industry_mapping, back_populates="stocks")
    medium_industries = relationship("MediumIndustry", secondary=stock_medium_industry_mapping, back_populates="stocks")
    small_industries = relationship(
        "SmallIndustry",
        secondary=stock_small_industry_mapping,
        back_populates="stocks",
        primaryjoin="and_(Stock.id==stock_small_industry_mapping.c.stock_id)"
    )

    primary_industry = relationship(
        "SmallIndustry",
        secondary=stock_small_industry_mapping,
        primaryjoin="and_(Stock.id==stock_small_industry_mapping.c.stock_id, stock_small_industry_mapping.c.is_primary==True)",
        secondaryjoin="SmallIndustry.code==stock_small_industry_mapping.c.small_industry_code",
        uselist=False,  # 단일 객체로 반환
        viewonly=True  # 읽기 전용
    )

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
    current_price = Column(Numeric(16, 2), nullable=False)
    previous_price = Column(Numeric(16, 2), nullable=False)
    open_price = Column(Numeric(16, 2), nullable=False)
    high_price = Column(Numeric(16, 2), nullable=False)
    low_price = Column(Numeric(16, 2), nullable=False)
    volume = Column(BigInteger, nullable=False)
    price_change = Column(Numeric(16, 2), nullable=False)
    market_cap = Column(Numeric(24, 2), nullable=False)
    created_dt = Column(DateTime, nullable=False, server_default=func.now())
    updated_dt = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    stock = relationship("Stock", back_populates="prices")

    __table_args__ = (
        UniqueConstraint('stock_id', 'trading_date', name='uq_stock_trading_date'),
        Index('ix_stock_prices_trading_date', trading_date),
        Index('ix_stock_prices_stock_id_date', stock_id, trading_date)
    )


class StockPriceHistory(Base):
    __tablename__ = 'stock_price_history'

    id = Column(BigInteger, primary_key=True)
    stock_id = Column(String(10), ForeignKey('stocks.id'), nullable=False)
    price = Column(Numeric(16, 2), nullable=False)
    volume = Column(BigInteger, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    created_dt = Column(DateTime, nullable=False, server_default=func.now())

    stock = relationship("Stock", back_populates="price_history")

    __table_args__ = (
        Index('ix_price_history_stock_timestamp', stock_id, timestamp),
    )