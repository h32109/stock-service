import typing as t
from pydantic import BaseModel
from datetime import date


class IndustryResponse(BaseModel):
    code: str
    name: str


class ThemeResponse(BaseModel):
    large: t.Optional[IndustryResponse] = None
    medium: t.Optional[IndustryResponse] = None
    small: t.Optional[IndustryResponse] = None


class StockSearchResponse(BaseModel):
    id: str
    company_name: str
    company_name_en: str
    company_name_initial: str
    security_type: str
    market_type: str
    current_price: float
    price_change: float
    volume: int
    market_cap: float
    themes: t.List[ThemeResponse]
    match_type: t.List[str]


class SearchResponse(BaseModel):
    data: dict


class StockDetailResponse(BaseModel):
    id: str
    company_name: str
    company_name_en: str
    company_name_initial: str
    listing_date: date
    market_type: str
    security_type: str
    industry_code: str
    is_active: bool
    current_price: float
    previous_price: float
    open_price: float
    high_price: float
    low_price: float
    volume: int
    price_change: float
    market_cap: float
    shares_outstanding: int
    trading_date: str
    themes: t.List[ThemeResponse]


class DetailResponse(BaseModel):
    data: StockDetailResponse
