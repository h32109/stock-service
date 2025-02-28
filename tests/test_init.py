import pytest


@pytest.mark.asyncio
async def test_kafka_producer_ctx_initialize(kafka_producer_ctx):
    assert kafka_producer_ctx._producer is not None


@pytest.mark.asyncio
async def test_es_ctx_initialize(es_ctx):
    assert es_ctx._es is not None


@pytest.mark.asyncio
async def test_sql_ctx_initialize(sql_ctx):
    assert sql_ctx._session_maker is not None
    assert sql_ctx._connection is not None


@pytest.mark.asyncio
async def test_redis_ctx_initialize(redis_ctx):
    assert redis_ctx._redis is not None
