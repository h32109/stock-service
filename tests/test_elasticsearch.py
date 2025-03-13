import pytest
import enum
from unittest.mock import AsyncMock, MagicMock, patch

from trader.context.elasticsearch.ctx import ElasticsearchContext


class MockElasticsearchIndex(str, enum.Enum):
    TEST_INDEX = "test-index-{param}"
    SIMPLE_INDEX = "simple-index"


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.ELASTICSEARCH.HOSTS = ["http://localhost:9200"]
    config.ELASTICSEARCH.USERNAME = "test_user"
    config.ELASTICSEARCH.PASSWORD = "test_password"
    return config


@pytest.fixture
def mock_elasticsearch():
    es_mock = AsyncMock()
    es_mock.index = AsyncMock()
    es_mock.get = AsyncMock()
    es_mock.search = AsyncMock()
    es_mock.delete = AsyncMock()
    es_mock.update = AsyncMock()
    es_mock.bulk = AsyncMock()
    es_mock.close = AsyncMock()

    es_mock.indices = AsyncMock()
    es_mock.indices.create = AsyncMock()
    es_mock.indices.delete = AsyncMock()

    return es_mock


@pytest.fixture
def es_context(mock_config, mock_elasticsearch):
    ctx = ElasticsearchContext(
        config=mock_config,
        elasticsearch=mock_elasticsearch
    )
    return ctx


@pytest.mark.asyncio
async def test_shutdown(es_context, mock_elasticsearch):
    await es_context.shutdown()
    mock_elasticsearch.close.assert_called_once()


@pytest.mark.asyncio
async def test_get_index(es_context, mock_elasticsearch):
    # Given
    index = MockElasticsearchIndex.TEST_INDEX
    document = {"field1": "value1", "field2": 123}
    param_value = "test1"

    # When
    await es_context.index(index, document, param=param_value)

    # Then
    mock_elasticsearch.index.assert_called_once_with(
        index=index.value.format(param=param_value),
        document=document,
        param=param_value
    )


@pytest.mark.asyncio
async def test_document_get_success(es_context, mock_elasticsearch):
    # Given
    index = MockElasticsearchIndex.TEST_INDEX
    doc_id = "doc123"
    param_value = "test1"
    source_data = {"field1": "value1", "field2": 123}
    mock_elasticsearch.get.return_value = {"_source": source_data}

    # When
    result = await es_context.eget(index, doc_id, param=param_value)

    # Then
    mock_elasticsearch.get.assert_called_once_with(
        index=index.value.format(param=param_value),
        id=doc_id,
        param=param_value
    )
    assert result == source_data


@pytest.mark.asyncio
async def test_document_get_exception(es_context, mock_elasticsearch):
    # Given
    index = MockElasticsearchIndex.TEST_INDEX
    doc_id = "doc123"
    param_value = "test1"
    mock_elasticsearch.get.side_effect = Exception("Document not found")

    # When
    result = await es_context.eget(index, doc_id, param=param_value)

    # Then
    mock_elasticsearch.get.assert_called_once_with(
        index=index.value.format(param=param_value),
        id=doc_id,
        param=param_value
    )
    assert result is None


@pytest.mark.asyncio
async def test_search_document_success(es_context, mock_elasticsearch):
    # Given
    index = MockElasticsearchIndex.TEST_INDEX
    query = {"query": {"match": {"field1": "value1"}}}
    param_value = "test1"
    search_results = {
        "hits": {
            "total": {"value": 1},
            "hits": [{"_source": {"field1": "value1", "field2": 123}}]
        }
    }
    mock_elasticsearch.search.return_value = search_results

    # When
    result = await es_context.search(index, query, param=param_value)

    # Then
    mock_elasticsearch.search.assert_called_once_with(
        index=index.value.format(param=param_value),
        body=query,
        param=param_value
    )
    assert result == search_results


@pytest.mark.asyncio
async def test_search_document_exception(es_context, mock_elasticsearch):
    # Given
    index = MockElasticsearchIndex.TEST_INDEX
    query = {"query": {"match": {"field1": "value1"}}}
    param_value = "test1"
    mock_elasticsearch.search.side_effect = Exception("Search failed")

    # When
    result = await es_context.search(index, query, param=param_value)

    # Then
    mock_elasticsearch.search.assert_called_once_with(
        index=index.value.format(param=param_value),
        body=query,
        param=param_value
    )
    assert result is None


@pytest.mark.asyncio
async def test_delete_document_success(es_context, mock_elasticsearch):
    # Given
    index = MockElasticsearchIndex.TEST_INDEX
    doc_id = "doc123"
    param_value = "test1"
    delete_result = {"result": "deleted"}
    mock_elasticsearch.delete.return_value = delete_result

    # When
    result = await es_context.delete(index, doc_id, param=param_value)

    # Then
    mock_elasticsearch.delete.assert_called_once_with(
        index=index.value.format(param=param_value),
        id=doc_id,
        param=param_value
    )
    assert result == delete_result


