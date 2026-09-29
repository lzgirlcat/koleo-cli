from asyncio import sleep as asleep

from aiohttp import (
    ClientConnectorError,
    ClientOSError,
    ClientResponse,
    ClientResponseError,
    ClientSession,
)
from orjson import loads

from .logging import LoggingMixin


class JsonableData(bytes):
    response: ClientResponse

    def __new__(cls, *args, response: ClientResponse, **kwargs):
        obj = super().__new__(cls, *args, **kwargs)
        obj.response = response
        return obj

    def json(self):
        if "_json" not in self.__dict__:
            self._json = loads(bytes(self))
        return self._json


class BaseAPIClient(LoggingMixin):
    _session: ClientSession

    exc = ClientResponseError

    @property
    def session(self) -> "ClientSession":
        if not hasattr(self, "_session"):
            self._session = ClientSession()
        return self._session

    async def close(self):
        return await self.session.close()

    async def exc_getter(self, r: JsonableData) -> Exception | None:
        return

    async def request(self, method, url: str, *args, retries: int = 0, fail_wait: float = 8, **kwargs) -> JsonableData:
        try:
            async with self.session.request(method, url, *args, **kwargs) as r:
                data = JsonableData(await r.read(), response=r)
                if not r.ok:
                    self.dl(r.headers)
                    try:
                        self.dl(data.decode())
                    except UnicodeDecodeError:
                        self.dl("Response is not text!")
                    if exc := (await self.exc_getter(data)):
                        raise exc
                    r.raise_for_status()
                return data
        except (ClientConnectorError, ClientOSError) as e:
            if retries > 0:
                await asleep(fail_wait)
                return await self.request(
                    method,
                    url,
                    *args,
                    retries=retries - 1,
                    fail_wait=fail_wait,
                    **kwargs,
                )
            raise e
