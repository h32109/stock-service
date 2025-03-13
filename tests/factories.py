import random
import datetime
from decimal import Decimal
import typing as t

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from trader.stock.model import (
    Stock,
    StockPrice,
    LargeIndustry,
    MediumIndustry,
    SmallIndustry,
    stock_large_industry_mapping,
    stock_medium_industry_mapping,
    stock_small_industry_mapping
)


class StockTestDataFactory:
    """테스트 데이터 생성을 위한 팩토리"""

    @classmethod
    async def create_large_industry(cls,
                                    session: AsyncSession,
                                    code: str = None,
                                    name: str = None) -> LargeIndustry:
        code = code or f'L{random.randint(10, 99)}'
        name = name or f'대분류산업{random.randint(1, 100)}'

        large = LargeIndustry(
            code=code,
            name=name
        )
        session.add(large)
        await session.flush()
        return large

    @classmethod
    async def create_medium_industry(cls,
                                     session: AsyncSession,
                                     large_industry_code: str = None,
                                     code: str = None,
                                     name: str = None) -> MediumIndustry:
        code = code or f'M{random.randint(10, 99)}'
        name = name or f'중분류산업{random.randint(1, 100)}'

        if not large_industry_code:
            large = await cls.create_large_industry(session)
            large_industry_code = large.code

        medium = MediumIndustry(
            code=code,
            name=name,
            large_industry_code=large_industry_code
        )
        session.add(medium)
        await session.flush()
        return medium

    @classmethod
    async def create_small_industry(cls,
                                    session: AsyncSession,
                                    medium_industry_code: str = None,
                                    code: str = None,
                                    name: str = None) -> SmallIndustry:
        code = code or f'S{random.randint(10, 99)}'
        name = name or f'소분류산업{random.randint(1, 100)}'

        if not medium_industry_code:
            medium = await cls.create_medium_industry(session)
            medium_industry_code = medium.code

        small = SmallIndustry(
            code=code,
            name=name,
            medium_industry_code=medium_industry_code
        )
        session.add(small)
        await session.flush()
        return small

    @classmethod
    async def create_stock(cls,
                           session: AsyncSession,
                           id: str = None,
                           company_name: str = None,
                           company_name_en: str = None,
                           company_name_initial: str = None) -> Stock:
        stock_id = id or f'{random.randint(100000, 999999)}'
        stock_name = company_name or f'테스트주식{random.randint(1, 100)}'
        stock_name_en = company_name_en or f'Test Stock {random.randint(1, 100)}'
        stock_initial = company_name_initial or f'ㅌㅅㅌㅈㅅ{random.randint(1, 10)}'

        stock = Stock(
            id=stock_id,
            company_name=stock_name,
            company_name_en=stock_name_en,
            company_name_initial=stock_initial,
            listing_date=datetime.date(2000, 1, 1),
            market_type=random.choice(['KOSPI', 'KOSDAQ']),
            security_type='보통주',
            is_active=True,
            shares_outstanding=random.randint(1000000, 10000000)
        )
        session.add(stock)
        await session.flush()
        return stock

    @classmethod
    async def create_stock_price(cls,
                                 session: AsyncSession,
                                 stock_id: str = None,
                                 current_price: float = None) -> StockPrice:
        if not stock_id:
            stock = await cls.create_stock(session)
            stock_id = stock.id

        curr_price = Decimal(str(current_price or random.randint(10000, 100000)))
        prev_price = curr_price * Decimal('0.98')

        price = StockPrice(
            stock_id=stock_id,
            trading_date=datetime.date.today(),
            current_price=curr_price,
            previous_price=prev_price,
            open_price=prev_price * Decimal('1.01'),
            high_price=curr_price * Decimal('1.02'),
            low_price=curr_price * Decimal('0.98'),
            volume=random.randint(10000, 1000000),
            price_change=curr_price - prev_price,
            market_cap=curr_price * Decimal('1000000')
        )
        session.add(price)
        await session.flush()
        return price

    @classmethod
    async def create_industry_hierarchy(cls,
                                        session: AsyncSession,
                                        large_name: str = None,
                                        medium_name: str = None,
                                        small_name: str = None) -> t.Dict[str, t.Any]:
        large = await cls.create_large_industry(session, name=large_name)
        medium = await cls.create_medium_industry(session,
                                                  large_industry_code=large.code,
                                                  name=medium_name)
        small = await cls.create_small_industry(session,
                                                medium_industry_code=medium.code,
                                                name=small_name)

        return {
            "large": large,
            "medium": medium,
            "small": small
        }

    @classmethod
    async def add_industry_mapping(cls,
                                   session: AsyncSession,
                                   stock_id: str,
                                   large_code: str = None,
                                   medium_code: str = None,
                                   small_code: str = None,
                                   is_primary: bool = False):
        if large_code:
            await session.execute(
                stock_large_industry_mapping.insert().values(
                    stock_id=stock_id,
                    large_industry_code=large_code
                )
            )

        if medium_code:
            await session.execute(
                stock_medium_industry_mapping.insert().values(
                    stock_id=stock_id,
                    medium_industry_code=medium_code
                )
            )

        if small_code:
            await session.execute(
                stock_small_industry_mapping.insert().values(
                    stock_id=stock_id,
                    small_industry_code=small_code,
                    is_primary=is_primary
                )
            )

    @classmethod
    async def create_stock_with_price_and_industry(cls,
                                                   session: AsyncSession,
                                                   industry_data: dict,
                                                   company_name: str = None,
                                                   company_name_en: str = None) -> t.Dict[str, t.Any]:
        """주식, 주가, 산업 연결을 한번에 생성"""
        stock = await cls.create_stock(session,
                                       company_name=company_name,
                                       company_name_en=company_name_en)

        price = await cls.create_stock_price(session, stock_id=stock.id)

        await cls.add_industry_mapping(
            session,
            stock.id,
            large_code=industry_data["large"].code,
            medium_code=industry_data["medium"].code,
            small_code=industry_data["small"].code,
            is_primary=True
        )

        return {
            "stock": stock,
            "price": price,
            "industry": industry_data
        }

    @classmethod
    async def create_full_test_data(cls,
                                    session: AsyncSession,
                                    stock_count: int = 2):
        """전체 테스트 데이터 세트 생성"""
        await cls.cleanup_all_data(session)

        # 산업 계층 구조 생성 (기술, 금융)
        industry_tech = await cls.create_industry_hierarchy(
            session,
            large_name="테크놀로지",
            medium_name="소프트웨어개발",
            small_name="기업용소프트웨어"
        )

        industry_finance = await cls.create_industry_hierarchy(
            session,
            large_name="금융",
            medium_name="은행",
            small_name="시중은행"
        )

        # 각 산업별 주식 생성
        tech_stocks = []
        finance_stocks = []

        # 기술 분야 주식 생성
        for i in range(stock_count):
            stock_data = await cls.create_stock_with_price_and_industry(
                session,
                industry_data=industry_tech,
                company_name=f"테크회사{i + 1}",
                company_name_en=f"Tech Company {i + 1}"
            )
            tech_stocks.append(stock_data)

        # 금융 분야 주식 생성
        for i in range(stock_count):
            stock_data = await cls.create_stock_with_price_and_industry(
                session,
                industry_data=industry_finance,
                company_name=f"금융회사{i + 1}",
                company_name_en=f"Finance Company {i + 1}"
            )
            finance_stocks.append(stock_data)

        return {
            "tech_industry": industry_tech,
            "finance_industry": industry_finance,
            "tech_stocks": tech_stocks,
            "finance_stocks": finance_stocks
        }

    @classmethod
    async def cleanup_all_data(cls, session: AsyncSession):
        """모든 테스트 데이터 삭제"""
        try:
            # 맵핑 테이블 데이터 삭제
            await session.execute(stock_small_industry_mapping.delete())
            await session.execute(stock_medium_industry_mapping.delete())
            await session.execute(stock_large_industry_mapping.delete())

            # 테이블 데이터 삭제
            await session.execute(text("DELETE FROM stock_prices"))
            await session.execute(text("DELETE FROM stocks"))
            await session.execute(text("DELETE FROM small_industries"))
            await session.execute(text("DELETE FROM medium_industries"))
            await session.execute(text("DELETE FROM large_industries"))

            await session.commit()
        except Exception as e:
            await session.rollback()
            print(f"데이터 삭제 중 오류 발생: {e}")
            raise