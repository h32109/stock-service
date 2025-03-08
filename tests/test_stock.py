import pytest
from unittest.mock import AsyncMock, patch
from datetime import date
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from trader.stock.schema import (
    ThemeResponse,
    StockSearchResponse,
    StockDetailResponse,
    IndustryResponse
)
from trader.stock.service import StockService
from trader.exceptions import InvalidStockError
from trader.stock.model import (
    Stock, StockPrice, SmallIndustry, MediumIndustry, LargeIndustry,
)


@pytest.fixture
def mock_stock():
    return Stock(
        id="005930",
        company_name="삼성전자",
        company_name_en="Samsung Electronics",
        company_name_initial="ㅅㅅㅈㅈ",
        listing_date=date(1975, 6, 11),
        market_type="KOSPI",
        security_type="보통주",
        is_active=True,
        shares_outstanding=5969782550
    )


@pytest.fixture
def mock_stock_price():
    return StockPrice(
        id=1,
        stock_id="005930",
        trading_date=date(2023, 7, 15),
        current_price=Decimal("70000.00"),
        previous_price=Decimal("69000.00"),
        open_price=Decimal("69500.00"),
        high_price=Decimal("70500.00"),
        low_price=Decimal("69000.00"),
        volume=12750000,
        price_change=Decimal("1000.00"),
        market_cap=Decimal("4.1788477850e+14")
    )


@pytest.fixture
def mock_industries():
    small_ind = SmallIndustry(
        code="C2611",
        name="반도체 제조업",
        medium_industry_code="C26"
    )

    medium_ind = MediumIndustry(
        code="C26",
        name="전자부품 제조업",
        large_industry_code="C"
    )

    large_ind = LargeIndustry(
        code="C",
        name="제조업"
    )

    return {"small": small_ind, "medium": medium_ind, "large": large_ind}


@pytest.fixture
def mock_theme(mock_industries):
    return ThemeResponse(
        large=IndustryResponse(code=mock_industries["large"].code, name=mock_industries["large"].name),
        medium=IndustryResponse(code=mock_industries["medium"].code, name=mock_industries["medium"].name),
        small=IndustryResponse(code=mock_industries["small"].code, name=mock_industries["small"].name)
    )


@pytest.fixture
def mock_search_response(mock_theme):
    return StockSearchResponse(
        id="005930",
        company_name="삼성전자",
        company_name_en="Samsung Electronics",
        company_name_initial="ㅅㅅㅈㅈ",
        security_type="보통주",
        market_type="KOSPI",
        current_price=70000.00,
        price_change=1000.00,
        volume=12750000,
        market_cap=417884778500000.00,
        themes=[mock_theme],
        match_type=["name"]
    )


@pytest.fixture
def mock_detail_response(mock_theme):
    return StockDetailResponse(
        id="005930",
        company_name="삼성전자",
        company_name_en="Samsung Electronics",
        company_name_initial="ㅅㅅㅈㅈ",
        listing_date=date(1975, 6, 11),
        market_type="KOSPI",
        security_type="보통주",
        industry_code="C2611",
        is_active=True,
        current_price=70000.00,
        previous_price=69000.00,
        open_price=69500.00,
        high_price=70500.00,
        low_price=69000.00,
        volume=12750000,
        price_change=1000.00,
        market_cap=417884778500000.00,
        shares_outstanding=5969782550,
        trading_date="2023-07-15T09:00:00Z",
        themes=[mock_theme]
    )


@pytest.fixture
async def mock_async_session(sql_ctx):
    original_session = sql_ctx._session.get()

    mock_session = AsyncMock(spec=AsyncSession)

    def setup_query_chain(mock_session_obj):
        mock_query = AsyncMock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []
        mock_query.first.return_value = None

        mock_session_obj.query = AsyncMock(return_value=mock_query)
        mock_session_obj.execute = AsyncMock()

        return mock_query

    mock_query = setup_query_chain(mock_session)

    sql_ctx._session.set(mock_session)

    yield mock_session

    sql_ctx._session.set(original_session)


class TestStockService:

    @pytest.fixture
    def service_instance(self, get_service):
        stock_service = get_service("StockService")
        return stock_service

    def test_is_stock_code(self):
        assert StockService.is_stock_code("005930") == True
        assert StockService.is_stock_code("12345") == True
        assert StockService.is_stock_code("123456") == True
        assert StockService.is_stock_code("1234567") == False
        assert StockService.is_stock_code("abcde") == False
        assert StockService.is_stock_code("123ab") == False

    def test_is_initial(self):
        assert StockService.is_initial("ㅅㅅ") == True
        assert StockService.is_initial("ㅅㅅㅈㅈ") == True
        assert StockService.is_initial("ㅅs") == True
        assert StockService.is_initial("Sㅅ") == True
        assert StockService.is_initial("삼성") == False
        assert StockService.is_initial("Samsung") == False

    @pytest.mark.asyncio
    async def test_get_themes_for_stock(self, mock_async_session, mock_industries):
        mock_query_result = [(
            mock_industries["small"],
            mock_industries["medium"],
            mock_industries["large"]
        )]

        mock_result = AsyncMock()
        mock_result.all.return_value = mock_query_result
        mock_async_session.execute.return_value = mock_result

        with patch('trader.stock.service.StockService.get_themes_for_stock', return_value=[
            ThemeResponse(
                large=IndustryResponse(code=mock_industries["large"].code, name=mock_industries["large"].name),
                medium=IndustryResponse(code=mock_industries["medium"].code, name=mock_industries["medium"].name),
                small=IndustryResponse(code=mock_industries["small"].code, name=mock_industries["small"].name)
            )
        ]):
            service = StockService()
            result = service.get_themes_for_stock("005930")

            assert len(result) == 1
            assert result[0].large.code == "C"
            assert result[0].medium.code == "C26"
            assert result[0].small.code == "C2611"

    @pytest.mark.asyncio
    async def test_search_by_code(self, service_instance, mock_async_session, mock_stock, mock_stock_price, mock_theme):
        mock_result = AsyncMock()
        mock_result.all.return_value = [(mock_stock, mock_stock_price)]
        mock_async_session.execute.return_value = mock_result

        with patch.object(service_instance, 'get_themes_for_stock', return_value=[mock_theme]):
            results, total_count = await service_instance.search("005930", 1, 20)

            assert len(results) == 1
            assert results[0].id == "005930"
            assert results[0].company_name == "삼성전자"
            assert "code" in results[0].match_type

    @pytest.mark.asyncio
    async def test_get_stock(self, service_instance, mock_async_session, mock_stock, mock_stock_price, mock_theme):
        mock_result = AsyncMock()
        mock_result.first.return_value = (mock_stock, mock_stock_price)
        mock_async_session.execute.return_value = mock_result

        with patch.object(service_instance, 'get_themes_for_stock', return_value=[mock_theme]):
            result = await service_instance.get_stock("005930")

            assert result.id == "005930"
            assert result.company_name == "삼성전자"
            assert result.industry_code == "C2611"

    @pytest.mark.asyncio
    async def test_get_stock_not_found(self, service_instance, mock_async_session):
        mock_result = AsyncMock()
        mock_result.first.return_value = None
        mock_async_session.execute.return_value = mock_result

        with pytest.raises(InvalidStockError):
            await service_instance.get_stock("000000")