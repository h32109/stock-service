from fastapi import APIRouter
from typing import Tuple

from trader.stock.endpoints import router as stock_router


def create_routers() -> Tuple[APIRouter, APIRouter]:
    api = APIRouter()
    view = APIRouter()

    router_configs = [
        (api, stock_router, '', ["stock"]),
    ]

    for p, c, prefix, tags in router_configs:
        p.include_router(c, prefix=prefix, tags=tags)

    return api, view
