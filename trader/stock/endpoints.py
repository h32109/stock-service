import fastapi as fa
import typing as t

from trader.stock.service import (
    stock_service
)

router = fa.APIRouter()


@router.get("/")
async def search_company_name(
):
    return "hello world"