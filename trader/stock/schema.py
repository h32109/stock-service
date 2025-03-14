import typing as t
from pydantic import BaseModel, Field
from datetime import date


class IndustryResponse(BaseModel):
    code: str = Field(..., description="산업 코드")
    name: str = Field(..., description="산업명")


class ThemeResponse(BaseModel):
    large: t.Optional[IndustryResponse] = Field(None, description="대분류 산업")
    medium: t.Optional[IndustryResponse] = Field(None, description="중분류 산업")
    small: t.Optional[IndustryResponse] = Field(None, description="소분류 산업")


class StockSearchResponse(BaseModel):
    id: str = Field(..., description="주식 종목 코드")
    company_name: str = Field(..., description="회사명")
    company_name_en: str = Field(..., description="회사 영문명")
    company_name_initial: str = Field(..., description="회사명 초성")
    security_type: str = Field(..., description="증권 유형 (보통주/우선주)")
    market_type: str = Field(..., description="시장 유형 (KOSPI/KOSDAQ)")
    current_price: float = Field(..., description="현재가")
    price_change: float = Field(..., description="변동금액")
    volume: int = Field(..., description="거래량")
    market_cap: float = Field(..., description="시가총액")
    themes: t.List[ThemeResponse] = Field(..., description="테마 정보")
    match_type: t.List[str] = Field(..., description="매치 타입 (검색 일치 유형)")


class StockDetailResponse(BaseModel):
    id: str = Field(..., description="주식 종목 코드")
    company_name: str = Field(..., description="회사명")
    company_name_en: str = Field(..., description="회사 영문명")
    company_name_initial: str = Field(..., description="회사명 초성")
    listing_date: date = Field(..., description="상장일")
    market_type: str = Field(..., description="시장 유형 (KOSPI/KOSDAQ)")
    security_type: str = Field(..., description="증권 유형 (보통주/우선주)")
    industry_code: str = Field(..., description="업종 코드")
    is_active: bool = Field(..., description="상장 여부")
    current_price: float = Field(..., description="현재가")
    previous_price: float = Field(..., description="전일 종가")
    open_price: float = Field(..., description="시가")
    high_price: float = Field(..., description="고가")
    low_price: float = Field(..., description="저가")
    volume: int = Field(..., description="거래량")
    price_change: float = Field(..., description="변동금액")
    market_cap: float = Field(..., description="시가총액")
    shares_outstanding: int = Field(..., description="상장주식수")
    trading_date: str = Field(..., description="거래일자")
    themes: t.List[ThemeResponse] = Field(..., description="테마 정보")


class StockListResponse(BaseModel):
    stocks: t.List[StockSearchResponse] = Field(..., description="주식 목록")
    total_count: int = Field(..., description="총 주식 수")


class StockSearchSuccessResponse(BaseModel):
    data: StockListResponse = Field(..., description="응답 데이터")


class StockDetailSuccessResponse(BaseModel):
    data: StockDetailResponse = Field(..., description="응답 데이터")