from contextlib import asynccontextmanager

from fastapi import FastAPI

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.cors import CORSMiddleware

from trader.core.config import settings
from trader.context.db.ctx import SQLContext
from trader.middleware import DBSessionMiddleware
from trader.models import get_models
from trader.routes import create_routers
from trader.service import Service


@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_context()
    await setup_service_manager(settings)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        version=settings.APP_VERSION,
        docs_url="/docs" if settings.is_dev else None,
        lifespan=lifespan
    )
    setup_context(settings)
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
    from trader.globals import postgresql
    app.add_middleware(
        DBSessionMiddleware,
        run_session=postgresql.run_session
    )


async def setup_service_manager(settings):
    await Service.init(settings)


def setup_context(settings):
    SQLContext.init(
        settings=settings,
        models=get_models(),
        session_maker_args={"class_": AsyncSession})


async def start_context():
    from trader.globals import postgresql
    await postgresql.start()
