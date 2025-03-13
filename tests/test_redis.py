import enum

import pytest
import ujson
from unittest.mock import AsyncMock, MagicMock
from trader.context.redis.ctx import RedisContext


class MockRedisKey(str, enum.Enum):
    SIMPLE_KEY = "test:simple:{param}"
    HASH_KEY = "test:hash"


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.REDIS.HOST = "localhost"
    config.REDIS.PORT = 6379
    config.REDIS.DB = 0
    config.REDIS.PASSWORD = None
    return config


@pytest.fixture
def mock_redis():
    redis_mock = AsyncMock()
    redis_mock.set = AsyncMock()
    redis_mock.get = AsyncMock()
    redis_mock.delete = AsyncMock()
    redis_mock.hset = AsyncMock()
    redis_mock.hget = AsyncMock()
    redis_mock.hdel = AsyncMock()
    redis_mock.close = MagicMock()
    redis_mock.wait_closed = AsyncMock()
    return redis_mock


@pytest.fixture
def redis_context(mock_config, mock_redis):
    ctx = RedisContext(
        config=mock_config,
        redis=mock_redis
    )
    return ctx


@pytest.mark.asyncio
async def test_shutdown(redis_context, mock_redis):
    await redis_context.shutdown()

    mock_redis.close.assert_called_once()
    mock_redis.wait_closed.assert_called_once()


@pytest.mark.asyncio
async def test_jset(redis_context, mock_redis):
    # Given
    key = MockRedisKey.SIMPLE_KEY
    test_data = {"name": "test", "value": 123}
    param_value = "param1"
    expire_time = 3600

    # When
    await redis_context.jset(key, test_data, param=param_value, expire=expire_time)

    # Then
    mock_redis.set.assert_called_once_with(
        key=key.value.format(param=param_value),
        value=ujson.dumps(test_data),
        expire=expire_time
    )


@pytest.mark.asyncio
async def test_jget(redis_context, mock_redis):
    # Given
    key = MockRedisKey.SIMPLE_KEY
    test_data = {"name": "test", "value": 123}
    param_value = "param1"
    mock_redis.get.return_value = ujson.dumps(test_data)

    # When
    result = await redis_context.jget(key, param=param_value)

    # Then
    mock_redis.get.assert_called_once_with(
        key=key.value.format(param=param_value),
        encoding="utf-8"
    )
    assert result == test_data


@pytest.mark.asyncio
async def test_jget_none(redis_context, mock_redis):
    # Given
    key = MockRedisKey.SIMPLE_KEY
    param_value = "param1"
    mock_redis.get.return_value = None

    # When
    result = await redis_context.jget(key, param=param_value)

    # Then
    mock_redis.get.assert_called_once_with(
        key=key.value.format(param=param_value),
        encoding="utf-8"
    )
    assert result is None


@pytest.mark.asyncio
async def test_delete(redis_context, mock_redis):
    # Given
    key = MockRedisKey.SIMPLE_KEY
    param_value = "param1"

    # When
    await redis_context.delete(key, param=param_value)

    # Then
    mock_redis.delete.assert_called_once_with(
        key=key.value.format(param=param_value)
    )


@pytest.mark.asyncio
async def test_hset(redis_context, mock_redis):
    # Given
    key = MockRedisKey.HASH_KEY
    field = "test_field"
    test_data = {"name": "test", "value": 123}

    # When
    await redis_context.hset(key, field, test_data)

    # Then
    mock_redis.hset.assert_called_once_with(
        key=key.value,
        field=field,
        value=ujson.dumps(test_data)
    )


@pytest.mark.asyncio
async def test_hget(redis_context, mock_redis):
    # Given
    key = MockRedisKey.HASH_KEY
    field = "test_field"
    test_data = {"name": "test", "value": 123}
    mock_redis.hget.return_value = ujson.dumps(test_data)

    # When
    result = await redis_context.hget(key, field)

    # Then
    mock_redis.hget.assert_called_once_with(
        key=key.value,
        field=field,
        encoding="utf-8"
    )
    assert result == test_data


@pytest.mark.asyncio
async def test_hget_none(redis_context, mock_redis):
    # Given
    key = MockRedisKey.HASH_KEY
    field = "test_field"
    mock_redis.hget.return_value = None

    # When
    result = await redis_context.hget(key, field)

    # Then
    mock_redis.hget.assert_called_once_with(
        key=key.value,
        field=field,
        encoding="utf-8"
    )
    assert result is None


@pytest.mark.asyncio
async def test_hdel(redis_context, mock_redis):
    # Given
    key = MockRedisKey.HASH_KEY
    field = "test_field"

    # When
    await redis_context.hdel(key, field)

    # Then
    mock_redis.hdel.assert_called_once_with(
        key=key.value,
        field=field
    )