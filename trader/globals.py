from functools import partial, wraps
from werkzeug import local

from sqlalchemy.orm import declarative_base

from trader.context.base import Context

Base = declarative_base()


def lookup_context(ctx: Context, name: str | None = None):
    if name is None:
        return ctx.get()
    return getattr(ctx, name, ctx).get(name)


sql = local.LocalProxy(
    partial(
        lookup_context,
        Context,
        "sql")
)

redis = local.LocalProxy(
    partial(
        lookup_context,
        Context,
        "redis")
)

producer = local.LocalProxy(
    partial(
        lookup_context,
        Context,
        "producer")
)

es = local.LocalProxy(
    partial(
        lookup_context,
        Context,
        "elasticsearch")
)


def transaction(func):
    @wraps(func)
    async def _tr(*args, **kwargs):
        async with sql.run_session(commit_on_exit=True):
            response = await func(*args, **kwargs)
        return response

    return _tr
