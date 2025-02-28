import pytest
from unittest.mock import AsyncMock, MagicMock

from trader.context.kafka.ctx import KafkaProducerContext
from trader.context.kafka.model import Data


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.KAFKA.HOSTS = ["localhost:9092"]
    return config


@pytest.fixture
def mock_producer():
    producer_mock = AsyncMock()
    producer_mock.start = AsyncMock()
    producer_mock.stop = AsyncMock()
    producer_mock.send = AsyncMock()
    return producer_mock


@pytest.fixture
def mock_data():
    data_mock = MagicMock(spec=Data)

    async def mock_chunk(chunk_size=0):
        yield data_mock

    data_mock.chunk = mock_chunk
    data_mock.dict.return_value = {"message": "test message"}

    return data_mock


@pytest.fixture
def kafka_context(mock_config, mock_producer):
    ctx = KafkaProducerContext(
        config=mock_config,
        producer=mock_producer
    )
    return ctx


@pytest.mark.asyncio
async def test_start(kafka_context, mock_producer):
    await kafka_context.start()
    mock_producer.start.assert_called_once()


@pytest.mark.asyncio
async def test_shutdown(kafka_context, mock_producer):
    await kafka_context.shutdown()
    mock_producer.stop.assert_called_once()


@pytest.mark.asyncio
async def test_send_single_chunk(kafka_context, mock_producer, mock_data):
    topic = "test-topic"
    key = "test-key"

    await kafka_context.send(topic=topic, data=mock_data, key=key)

    mock_producer.send.assert_called_once_with(
        topic=topic,
        key=key,
        value=mock_data.dict()
    )


@pytest.mark.asyncio
async def test_send_no_key(kafka_context, mock_producer, mock_data):
    topic = "test-topic"

    await kafka_context.send(topic=topic, data=mock_data)

    mock_producer.send.assert_called_once_with(
        topic=topic,
        key=None,
        value=mock_data.dict()
    )


@pytest.mark.asyncio
async def test_send_multiple_chunks(kafka_context, mock_producer):
    topic = "test-topic"
    key = "test-key"
    chunk_size = 2

    chunks = [
        {"chunk": 1},
        {"chunk": 2},
        {"chunk": 3}
    ]

    data_mock = MagicMock(spec=Data)

    async def mock_multi_chunk(chunk_size=0):
        for chunk_data in chunks:
            chunk_mock = MagicMock(spec=Data)
            chunk_mock.dict.return_value = chunk_data
            yield chunk_mock

    data_mock.chunk = mock_multi_chunk

    await kafka_context.send(topic=topic, data=data_mock, key=key, chunk_size=chunk_size)

    assert mock_producer.send.call_count == 3

    for i, chunk_data in enumerate(chunks):
        mock_producer.send.assert_any_call(
            topic=topic,
            key=key,
            value=chunk_data
        )
