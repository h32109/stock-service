import json

import aiohttp

import typing as t
from starlette.responses import Response as StarletteResponse
from starlette.background import BackgroundTask


class JSONResponse(StarletteResponse):
    media_type = "application/json"
    status: int

    def __init__(
            self,
            content: t.Any,
            status_code: int = 200,
            headers: t.Optional[t.Dict[str, str]] = None,
            media_type: t.Optional[str] = None,
            background: t.Optional[BackgroundTask] = None,
    ) -> None:
        self.status = status_code
        super().__init__(content, status_code, headers, media_type, background)

    async def json(
            self,
    ) -> t.Any:
        """Read and decodes JSON response."""

        content = self.body
        if not content:
            return None

        return json.loads(content)


class Requestor:
    def __init__(self, config):
        self.config = config
        self.session = None

    async def create_session(self,
                             total: t.Optional[float] = None,
                             connect: t.Optional[float] = None,
                             sock_read: t.Optional[float] = None,
                             sock_connect: t.Optional[float] = None,
                             raise_for_status: t.Optional[bool] = False):
        timeout = aiohttp.ClientTimeout(
            total=total,
            connect=connect,
            sock_read=sock_read,
            sock_connect=sock_connect
        )
        conn = aiohttp.TCPConnector(limit_per_host=30, limit=50, force_close=True)
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            raise_for_status=raise_for_status,
            connector=conn
        )

    async def close(self):
        await self.session.close()

    async def request(self,
                      method: str,
                      url: str,
                      **kwargs: t.Any):
        # method, body, url, params validation TODO: mandate to Client session
        async with self.session.request(
                method, url, **kwargs
        ) as res:
            response = JSONResponse(
                content=await res.read(),
                status_code=res.status,
                headers=res._headers,
            )
            return response

