from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request


class DBSessionMiddleware(BaseHTTPMiddleware):
    def __init__(
            self,
            app: FastAPI,
            run_session,
            commit_on_exit: bool = False,
    ):
        super().__init__(app)
        self.run_session = run_session
        self.commit_on_exit = commit_on_exit

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        async with self.run_session(commit_on_exit=self.commit_on_exit):
            response = await call_next(request)
        return response