@pytest.mark.asyncio
async def test_delete_document_exception(es_context, mock_elasticsearch):
    # Given
    index = MockElasticsearchIndex.TEST_INDEX
    doc_id = "doc123"
    param_value = "test1"
    mock_elasticsearch.delete.side_effect = Exception("Delete failed")

    # When
    result = await es_context.delete(index, doc_id, param=param_value)

    # Then
    mock_elasticsearch.delete.assert_called_once_with(
        index=index.value.format(param=param_value),
        id=doc_id,
        param=param_value
    )
    assert result is None


@pytest.mark.asyncio
async def test_update_document_success(es_context, mock_elasticsearch):
    # Given
    index = MockElasticsearchIndex.TEST_INDEX
    doc_id = "doc123"
    document = {"field1": "updated_value"}
    param_value = "test1"
    update_result = {"result": "updated"}
    mock_elasticsearch.update.return_value = update_result

    # When
    result = await es_context.update(index, doc_id, document, param=param_value)

    # Then
    mock_elasticsearch.update.assert_called_once_with(
        index=index.value.format(param=param_value),
        id=doc_id,
        body={'doc': document},
        param=param_value
    )
    assert result == update_result


@pytest.mark.asyncio
async def test_update_document_exception(es_context, mock_elasticsearch):
    # Given
    index = MockElasticsearchIndex.TEST_INDEX
    doc_id = "doc123"
    document = {"field1": "updated_value"}
    param_value = "test1"
    mock_elasticsearch.update.side_effect = Exception("Update failed")

    # When
    result = await es_context.update(index, doc_id, document, param=param_value)

    # Then
    mock_elasticsearch.update.assert_called_once_with(
        index=index.value.format(param=param_value),
        id=doc_id,
        body={'doc': document},
        param=param_value
    )
    assert result is None


@pytest.mark.asyncio
async def test_bulk_documents_success(es_context, mock_elasticsearch):
    # Given
    operations = [
        {"index": {"_index": "test-index", "_id": "1"}},
        {"field1": "value1", "field2": 123},
        {"index": {"_index": "test-index", "_id": "2"}},
        {"field1": "value2", "field2": 456}
    ]
    bulk_result = {"errors": False, "items": [{}, {}]}
    mock_elasticsearch.bulk.return_value = bulk_result

    # When
    result = await es_context.bulk(operations)

    # Then
    mock_elasticsearch.bulk.assert_called_once_with(
        operations=operations
    )
    assert result == bulk_result


@pytest.mark.asyncio
async def test_bulk_documents_exception(es_context, mock_elasticsearch):
    # Given
    operations = [
        {"index": {"_index": "test-index", "_id": "1"}},
        {"field1": "value1", "field2": 123}
    ]
    mock_elasticsearch.bulk.side_effect = Exception("Bulk operation failed")

    # When
    result = await es_context.bulk(operations)

    # Then
    mock_elasticsearch.bulk.assert_called_once_with(
        operations=operations
    )
    assert result is None


@pytest.mark.asyncio
async def test_create_index_success(es_context, mock_elasticsearch):
    # Given
    index = MockElasticsearchIndex.TEST_INDEX
    mappings = {
        "mappings": {
            "properties": {
                "field1": {"type": "text"},
                "field2": {"type": "integer"}
            }
        }
    }
    param_value = "test1"
    create_result = {"acknowledged": True}
    mock_elasticsearch.indices.create.return_value = create_result

    # When
    result = await es_context.create_index(index, mappings, param=param_value)

    # Then
    mock_elasticsearch.indices.create.assert_called_once_with(
        index=index.value.format(param=param_value),
        body=mappings,
        param=param_value
    )
    assert result == create_result


@pytest.mark.asyncio
async def test_create_index_exception(es_context, mock_elasticsearch):
    # Given
    index = MockElasticsearchIndex.TEST_INDEX
    mappings = {
        "mappings": {
            "properties": {
                "field1": {"type": "text"},
                "field2": {"type": "integer"}
            }
        }
    }
    param_value = "test1"
    mock_elasticsearch.indices.create.side_effect = Exception("Index creation failed")

    # When
    result = await es_context.create_index(index, mappings, param=param_value)

    # Then
    mock_elasticsearch.indices.create.assert_called_once_with(
        index=index.value.format(param=param_value),
        body=mappings,
        param=param_value
    )
    assert result is None


@pytest.mark.asyncio
async def test_delete_index_success(es_context, mock_elasticsearch):
    # Given
    index = MockElasticsearchIndex.TEST_INDEX
    param_value = "test1"
    delete_result = {"acknowledged": True}
    mock_elasticsearch.indices.delete.return_value = delete_result

    # When
    result = await es_context.delete_index(index, param=param_value)

    # Then
    mock_elasticsearch.indices.delete.assert_called_once_with(
        index=index.value.format(param=param_value),
        param=param_value
    )
    assert result == delete_result


@pytest.mark.asyncio
async def test_delete_index_exception(es_context, mock_elasticsearch):
    # Given
    index = MockElasticsearchIndex.TEST_INDEX
    param_value = "test1"
    mock_elasticsearch.indices.delete.side_effect = Exception("Index deletion failed")

    # When
    result = await es_context.delete_index(index, param=param_value)

    # Then
    mock_elasticsearch.indices.delete.assert_called_once_with(
        index=index.value.format(param=param_value),
        param=param_value
    )
    assert result is None