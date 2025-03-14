import fastapi as fa
from fastapi import Path, Query, HTTPException, status

from trader import exceptions, status as app_status
from trader.stock.schema import (
    StockSearchSuccessResponse,
    StockDetailSuccessResponse
)
from trader.stock.service import stock_service

router = fa.APIRouter()


@router.get("/stocks", response_model=StockSearchSuccessResponse)
async def search(
        q: str = Query(..., min_length=1, max_length=20, description="검색어 (회사명, 초성, 종목코드, 테마명)"),
        page: int = Query(1, ge=1, description="페이지 번호"),
        size: int = Query(20, ge=1, le=100, description="페이지 크기")
):
    try:
        stocks, total = await stock_service.search(query=q, page=page, size=size)
        return {
            "data": {
                "stocks": stocks,
                "total_count": total
            }
        }
    except exceptions.BaseCustomException as e:
        raise e.raise_http(status_code=app_status.ClientError.HTTP_400_BAD_REQUEST)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to search stocks", "details": str(e)}
        )


@router.get("/stocks/{stock_id}", response_model=StockDetailSuccessResponse)
async def get_stock(
        stock_id: str = Path(..., description="주식 종목 코드")
):
    try:
        stock = await stock_service.get_stock(stock_id=stock_id)
        return {"data": stock}
    except exceptions.BaseCustomException as e:
        raise e.raise_http(status_code=app_status.ClientError.HTTP_400_BAD_REQUEST)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Failed to get stock details", "details": str(e)}
        )