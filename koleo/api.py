import typing as t
from datetime import datetime

from requests import PreparedRequest, Response, Session

from koleo.types import *


class errors:
    class KoleoAPIException(Exception):
        status: int
        request: PreparedRequest
        response: Response

        def __init__(self, response: Response, *args: object) -> None:
            super().__init__(*args)
            self.status = response.status_code
            self.request = response.request
            self.response = response

        @classmethod
        def from_response(cls, response: Response) -> "t.Self":
            if response.status_code == 404:
                return errors.KoleoNotFound(response)
            elif response.status_code == 401:
                return errors.KoleoUnauthorized(response)
            elif response.status_code == 403:
                return errors.KoleoForbidden(response)
            elif response.status_code == 429:
                return errors.KoleoRatelimited(response)
            else:
                return cls(response)

    class KoleoNotFound(KoleoAPIException):
        pass

    class KoleoForbidden(KoleoAPIException):
        pass

    class KoleoUnauthorized(KoleoAPIException):
        pass

    class KoleoRatelimited(KoleoAPIException):
        pass


class KoleoAPI:
    errors = errors

    def __init__(self) -> None:
        self.session = Session()
        self.base_url = "https://koleo.pl"
        self.version = 2
        self.base_headers = {
            "x-koleo-version": str(self.version),
            "User-Agent": "Koleo-CLI(https://pypi.org/project/koleo-cli)",
        }

    def _get(self, path, *args, **kwargs) -> Response:
        headers = {**self.base_headers, **kwargs.get("headers", {})}
        r = self.session.get(self.base_url + path, *args, headers=headers, **kwargs)
        if not r.ok:
            raise errors.KoleoAPIException.from_response(r)
        return r

    def _get_json(self, path, *args, **kwargs) -> t.Any:
        r = self._get(path, *args, **kwargs)
        res = r.json()
        if res is None:
            raise self.errors.KoleoNotFound(r)
        return res

    def _get_bytes(self, path, *args, **kwargs) -> bytes:
        r = self._get(path, *args, **kwargs)
        return r.content

    def get_stations(self) -> list[ExtendedStationInfo]:
        return self._get_json("/api/v2/main/stations")

    def find_station(self, query: str, language: str = "pl") -> list[ExtendedStationInfo]:
        # https://koleo.pl/ls?q=tere&language=pl
        return self._get_json("/ls", params={"q": query, "language": language})["stations"]

    def get_station_by_id(self, id: int) -> ExtendedBaseStationInfo:
        # https://koleo.pl/api/v2/main/stations/by_id/24000
        return self._get_json(
            f"/api/v2/main/stations/by_id/{id}",
        )

    def get_station_by_slug(self, slug: str) -> ExtendedBaseStationInfo:
        # https://koleo.pl/api/v2/main/stations/by_slug/inowroclaw
        return self._get_json(
            f"/api/v2/main/stations/by_slug/{slug}",
        )

    def get_station_info_by_slug(self, slug: str) -> StationDetails:
        # https://koleo.pl/api/v2/main/station_info/inowroclaw
        return self._get_json(
            f"/api/v2/main/station_info/{slug}",
        )

    def get_departures(self, station_id: int, date: datetime) -> list[TrainOnStationInfo]:
        # https://koleo.pl/api/v2/main/timetables/18705/2024-03-25/departures
        return self._get_json(
            f"/api/v2/main/timetables/{station_id}/{date.strftime("%Y-%m-%d")}/departures",
        )

    def get_arrivals(self, station_id: int, date: datetime) -> list[TrainOnStationInfo]:
        # https://koleo.pl/api/v2/main/timetables/18705/2024-03-25/arrivals
        return self._get_json(
            f"/api/v2/main/timetables/{station_id}/{date.strftime("%Y-%m-%d")}/arrivals",
        )

    def get_train_calendars(self, brand_name: str, number: int, name: str | None = None) -> TrainCalendarResponse:
        # https://koleo.pl/pl/train_calendars?brand=REG&nr=10417
        # https://koleo.pl/pl/train_calendars?brand=IC&nr=1106&name=ESPERANTO ; WHY!!!! WHY!!!!!!1
        params = {"brand": brand_name, "nr": number}
        if name:
            params["name"] = name.upper()  # WHY!!!!!!!!!
        return self._get_json("/pl/train_calendars", params=params)

    def get_train(self, id: int) -> TrainDetailResponse:
        # https://koleo.pl/pl/trains/142821312
        return self._get_json(f"/pl/trains/{id}")

    def get_connections(
        self,
        start: str,
        end: str,
        brand_ids: list[int],
        date: datetime,
        direct: bool = False,
        purchasable: bool = False,
    ) -> list[ConnectionDetail]:
        params = {
            "query[date]": date.strftime("%d-%m-%Y %H:%M:%S"),
            "query[start_station]": start,
            "query[end_station]": end,
            "query[only_purchasable]": str(direct).lower(),
            "query[only_direct]": str(direct).lower(),
            "query[brand_ids][]": brand_ids,
        }
        return self._get_json("/api/v2/main/connections", params=params)["connections"]

    def get_brands(self) -> list[ApiBrand]:
        # https://koleo.pl/api/v2/main/brands
        return self._get_json(
            "/api/v2/main/brands",
        )

    def get_carriers(self) -> list[Carrier]:
        # https://koleo.pl/api/v2/main/carriers
        return self._get_json(
            "/api/v2/main/carriers",
        )

    def get_discounts(self) -> list[DiscountInfo]:
        # https://koleo.pl/api/v2/main/discounts
        return self._get_json(
            "/api/v2/main/discounts",
        )
