import typing as t
from elasticsearch import AsyncElasticsearch
from trader.context.base import Context
from trader.context.elasticsearch.model import ElasticsearchIndex


class ElasticsearchContext(Context):
    config: t.Any
    _es: t.Optional[AsyncElasticsearch]

    def __init__(
            self,
            config,
            elasticsearch=None
    ):
        self._es = elasticsearch
        self.config = config

    @classmethod
    def init(
            cls,
            config,
            **kwargs):
        ctx = ElasticsearchContext(config=config)
        cls._es = AsyncElasticsearch(
            hosts=config.ELASTICSEARCH.HOSTS,
            basic_auth=(
                config.ELASTICSEARCH.USERNAME,
                config.ELASTICSEARCH.PASSWORD
            ),
        )
        assert cls._es
        ctx.register("elasticsearch", ctx)
        return ctx

    async def start(self):
        pass


    async def shutdown(self):
        await self._es.close()

    async def index(self, index: ElasticsearchIndex, document: t.Dict[str, t.Any], **kwargs):
        return await self._es.index(
            index=index.value.format(**kwargs),
            document=document,
            **kwargs
        )

    async def eget(self, index: ElasticsearchIndex, id: str, **kwargs):
        try:
            result = await self._es.get(
                index=index.value.format(**kwargs),
                id=id,
                **kwargs
            )
            return result['_source'] if result else None
        except Exception:
            return None

    async def search(self, index: ElasticsearchIndex, query: t.Dict[str, t.Any], **kwargs):
        try:
            result = await self._es.search(
                index=index.value.format(**kwargs),
                body=query,
                **kwargs
            )
            return result
        except Exception:
            return None

    async def delete(self, index: ElasticsearchIndex, id: str, **kwargs):
        try:
            return await self._es.delete(
                index=index.value.format(**kwargs),
                id=id,
                **kwargs
            )
        except Exception:
            return None

    async def update(self, index: ElasticsearchIndex, id: str, document: t.Dict[str, t.Any], **kwargs):
        try:
            return await self._es.update(
                index=index.value.format(**kwargs),
                id=id,
                body={'doc': document},
                **kwargs
            )
        except Exception:
            return None

    async def bulk(self, operations: t.List[t.Dict[str, t.Any]], **kwargs):
        try:
            return await self._es.bulk(
                operations=operations,
                **kwargs
            )
        except Exception:
            return None

    async def create_index(self, index: ElasticsearchIndex, mappings: t.Dict[str, t.Any], **kwargs):
        try:
            return await self._es.indices.create(
                index=index.value.format(**kwargs),
                body=mappings,
                **kwargs
            )
        except Exception:
            return None

    async def delete_index(self, index: ElasticsearchIndex, **kwargs):
        try:
            return await self._es.indices.delete(
                index=index.value.format(**kwargs),
                **kwargs
            )
        except Exception:
            return None
