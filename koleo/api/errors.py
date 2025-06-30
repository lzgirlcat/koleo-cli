from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from aiohttp import ClientResponse, RequestInfo


class errors:
    class KoleoAPIException(Exception):
        status: int
        request: "RequestInfo"
        response: "ClientResponse"

        def __init__(self, response: "ClientResponse", *args: object) -> None:
            super().__init__(*args)
            self.status = response.status
            self.request = response.request_info
            self.response = response

    @staticmethod
    async def from_response(response: "ClientResponse") -> "KoleoAPIException":
        if response.status == 404:
            return errors.KoleoNotFound(response)
        elif response.status == 401:
            return errors.KoleoUnauthorized(response)
        elif response.status == 403:
            return errors.KoleoForbidden(response)
        elif response.status == 429:
            return errors.KoleoRatelimited(response)
        else:
            return errors.KoleoAPIException(response, await response.text())

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
