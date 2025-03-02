import asyncio
import os
import sys
import logging
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from trader import get_models

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

os.environ["TRADER_ENVIRONMENT"] = "test"

async def test_stock_crawler():
    try:
        from trader.config import init_config

        config = init_config()

        from trader.context.db.ctx import SQLContext
        SQLContext.init(
            config=config,
            models=get_models(),
            session_maker_args={"class_": AsyncSession}
        )

        from trader.globals import sql
        await sql.start()

        from trader.requestor import Requestor

        requestor = Requestor(config=config)

        from trader.context.celery.ctx import CeleryContext
        celery = CeleryContext.init(config, requestor=requestor)
        await celery.start()

        test_stock_codes = ["005930", "035420"]  # 삼성전자, NAVER

        logger.info("테스트 1: 종목 기본 정보 수집")
        for code in test_stock_codes:
            info = await celery.get_stock_info(code)
            if info:
                logger.info(f"종목 {code} 정보 조회 성공: {info.get('prdt_name', '')}")
                await celery._save_stock_info_to_db(code, info)
                logger.info(f"종목 {code} 정보 DB 저장 완료")
            else:
                logger.error(f"종목 {code} 정보 조회 실패")

            await asyncio.sleep(1)

        logger.info("\n테스트 2: 종목 가격 데이터 수집")
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")

        for code in test_stock_codes:
            price_data = await celery.get_stock_price(code, start_date, end_date, "D")
            if price_data:
                logger.info(f"종목 {code} 가격 데이터 조회 성공: {len(price_data.get('price_data', []))}개 데이터")
                await celery._save_stock_price_to_db(code, price_data)
                logger.info(f"종목 {code} 가격 데이터 DB 저장 완료")
            else:
                logger.error(f"종목 {code} 가격 데이터 조회 실패")

            await asyncio.sleep(1)

        await celery.shutdown()
        await sql.shutdown()

        logger.info("테스트 완료!")

    except Exception as e:
        logger.exception(f"테스트 중 오류 발생: {str(e)}")


if __name__ == "__main__":
    asyncio.run(test_stock_crawler())