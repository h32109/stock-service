import typing as t
from contextvars import ContextVar

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    AsyncEngine
)
from sqlalchemy.orm import sessionmaker

from trader.globals import Base

from trader.context.base import Context


class Session:
    def __init__(self,
                 session: ContextVar[t.Optional[AsyncSession]],
                 session_maker: sessionmaker,
                 session_args: t.Dict = None,
                 commit_on_exit: bool = False):
        self.session = session
        self.session_maker = session_maker
        self.token = None
        self.session_args = session_args or {}
        self.commit_on_exit = commit_on_exit

    async def __aenter__(self):
        sess = self.session.get()
        if not sess:
            self.token = self.session.set(self.session_maker(**self.session_args))
        return type(self)

    async def __aexit__(self, exc_type, exc_value, traceback):
        sess = self.session.get()
        if exc_type is not None:
            await sess.rollback()

        if self.commit_on_exit:
            await sess.commit()

        await sess.close()

        if self.token:
            self.session.reset(self.token)


class SQLContext(Context):
    config: t.Any
    _models: t.Any
    _connection: t.Optional[AsyncEngine]
    _session_maker: t.Optional[sessionmaker]
    _session: ContextVar[t.Optional[AsyncSession]] = ContextVar("_session", default=None)

    def __init__(self, models, config):
        super().__init__()
        self.config = config
        self._models = models or []

    @property
    def session(self) -> AsyncSession:
        session = self._session.get()
        return session

    def set_session(self, session_args: t.Dict = None,):
        session_args = session_args or {}
        self._session.set(self._session_maker(**session_args))

    def run_session(
            self,
            session_args: t.Dict = None,
            commit_on_exit: bool = False
    ) -> Session:
        return Session(
            session=self._session,
            session_maker=self._session_maker,
            session_args=session_args,
            commit_on_exit=commit_on_exit)

    @classmethod
    def init(cls,
             config,
             models=None,
             session_maker_args: t.Dict = None):

        cls._connection = create_async_engine(
            config.POSTGRESQL.URL + "/" + config.POSTGRESQL.DATABASE
        )

        session_maker_args = session_maker_args or {}
        cls._session_maker = sessionmaker(bind=cls._connection, **session_maker_args)

        ctx = SQLContext(models, config)
        ctx.register("sql", ctx)
        return ctx

    async def start(self):
        async with self._connection.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    async def shutdown(self):
        pass

