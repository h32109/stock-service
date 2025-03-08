import asyncio
import os

import pytest
from async_asgi_testclient import TestClient
from trader.globals import sql, es, redis, producer

os.environ["TRADER_ENVIRONMENT"] = "test"


@pytest.fixture(scope="session")
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture
def get_service():
    from trader.service import Service

    def _get_service(service_name):
        return Service.get(service_name)

    return _get_service


@pytest.fixture(scope="session")
def sql_ctx(app):
    sql.set_session()
    yield sql


@pytest.fixture(scope="session")
def es_ctx(app):
    yield es


@pytest.fixture(scope="session")
def redis_ctx(app):
    yield redis


@pytest.fixture(scope="session")
def kafka_producer_ctx(app):
    yield producer


@pytest.fixture(scope="session")
async def app(event_loop):
    from trader import create_app
    os.environ["TRADER_ENVIRONMENT"] = "test"
    app_instance = create_app()
    yield app_instance


@pytest.fixture(scope="session")
async def client(app):
    async with TestClient(app) as client:
        yield client


@pytest.fixture(scope="session")
def trader_config():
    from trader.config import init_config
    os.environ["TRADER_ENVIRONMENT"] = "test"
    return init_config()


@pytest.fixture(scope="session")
def trader_api_version(trader_config):
    return trader_config.API_PREFIX.lstrip("/")
