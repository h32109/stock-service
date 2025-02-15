from contextlib import asynccontextmanager

from fastapi import FastAPI

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.cors import CORSMiddleware

from trader.config import init_config
from trader.context.db.ctx import SQLContext
from trader.context.redis.ctx import RedisContext
from trader.middleware import DBSessionMiddleware
from trader.models import get_models
from trader.routes import create_routers
from trader.service import Service


def get_trader_config():
    return init_config(service_name="trader")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_context()
    await setup_service_manager(get_trader_config())
    yield


def create_app() -> FastAPI:
    config = get_trader_config()
    app = FastAPI(
        version=config.API_VERSION,
        docs_url="/docs" if config.is_dev else None,
        lifespan=lifespan
    )
    setup_context(config)
    setup_routers(app)
    setup_middlewares(app)
    return app


def setup_routers(app: FastAPI):
    api_router, view_router = create_routers()
    app.include_router(api_router)
    app.include_router(view_router)


def setup_middlewares(app):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    from trader.globals import sql
    app.add_middleware(
        DBSessionMiddleware,
        run_session=sql.run_session
    )


async def setup_service_manager(config):
    await Service.init(config)


def setup_context(config):
    SQLContext.init(
        config=config,
        models=get_models(),
        session_maker_args={"class_": AsyncSession})
    RedisContext.init(
        config=config
    )


async def start_context():
    from trader.globals import sql, redis
    await sql.start()
    await redis.start()
