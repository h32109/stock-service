import typing as t

import aiokafka
from trader.context.base import Context
from trader.context.kafka.model import Data

ENCODING = "utf-8"


class KafkaProducerContext(Context):
    _producer: t.Optional[aiokafka.AIOKafkaProducer]

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
        cls.async_producer = aiokafka.AIOKafkaProducer(
            bootstrap_servers=config.KAFKA.HOSTS,
            value_serializer=lambda m: m.json(ensure_ascii=False).encode(ENCODING)
        )
        ctx.register("producer", ctx)
        return ctx

    async def start(self):
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
