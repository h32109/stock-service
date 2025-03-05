import fastapi as fa

from trader import exceptions, status
from trader.stock.schema import SearchResponse, DetailResponse
from trader.stock.service import stock_service

router = fa.APIRouter()


@router.get("/stocks", response_model=SearchResponse)
async def search(
        q: str = fa.Query(..., min_length=1, max_length=20, description="검색어 (회사명, 초성, 종목코드, 테마명)"),
        page: int = fa.Query(1, ge=1, description="페이지 번호"),
        size: int = fa.Query(20, ge=1, le=100, description="페이지 크기")
):
    try:
        stocks, total = await stock_service.search(query=q, page=page, size=size)
    except exceptions.BaseCustomException as e:
        raise e.raise_http(status_code=status.ClientError.HTTP_400_BAD_REQUEST)
    except Exception as e:
        raise e
    return {
            "data": {
                "stocks": stocks,
                "total_count": total
            }
    }


@router.get("/stocks/{stock_id}", response_model=DetailResponse)
async def get_stock(
        stock_id: str = fa.Path(..., description="주식 종목 코드")
):
    try:
        stock = await stock_service.get_stock(stock_id=stock_id)
    except exceptions.BaseCustomException as e:
        raise e.raise_http(status_code=status.ClientError.HTTP_400_BAD_REQUEST)
    except Exception as e:
        raise e
    return {"data": stock}
