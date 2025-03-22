import typing as t

import hgtk
from sqlalchemy import or_, and_, select
from sqlalchemy.exc import SQLAlchemyError

from trader.exceptions import InvalidStockError, DatabaseError
from trader.service import ServiceBase, Service
from trader.globals import sql
from trader.stock.model import (
    Stock,
    StockPrice,
    SmallIndustry,
    MediumIndustry,
    LargeIndustry,
    stock_small_industry_mapping,
    stock_medium_industry_mapping,
    stock_large_industry_mapping
)
from trader.stock.schema import (
    ThemeResponse,
    StockSearchResponse,
    IndustryResponse,
    StockDetailResponse
)


class StockServiceBase(ServiceBase):
    config: t.Any

    async def configuration(self, config):
        self.config = config


class StockService(StockServiceBase):

    @staticmethod
    def is_stock_code(query: str) -> bool:
        """종목코드 검색어 여부 확인"""
        return len(query) <= 6 and query.isdigit()

    @staticmethod
    def is_initial(query: str) -> bool:
        """
        한글 초성 또는 초성+영문 혼합 검색어 여부 확인
        예: 'ㅅㅅ', 'ㅅS', 'Sㅅ' 등을 모두 초성 검색으로 인식
        """
        korean_part = ""
        english_part = ""

        for c in query:
            if hgtk.checker.is_jamo(c):
                korean_part += c
            elif c.isalpha():
                english_part += c

        has_korean_initial = bool(korean_part)
        is_valid_query = len(korean_part) + len(english_part) == len(query)

        return has_korean_initial and is_valid_query

    @staticmethod
    async def get_themes_for_stock(stock_id: str) -> t.List[ThemeResponse]:
        """
        주식의 산업분류를 계층 구조로 가져옴 (대-중-소 연결)
        """
        try:
            stmt = select(
                SmallIndustry, MediumIndustry, LargeIndustry
            ).join(
                stock_small_industry_mapping,
                SmallIndustry.code == stock_small_industry_mapping.c.small_industry_code
            ).filter(
                stock_small_industry_mapping.c.stock_id == stock_id
            ).join(
                MediumIndustry,
                SmallIndustry.medium_industry_code == MediumIndustry.code
            ).join(
                LargeIndustry,
                MediumIndustry.large_industry_code == LargeIndustry.code
            )

            result = await sql.session.execute(stmt)
            results = result.all()

            theme_results = []

            for small_ind, medium_ind, large_ind in results:
                theme = ThemeResponse(
                    large=IndustryResponse(code=large_ind.code, name=large_ind.name),
                    medium=IndustryResponse(code=medium_ind.code, name=medium_ind.name),
                    small=IndustryResponse(code=small_ind.code, name=small_ind.name)
                )

                theme_results.append(theme)

            return theme_results
        except SQLAlchemyError as e:
            return []

    async def search(self, query: str, page: int, size: int) -> t.Tuple[t.List[StockSearchResponse], int]:
        try:
            if self.is_stock_code(query):
                stmt = select(Stock, StockPrice) \
                    .join(StockPrice, Stock.id == StockPrice.stock_id) \
                    .filter(Stock.id.like(f"{query}%")) \
                    .order_by(StockPrice.market_cap.desc())

                result = await sql.session.execute(stmt)
                stocks_with_prices = result.all()

                total_count = len(stocks_with_prices)
                search_type = "code"

            # 초성 검색
            elif self.is_initial(query):
                korean_part = ""
                english_part = ""

                for c in query:
                    if hgtk.checker.is_jamo(c):
                        korean_part += c
                    elif c.isalpha():
                        english_part += c

                conditions = []

                if korean_part:
                    conditions.append(Stock.company_name_initial.startswith(korean_part))

                if english_part:
                    conditions.append(Stock.company_name_en.ilike(f"{english_part}%"))

                stmt = select(Stock, StockPrice) \
                    .join(StockPrice, Stock.id == StockPrice.stock_id) \
                    .filter(and_(*conditions)) \
                    .order_by(StockPrice.market_cap.desc())

                result = await sql.session.execute(stmt)
                stocks_with_prices = result.all()

                total_count = len(stocks_with_prices)
                search_type = "initial"

            else:
                # 대분류 산업 검색
                stmt = select(Stock.id) \
                    .join(stock_large_industry_mapping, Stock.id == stock_large_industry_mapping.c.stock_id) \
                    .join(LargeIndustry, LargeIndustry.code == stock_large_industry_mapping.c.large_industry_code) \
                    .filter(LargeIndustry.name.like(f"%{query}%"))

                result = await sql.session.execute(stmt)
                large_industry_stock_ids = result.scalars().all()

                if large_industry_stock_ids:
                    # 대분류 산업으로 검색된 종목들 조회
                    stmt = select(Stock, StockPrice) \
                        .join(StockPrice, Stock.id == StockPrice.stock_id) \
                        .filter(Stock.id.in_(large_industry_stock_ids)) \
                        .order_by(StockPrice.market_cap.desc()) \
                        .limit(size * page + size)

                    result = await sql.session.execute(stmt)
                    stocks_with_prices = result.all()

                    total_count = len(large_industry_stock_ids)
                    search_type = "large_industry"

                else:
                    # 중분류 산업 검색
                    stmt = select(Stock.id) \
                        .join(stock_medium_industry_mapping, Stock.id == stock_medium_industry_mapping.c.stock_id) \
                        .join(MediumIndustry,
                              MediumIndustry.code == stock_medium_industry_mapping.c.medium_industry_code) \
                        .filter(MediumIndustry.name.like(f"%{query}%"))

                    result = await sql.session.execute(stmt)
                    medium_industry_stock_ids = result.scalars().all()

                    if medium_industry_stock_ids:
                        # 중분류 산업으로 검색된 종목들 조회
                        stmt = select(Stock, StockPrice) \
                            .join(StockPrice, Stock.id == StockPrice.stock_id) \
                            .filter(Stock.id.in_(medium_industry_stock_ids)) \
                            .order_by(StockPrice.market_cap.desc()) \
                            .limit(size * page + size)

                        result = await sql.session.execute(stmt)
                        stocks_with_prices = result.all()

                        total_count = len(medium_industry_stock_ids)
                        search_type = "medium_industry"

                    else:
                        # 소분류 산업 검색
                        stmt = select(Stock.id) \
                            .join(stock_small_industry_mapping, Stock.id == stock_small_industry_mapping.c.stock_id) \
                            .join(SmallIndustry,
                                  SmallIndustry.code == stock_small_industry_mapping.c.small_industry_code) \
                            .filter(SmallIndustry.name.like(f"%{query}%"))

                        result = await sql.session.execute(stmt)
                        small_industry_stock_ids = result.scalars().all()

                        if small_industry_stock_ids:
                            # 소분류 산업으로 검색된 종목들 조회
                            stmt = select(Stock, StockPrice) \
                                .join(StockPrice, Stock.id == StockPrice.stock_id) \
                                .filter(Stock.id.in_(small_industry_stock_ids)) \
                                .order_by(StockPrice.market_cap.desc()) \
                                .limit(size * page + size)

                            result = await sql.session.execute(stmt)
                            stocks_with_prices = result.all()

                            total_count = len(small_industry_stock_ids)
                            search_type = "small_industry"

                        else:
                            # 회사명 검색
                            stmt = select(Stock, StockPrice) \
                                .join(StockPrice, Stock.id == StockPrice.stock_id) \
                                .filter(
                                or_(
                                    Stock.company_name.like(f"%{query}%"),
                                    Stock.company_name_en.like(f"%{query}%")
                                )
                            ) \
                                .order_by(StockPrice.market_cap.desc())

                            result = await sql.session.execute(stmt)
                            stocks_with_prices = result.all()

                            total_count = len(stocks_with_prices)
                            search_type = "company_name"

            # 페이지네이션 처리
            skip = (page - 1) * size
            if skip >= total_count:
                return [], total_count

            end = min(skip + size, total_count)
            stocks_with_prices_paginated = stocks_with_prices[skip:end]

            # 결과 목록 생성
            results = []
            for stock, price in stocks_with_prices_paginated:
                themes = await self.get_themes_for_stock(stock.id)

                # 매치 타입 결정
                if search_type == "code":
                    current_match_type = ["code"]
                elif search_type == "initial":
                    current_match_type = ["initial"]
                elif search_type in ["large_industry", "medium_industry", "small_industry"]:
                    current_match_type = ["industry", search_type]
                else:
                    current_match_type = ["name"]

                stock_response = StockSearchResponse(
                    id=stock.id,
                    company_name=stock.company_name,
                    company_name_en=stock.company_name_en,
                    company_name_initial=stock.company_name_initial,
                    security_type=stock.security_type,
                    market_type=stock.market_type,
                    current_price=float(price.current_price),
                    price_change=float(price.price_change),
                    volume=price.volume,
                    market_cap=float(price.market_cap),
                    themes=themes,
                    match_type=current_match_type
                )
                results.append(stock_response)

            return results, total_count

        except SQLAlchemyError as e:
            raise DatabaseError(
                "Database error while searching stocks",
                {"query": query, "error": str(e)}
            )

    async def get_stock(self, stock_id: str) -> StockDetailResponse:
        try:
            stmt = select(Stock, StockPrice) \
                .join(StockPrice, Stock.id == StockPrice.stock_id) \
                .filter(Stock.id == stock_id)

            result = await sql.session.execute(stmt)
            result_row = result.first()

            if not result_row:
                raise InvalidStockError(
                    "Invalid stock",
                    {"stock_id": stock_id}
                )

            stock, price = result_row

            themes = await self.get_themes_for_stock(stock.id)

            # 주식 산업 코드 - 소분류 산업 코드 사용
            industry_code = stock.id
            if themes and themes[0].small:
                industry_code = themes[0].small.code

            return StockDetailResponse(
                id=stock.id,
                company_name=stock.company_name,
                company_name_en=stock.company_name_en,
                company_name_initial=stock.company_name_initial,
                listing_date=stock.listing_date,
                market_type=stock.market_type,
                security_type=stock.security_type,
                industry_code=industry_code,
                is_active=stock.is_active,
                current_price=float(price.current_price),
                previous_price=float(price.previous_price),
                open_price=float(price.open_price),
                high_price=float(price.high_price),
                low_price=float(price.low_price),
                volume=price.volume,
                price_change=float(price.price_change),
                market_cap=float(price.market_cap),
                shares_outstanding=stock.shares_outstanding,
                trading_date=price.trading_date.strftime("%Y-%m-%dT09:00:00Z"),
                themes=themes
            )

        except InvalidStockError:
            raise
        except SQLAlchemyError as e:
            raise DatabaseError(
                "Database error while fetching stock details",
                {"stock_id": stock_id, "error": str(e)}
            )


stock_service = Service.add_service(StockService)