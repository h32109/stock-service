import typing as t
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from pprint import pprint

from celery import Celery
from celery.schedules import crontab
from sqlalchemy import select

from trader.context.base import Context
from trader.context.celery import logger
from trader.globals import transaction, sql
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
from trader.utils import extract_initial_sound


class CeleryContext(Context):
    settings: t.Any
    _celery_app: t.Optional[Celery]
    _requestor: t.Any
    _access_token = None
    _token_expire_time = None

    def __init__(
            self,
            config,
            celery_app=None,
            requestor=None,
    ):
        self.config = config
        self._celery_app = celery_app
        self._requestor = requestor
        self._access_token = None
        self._token_expire_time = None

    @classmethod
    def init(
            cls,
            config,
            requestor=None,
            **kwargs
    ):
        celery_app = Celery('trader')

        from trader.context.celery import get_celery_config
        celery_app.conf.update(get_celery_config(config))

        celery_app.autodiscover_tasks(['trader.context.stock_crawler'])

        @celery_app.on_after_configure.connect
        def setup_periodic_tasks(sender, **kwargs):
            pass

        @celery_app.task(bind=True)
        def debug_task(self):
            print(f'Request: {self.request!r}')

        ctx = CeleryContext(
            config=config,
            celery_app=celery_app,
            requestor=requestor,
        )
        ctx.register("stock_crawler", ctx)
        return ctx

    async def start(self):
        self._register_tasks()
        await self._requestor.create_session()

    async def shutdown(self):
        pass

    def _register_tasks(self):
        stock_info_schedule = self.config.CELERY.SCHEDULE_STOCK_INFO
        schedule_stock_price = self.config.CELERY.SCHEDULE_STOCK_PRICE

        crawl_stock_info = self._celery_app.task(
            bind=True,
            name='celery.crawl_stock_info'
        )(self.crawl_stock_info)

        self._celery_app.add_periodic_task(
            crontab(**stock_info_schedule),
            crawl_stock_info.s(),
            name='crawl_stock_info'
        )

        crawl_stock_price = self._celery_app.task(
            bind=True,
            name='celery.crawl_stock_price'
        )(self.crawl_stock_price)

        self._celery_app.add_periodic_task(
            crontab(**schedule_stock_price),
            crawl_stock_price.s(),
            name='crawl_stock_price'
        )

    async def get_access_token(self) -> str:
        """접근 토큰 발급 또는 캐시된 토큰 반환"""
        now = datetime.now()

        if not self._access_token or not self._token_expire_time or now >= self._token_expire_time:
            url = "https://openapi.koreainvestment.com:9443/oauth2/tokenP"

            headers = {
                "content-type": "application/json; charset=utf-8"
            }

            data = {
                "grant_type": "client_credentials",
                "appkey": self.config.KIS.APP_KEY,
                "appsecret": self.config.KIS.SECRET_KEY
            }

            response = await self._requestor.request(
                method="POST",
                url=url,
                json=data,
                headers=headers
            )

            if response.status != 200:
                error_text = await response.json()
                logger.error(f"Failed to get access token: {error_text}")
                raise Exception(f"Failed to get access token: {response.status}")

            result = await response.json()
            self._access_token = result.get("access_token")
            expires_in = result.get("expires_in", self.config.KLS.DEFAULT_TOKEN_EXPIRE_TIME)  # 기본값 1일
            self._token_expire_time = now + timedelta(seconds=expires_in)

            logger.info(f"Access token acquired, expires at {self._token_expire_time}")

        return self._access_token

    async def get_stock_info(self, stock_code: str) -> t.Dict[str, t.Any]:
        try:
            token = await self.get_access_token()
            url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/search-stock-info"

            headers = {
                "content-type": "application/json; charset=utf-8",
                "authorization": f"Bearer {token}",
                "appkey": self.config.KIS.APP_KEY,
                "appsecret": self.config.KIS.SECRET_KEY,
                "tr_id": "CTPF1002R",
                "custtype": "P"  # 개인
            }

            params = {
                "PRDT_TYPE_CD": "300",  # 주식, ETF, ETN, ELW
                "PDNO": stock_code
            }

            response = await self._requestor.request(
                method="GET",
                url=url,
                params=params,
                headers=headers
            )

            if response.status != 200:
                error_text = await response.json()
                logger.error(f"Failed to get stock info for {stock_code}: {error_text}")
                return None

            result = await response.json()
            if result.get("rt_cd") != "0":
                logger.error(f"API error: {result.get('msg1')}")
                return None

            return result.get("output", {})
        except Exception as e:
            logger.exception(f"Error getting stock info for {stock_code}: {str(e)}")
            return None

    async def get_stock_price(self, stock_code: str, start_date: str, end_date: str, period: str = "D"):
        try:
            token = await self.get_access_token()
            url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/inquire-daily-price"

            headers = {
                "content-type": "application/json; charset=utf-8",
                "authorization": f"Bearer {token}",
                "appkey": self.config.KIS.APP_KEY,
                "appsecret": self.config.KIS.SECRET_KEY,
                "tr_id": "FHKST03010100",
                "custtype": "P"  # 개인
            }

            params = {
                "FID_COND_MRKT_DIV_CODE": "J",  # 주식, ETF, ETN
                "FID_INPUT_ISCD": stock_code,
                "FID_INPUT_DATE_1": start_date,
                "FID_INPUT_DATE_2": end_date,
                "FID_PERIOD_DIV_CODE": period,  # D:일봉, W:주봉, M:월봉, Y:년봉
                "FID_ORG_ADJ_PRC": "0"  # 수정주가
            }

            response = await self._requestor.request(
                method="GET",
                url=url,
                params=params,
                headers=headers
            )

            if response.status != 200:
                error_text = await response.json()
                logger.error(f"Failed to get stock price for {stock_code}: {error_text}")
                return None

            result = await response.json()
            if result.get("rt_cd") != "0":
                logger.error(f"API error: {result.get('msg1')}")
                return None

            return {
                "stock_info": result.get("output1", {}),
                "price_data": result.get("output2", [])
            }
        except Exception as e:
            logger.exception(f"Error getting stock price for {stock_code}: {str(e)}")
            return None

    def crawl_stock_info(self, stock_codes: t.List[str] = None):
        stock_codes = stock_codes or self.config.STOCK_CRAWLER.STOCK_CODES

        async def _crawl():
            for code in stock_codes:
                info = await self.get_stock_info(code)
                if info:
                    await self._save_stock_info_to_db(code, info)
                    logger.info(f"Stock info for {code} crawled successfully")

                await asyncio.sleep(0.5)

        asyncio.run(_crawl())
        return "Stock info crawling completed"

    def crawl_stock_price(self, stock_codes: t.List[str] = None, days: int = 7):
        stock_codes = stock_codes or self.config.STOCK_CRAWLER.STOCK_CODES

        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")

        async def _crawl():
            for code in stock_codes:
                price_data = await self.get_stock_price(code, start_date, end_date)
                if price_data:
                    await self._save_stock_price_to_db(code, price_data)
                    logger.info(f"Stock price data for {code} from {start_date} to {end_date} crawled successfully")

                await asyncio.sleep(0.5)

        asyncio.run(_crawl())
        return "Stock price crawling completed"


    @transaction
    async def _save_stock_info_to_db(self, stock_code: str, info: t.Dict[str, t.Any]):
        try:
            small_industry_code = info.get("std_idst_clsf_cd", "000000")
            small_industry_name = info.get("std_idst_clsf_cd_name", "해당사항없음")

            medium_industry_code = info.get("idx_bztp_mcls_cd", "000")
            medium_industry_name = info.get("idx_bztp_mcls_cd_name", "해당사항없음")

            large_industry_code = info.get("idx_bztp_scls_cd", "000")
            large_industry_name = info.get("idx_bztp_scls_cd_name", "해당사항없음")

            large_industry = await sql.session.get(LargeIndustry, large_industry_code)
            if not large_industry:
                large_industry = LargeIndustry(
                    code=large_industry_code,
                    name=large_industry_name
                )
                sql.session.add(large_industry)
                await sql.session.flush()

            medium_industry = await sql.session.get(MediumIndustry, medium_industry_code)
            if not medium_industry:
                medium_industry = MediumIndustry(
                    code=medium_industry_code,
                    name=medium_industry_name,
                    large_industry_code=large_industry_code
                )
                sql.session.add(medium_industry)
                await sql.session.flush()

            small_industry = await sql.session.get(SmallIndustry, small_industry_code)
            if not small_industry:
                small_industry = SmallIndustry(
                    code=small_industry_code,
                    name=small_industry_name,
                    medium_industry_code=medium_industry_code
                )
                sql.session.add(small_industry)
                await sql.session.flush()

            market_type = "KOSPI" if info.get("mket_id_cd", "") == "STK" else "KOSDAQ"
            security_type = "보통주" if info.get("stck_kind_cd", "") == "101" else "우선주"

            listing_date_str = info.get("scts_mket_lstg_dt", "") or info.get("kosdaq_mket_lstg_dt", "")
            listing_date = datetime.strptime(listing_date_str,
                                             "%Y%m%d").date() if listing_date_str else datetime.now().date()

            stock = await sql.session.get(Stock, stock_code)
            pprint(info)

            if not stock:
                stock = Stock(
                    id=stock_code,
                    company_name=info.get("prdt_abrv_name", ""),
                    company_name_en=info.get("prdt_eng_name", ""),
                    company_name_initial=extract_initial_sound(info.get("prdt_abrv_name", "")),  # 회사명 약어
                    listing_date=listing_date,
                    market_type=market_type,
                    security_type=security_type,
                    is_active=True,
                    shares_outstanding=int(info.get("lstg_stcn", 0) or 0)
                )
                sql.session.add(stock)
                await sql.session.flush()
            else:
                stock.company_name = info.get("prdt_abrv_name", "")
                stock.company_name_en = info.get("prdt_eng_name", "")
                stock.listing_date = listing_date
                stock.market_type = market_type
                stock.security_type = security_type
                stock.shares_outstanding = int(info.get("lstg_stcn", 0) or 0)
                stock.updated_dt = datetime.now()

            stmt = select(stock_small_industry_mapping).where(
                stock_small_industry_mapping.c.stock_id == stock_code,
                stock_small_industry_mapping.c.is_primary == True
            )
            result = await sql.session.execute(stmt)
            existing_primary = result.first()

            stmt = select(stock_small_industry_mapping).where(
                stock_small_industry_mapping.c.stock_id == stock_code,
                stock_small_industry_mapping.c.small_industry_code == small_industry_code
            )
            result = await sql.session.execute(stmt)
            existing_mapping = result.first()

            if not existing_mapping:
                await sql.session.execute(
                    stock_small_industry_mapping.insert().values(
                        stock_id=stock_code,
                        small_industry_code=small_industry_code,
                        is_primary=True if not existing_primary else False,
                        created_dt=datetime.now()
                    )
                )
            elif not existing_primary:
                await sql.session.execute(
                    stock_small_industry_mapping.update().where(
                        stock_small_industry_mapping.c.stock_id == stock_code,
                        stock_small_industry_mapping.c.small_industry_code == small_industry_code
                    ).values(
                        is_primary=True
                    )
                )

            stmt = select(stock_medium_industry_mapping).where(
                stock_medium_industry_mapping.c.stock_id == stock_code,
                stock_medium_industry_mapping.c.medium_industry_code == medium_industry_code
            )
            result = await sql.session.execute(stmt)
            existing_medium_mapping = result.first()

            if not existing_medium_mapping:
                await sql.session.execute(
                    stock_medium_industry_mapping.insert().values(
                        stock_id=stock_code,
                        medium_industry_code=medium_industry_code,
                        created_dt=datetime.now()
                    )
                )

            stmt = select(stock_large_industry_mapping).where(
                stock_large_industry_mapping.c.stock_id == stock_code,
                stock_large_industry_mapping.c.large_industry_code == large_industry_code
            )
            result = await sql.session.execute(stmt)
            existing_large_mapping = result.first()

            if not existing_large_mapping:
                await sql.session.execute(
                    stock_large_industry_mapping.insert().values(
                        stock_id=stock_code,
                        large_industry_code=large_industry_code,
                        created_dt=datetime.now()
                    )
                )

            await sql.session.flush()
        except Exception as e:
            logger.exception(f"Error saving stock info to database: {str(e)}")
            raise

    @transaction
    async def _save_stock_price_to_db(self, stock_code: str, price_data: t.Dict[str, t.Any]):
        try:
            stock = await sql.session.get(Stock, stock_code)
            if not stock:
                logger.error(f"Stock {stock_code} not found in database")
                return

            for price_item in price_data.get("price_data", []):
                trading_date_str = price_item.get("stck_bsop_date", "")
                if not trading_date_str:
                    continue

                trading_date = datetime.strptime(trading_date_str, "%Y%m%d").date()

                # 이미 해당 날짜의 가격 데이터가 있는지 확인
                from sqlalchemy import select
                existing_price_query = select(StockPrice).where(
                    StockPrice.stock_id == stock_code,
                    StockPrice.trading_date == trading_date
                )
                existing_price = await sql.session.execute(existing_price_query)
                existing_price = existing_price.scalar_one_or_none()

                if existing_price:
                    existing_price.current_price = Decimal(price_item.get("stck_clpr", 0) or 0)
                    existing_price.previous_price = Decimal(price_item.get("stck_lwpr", 0) or 0)
                    existing_price.open_price = Decimal(price_item.get("stck_oprc", 0) or 0)
                    existing_price.high_price = Decimal(price_item.get("stck_hgpr", 0) or 0)
                    existing_price.low_price = Decimal(price_item.get("stck_lwpr", 0) or 0)
                    existing_price.volume = int(price_item.get("acml_vol", 0) or 0)
                    existing_price.price_change = Decimal(price_item.get("prdy_vrss", 0) or 0)
                    # 시가총액 = 종가 * 발행주식수
                    existing_price.market_cap = Decimal(
                        price_item.get("stck_clpr", 0) or 0) * stock.shares_outstanding
                    existing_price.updated_dt = datetime.now()
                else:
                    new_price = StockPrice(
                        stock_id=stock_code,
                        trading_date=trading_date,
                        current_price=Decimal(price_item.get("stck_clpr", 0) or 0),
                        previous_price=Decimal(price_item.get("stck_lwpr", 0) or 0),
                        open_price=Decimal(price_item.get("stck_oprc", 0) or 0),
                        high_price=Decimal(price_item.get("stck_hgpr", 0) or 0),
                        low_price=Decimal(price_item.get("stck_lwpr", 0) or 0),
                        volume=int(price_item.get("acml_vol", 0) or 0),
                        price_change=Decimal(price_item.get("prdy_vrss", 0) or 0),
                        market_cap=Decimal(price_item.get("stck_clpr", 0) or 0) * stock.shares_outstanding
                    )
                    sql.session.add(new_price)

            await sql.session.flush()
        except Exception as e:
            logger.exception(f"Error saving stock price to database: {str(e)}")
            raise

    async def get_stocks_info(self, stock_codes: t.List[str]):
        results = {}
        for code in stock_codes:
            info = await self.get_stock_info(code)
            if info:
                results[code] = info
            await asyncio.sleep(0.5)
        return results

    async def get_stocks_price(self, stock_codes: t.List[str], start_date: str, end_date: str, period: str = "D"):
        results = {}
        for code in stock_codes:
            price_data = await self.get_stock_price(code, start_date, end_date, period)
            if price_data:
                results[code] = price_data
            await asyncio.sleep(0.5)
        return results