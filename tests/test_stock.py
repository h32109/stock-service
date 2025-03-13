import pytest

from trader.exceptions import InvalidStockError
from trader.stock.service import stock_service
from tests.factories import StockTestDataFactory


@pytest.fixture(scope="module")
async def test_db_setup(sql_ctx):
    async with sql_ctx.run_session(commit_on_exit=True):
        test_data = await StockTestDataFactory.create_full_test_data(sql_ctx.session)
        yield test_data

    async with sql_ctx.run_session(commit_on_exit=True):
        await StockTestDataFactory.cleanup_all_data(sql_ctx.session)


@pytest.mark.asyncio
async def test_service_is_stock_code():
    assert stock_service.is_stock_code("123456") == True
    assert stock_service.is_stock_code("12345") == True
    assert stock_service.is_stock_code("1234567") == False
    assert stock_service.is_stock_code("ABC123") == False


@pytest.mark.asyncio
async def test_service_is_initial():
    assert stock_service.is_initial("ㅅㅅㅈㅈ") == True
    assert stock_service.is_initial("ㅅㅅA") == True
    assert stock_service.is_initial("Aㅅㅅ") == True
    assert stock_service.is_initial("삼성") == False
    assert stock_service.is_initial("123") == False


@pytest.mark.asyncio
async def test_service_search_by_code(test_db_setup):
    # Given
    stock_id = test_db_setup["tech_stocks"][0]["stock"].id

    # When
    stocks, total = await stock_service.search(query=stock_id, page=1, size=10)

    # Then
    assert len(stocks) == 1
    assert stocks[0].id == stock_id
    assert "code" in stocks[0].match_type
    assert total == 1


@pytest.mark.asyncio
async def test_service_search_by_partial_code(test_db_setup):
    # Given
    first_digit = test_db_setup["tech_stocks"][0]["stock"].id[0]

    # When
    stocks, total = await stock_service.search(query=first_digit, page=1, size=10)

    # Then
    assert len(stocks) > 0
    for stock in stocks:
        assert stock.id.startswith(first_digit)


@pytest.mark.asyncio
async def test_service_search_by_company_name(test_db_setup):
    # Given
    company_name = test_db_setup["tech_stocks"][0]["stock"].company_name

    # When
    stocks, total = await stock_service.search(query=company_name, page=1, size=10)

    # Then
    assert len(stocks) == 1
    assert stocks[0].company_name == company_name
    assert "name" in stocks[0].match_type


@pytest.mark.asyncio
async def test_service_search_by_initial(test_db_setup):
    # When
    stocks, total = await stock_service.search(query="ㅌㅅ", page=1, size=10)

    # Then
    assert len(stocks) > 0
    assert "initial" in stocks[0].match_type


@pytest.mark.asyncio
async def test_service_search_by_english_name(test_db_setup):
    # When
    stocks, total = await stock_service.search(query="Tech", page=1, size=10)

    # Then
    assert len(stocks) > 0
    found = False
    for stock in stocks:
        if "Tech" in stock.company_name_en:
            found = True
            break
    assert found


@pytest.mark.asyncio
async def test_service_search_by_industry(test_db_setup):
    # When
    stocks, total = await stock_service.search(query="소프트웨어", page=1, size=10)

    # Then
    assert len(stocks) > 0
    assert "industry" in stocks[0].match_type

    assert len(stocks[0].themes) > 0
    found = False
    for theme in stocks[0].themes:
        if theme.medium and "소프트웨어" in theme.medium.name:
            found = True
            break
    assert found


@pytest.mark.asyncio
async def test_service_search_pagination(test_db_setup):
    # When
    all_stocks, total_count = await stock_service.search(query="회사", page=1, size=10)

    # 페이지 크기를 1로 설정하고 첫 페이지 조회
    first_page, _ = await stock_service.search(query="회사", page=1, size=1)

    # 페이지 크기를 1로 설정하고 두번째 페이지 조회
    if total_count > 1:
        second_page, _ = await stock_service.search(query="회사", page=2, size=1)

        # Then
        assert first_page[0].id != second_page[0].id

    # Then
    assert len(first_page) <= 1
    assert total_count == len(all_stocks)


@pytest.mark.asyncio
async def test_service_get_stock(test_db_setup):
    # Given
    stock_id = test_db_setup["tech_stocks"][0]["stock"].id

    # When
    stock = await stock_service.get_stock(stock_id=stock_id)

    # Then
    assert stock.id == stock_id
    assert stock.company_name == test_db_setup["tech_stocks"][0]["stock"].company_name
    assert stock.market_type == test_db_setup["tech_stocks"][0]["stock"].market_type
    assert stock.current_price == float(test_db_setup["tech_stocks"][0]["price"].current_price)
    assert len(stock.themes) > 0


@pytest.mark.asyncio
async def test_service_get_invalid_stock():
    with pytest.raises(InvalidStockError):
        await stock_service.get_stock(stock_id="999999")


@pytest.mark.asyncio
async def test_service_get_themes_for_stock(test_db_setup):
    # Given
    stock_id = test_db_setup["tech_stocks"][0]["stock"].id

    # When
    themes = await stock_service.get_themes_for_stock(stock_id=stock_id)

    # Then
    assert len(themes) > 0
    theme = themes[0]

    assert theme.large.code == test_db_setup["tech_industry"]["large"].code
    assert theme.large.name == test_db_setup["tech_industry"]["large"].name
    assert theme.medium.code == test_db_setup["tech_industry"]["medium"].code
    assert theme.medium.name == test_db_setup["tech_industry"]["medium"].name
    assert theme.small.code == test_db_setup["tech_industry"]["small"].code
    assert theme.small.name == test_db_setup["tech_industry"]["small"].name


@pytest.mark.asyncio
async def test_service_search_by_large_industry(test_db_setup):
    # Given
    large_industry_name = test_db_setup["tech_industry"]["large"].name

    # When
    stocks, total = await stock_service.search(query=large_industry_name, page=1, size=10)

    # Then
    assert len(stocks) > 0
    assert "industry" in stocks[0].match_type


@pytest.mark.asyncio
async def test_service_search_by_medium_industry(test_db_setup):
    # Given
    medium_industry_name = test_db_setup["finance_industry"]["medium"].name

    # When
    stocks, total = await stock_service.search(query=medium_industry_name, page=1, size=10)

    # Then
    assert len(stocks) > 0
    assert "industry" in stocks[0].match_type


@pytest.mark.asyncio
async def test_service_search_by_small_industry(test_db_setup):
    # Given
    small_industry_name = test_db_setup["finance_industry"]["small"].name

    # When
    stocks, total = await stock_service.search(query=small_industry_name, page=1, size=10)

    # Then
    assert len(stocks) > 0
    assert "industry" in stocks[0].match_type


@pytest.mark.asyncio
async def test_service_search_empty_result():
    # When
    stocks, total = await stock_service.search(query="존재하지않는회사", page=1, size=10)

    # Then
    assert len(stocks) == 0
    assert total == 0


@pytest.mark.asyncio
async def test_service_search_page_out_of_range(test_db_setup):
    # Given
    _, total = await stock_service.search(query="회사", page=1, size=10)

    # When (존재하지 않는 페이지 요청)
    out_of_range_page = (total // 10) + 10
    stocks, _ = await stock_service.search(query="회사", page=out_of_range_page, size=10)

    # Then
    assert len(stocks) == 0