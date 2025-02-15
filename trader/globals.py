from functools import partial
from werkzeug import local

from sqlalchemy.ext.declarative import declarative_base

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

