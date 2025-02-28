import typing as t

import ujson

from trader.context.base import Context
from trader.context.redis.model import RedisKey

import redis.asyncio as redis


class RedisContext(Context):
    config: t.Any
    _redis: t.Any

    def __init__(
            self,
            config,
            redis=None
    ):
        self._redis = redis
        self.config = config

    @classmethod
    def init(
            cls,
            config,
            **kwargs):
        _redis = redis.Redis(
            host=config.REDIS.HOST,
            port=config.REDIS.PORT,
            db=config.REDIS.DB,
            password=config.REDIS.PASSWORD,
        )
        ctx = RedisContext(
            config=config,
            redis=_redis
        )
        ctx.register("redis", ctx)
        return ctx

    async def start(self):
        pass

    async def shutdown(self):
        self._redis.close()
        await self._redis.wait_closed()

    async def jset(self, key: RedisKey, value: t.Dict[str, t.Any], **kwargs):
        await self._redis.set(key=key.value.format(**kwargs), value=ujson.dumps(value), expire=kwargs.get("expire"))

    async def jget(self, key: RedisKey, **kwargs):
        value = await self._redis.get(key=key.value.format(**kwargs), encoding="utf-8")
        return ujson.loads(value) if value else None

    async def delete(self, key: RedisKey, **kwargs):
        await self._redis.delete(key=key.value.format(**kwargs))

    async def hset(self, key: RedisKey, field: str, value: t.Dict[str, t.Any]):
        await self._redis.hset(key=key.value, field=field, value=ujson.dumps(value))

    async def hget(self, key: RedisKey, field: str):
        value = await self._redis.hget(key=key.value, field=field, encoding="utf-8")
        return ujson.loads(value) if value else None

    async def hdel(self, key: RedisKey, field: str):
        await self._redis.hdel(key=key.value, field=field)
