from fastapi import APIRouter

from trader.stock.endpoints import router as stock_router


def create_routers() -> APIRouter:
    api = APIRouter()

    router_configs = [
        (api, stock_router, '', ["stock"]),
    ]

    for p, c, prefix, tags in router_configs:
        p.include_router(c, prefix=prefix, tags=tags)

    return api
