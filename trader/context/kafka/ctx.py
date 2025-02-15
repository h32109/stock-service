import typing as t

import aiokafka
from trader.context.base import Context
from trader.context.kafka.model import Data

ENCODING = "utf-8"


class KafkaProducerContext(Context):

    def __init__(
            self,
            config,
            producer=None):
        self._producer = producer
        self.config = config

    @classmethod
    def init(
            cls,
            config,
            **kwargs
    ):
        ctx = KafkaProducerContext(config=config)
        ctx.register("producer", ctx)
        return ctx

    async def start(self):
        async_producer = aiokafka.AIOKafkaProducer(
            bootstrap_servers=self.config.KAFKA.HOSTS,
            value_serializer=lambda m: m.json(ensure_ascii=False).encode(ENCODING)
        )
        self._producer = async_producer
        await self._producer.start()

    async def shutdown(self):
        await self._producer.stop()

    async def send(
            self,
            topic: str,
            data: Data,
            key: t.Optional[str] = None,
            chunk_size: t.Optional[int] = 0
    ):
        async for chunk in data.chunk(chunk_size=chunk_size):
            await self._producer.send(
                topic=topic,
                key=key,
                value=chunk.dict()
            )
