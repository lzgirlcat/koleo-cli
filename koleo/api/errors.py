from typing import TYPE_CHECKING
from orjson import loads

if TYPE_CHECKING:
    from aiohttp import ClientResponse, RequestInfo
    from .base import JsonableData

class errors:
    class KoleoAPIException(Exception):
        status: int
        request: "RequestInfo"
        response: "ClientResponse"

        def __init__(self, response: "ClientResponse", data: "JsonableData", *args: object) -> None:
            super().__init__(*args)
            self.status = response.status
            self.request = response.request_info
            self.response = response
            self.data = data

    @staticmethod
    async def from_response(data: "JsonableData") -> "KoleoAPIException":
        if data.response.status == 404:
            return errors.KoleoNotFound(data.response, data)
        elif data.response.status == 401:
            return errors.KoleoUnauthorized(data.response, data)
        elif data.response.status == 403:
            return errors.KoleoForbidden(data.response, data)
        elif data.response.status == 429:
            return errors.KoleoRatelimited(data.response, data)
        else:
            return errors.KoleoAPIException(data.response, data)

    class KoleoNotFound(KoleoAPIException):
        pass

    class KoleoForbidden(KoleoAPIException):
        pass

    class KoleoUnauthorized(KoleoAPIException):
        pass

    class KoleoRatelimited(KoleoAPIException):
        pass

    class AuthRequired(Exception):
        pass

    class AuthExpired(AuthRequired):
        pass
