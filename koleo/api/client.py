import typing as t
from datetime import datetime

from aiohttp import ClientResponse

from koleo.api.types import *

from .base import BaseAPIClient
from .errors import errors


class KoleoAPI(BaseAPIClient):
    errors = errors

    def __init__(self, auth: dict[str, str] | None = None) -> None:
        self.base_url = "https://api.koleo.pl"
        self.version = 2
        self.base_headers = {
            "x-koleo-version": str(self.version),
            "x-koleo-client": "Nuxt-1",
            "User-Agent": "Koleo-CLI(https://pypi.org/project/koleo-cli)",
        }
        self._auth: dict[str, str] | None = auth
        self._auth_valid: bool | None = None

    async def get(self, path: str, use_auth: bool = False, *args, **kwargs):
        headers = {**self.base_headers, **kwargs.pop("headers", {})}
        if self._auth and use_auth:
            headers["cookie"] = "; ".join([f"{k}={v}" for k, v in self._auth.items()])
        r = await self.request(
            "GET", self.base_url + path if not path.startswith("http") else path, headers=headers, *args, **kwargs
        )
        if len(r) == 0:
            raise self.errors.KoleoNotFound(r.response)
        return r

    async def post(self, path, use_auth: bool = False, *args, **kwargs):
        headers = {**self.base_headers, **kwargs.pop("headers", {})}
        if self._auth and use_auth:
            headers["cookie"] = ("; ".join([f"{k}={v}" for k, v in self._auth.items()]),)
        r = await self.request(
            "POST", self.base_url + path if not path.startswith("http") else path, headers=headers, *args, **kwargs
        )
        if len(r) == 0:
            raise self.errors.KoleoNotFound(r.response)
        return r

    async def put(self, path, use_auth: bool = False, *args, **kwargs):
        headers = {**self.base_headers, **kwargs.pop("headers", {})}
        if self._auth and use_auth:
            headers["cookie"] = ("; ".join([f"{k}={v}" for k, v in self._auth.items()]),)
        r = await self.request("PUT", self.base_url + path, headers=headers, *args, **kwargs)
        if len(r) == 0:
            raise self.errors.KoleoNotFound(r.response)
        return r

    async def exc_getter(self, r: ClientResponse) -> Exception | None:
        return await self.errors.from_response(r)

    async def _require_auth(self) -> t.Literal[True]:
        if self._auth is None:
            raise errors.AuthRequired()
        if self._auth_valid is None:
            await self.get_current_session()
            self._auth_valid = True
        return True

    async def get_stations(self) -> list[ExtendedStationInfo]:
        return (await self.get("/v2/main/stations")).json()

    async def find_station(self, query: str, language: str = "pl") -> list[SearchStationInfo]:
        # https://koleo.pl/ls?q=tere&language=pl
        return (await self.get("/ls", params={"q": query, "language": language})).json()["stations"]

    async def get_station_by_id(self, id: int) -> ExtendedStationInfo:
        # https://koleo.pl/api/v2/main/stations/by_id/24000
        return (
            await self.get(
                f"/v2/main/stations/by_id/{id}",
            )
        ).json()

    async def get_station_by_slug(self, slug: str) -> ExtendedStationInfo:
        # https://koleo.pl/api/v2/main/stations/by_slug/inowroclaw
        return (
            await self.get(
                f"/v2/main/stations/by_slug/{slug}",
            )
        ).json()

    async def get_station_info_by_slug(self, slug: str) -> StationDetails:
        # https://koleo.pl/api/v2/main/station_info/inowroclaw
        return (
            await self.get(
                f"/v2/main/station_info/{slug}",
            )
        ).json()

    async def get_departures(self, station_id: int, date: datetime) -> list[TrainOnStationInfo]:
        # https://koleo.pl/api/v2/main/timetables/18705/2024-03-25/departures
        return (
            await self.get(
                f"/v2/main/timetables/{station_id}/{date.strftime("%Y-%m-%d")}/departures",
            )
        ).json()

    async def get_arrivals(self, station_id: int, date: datetime) -> list[TrainOnStationInfo]:
        # https://koleo.pl/api/v2/main/timetables/18705/2024-03-25/arrivals
        return (
            await self.get(
                f"/v2/main/timetables/{station_id}/{date.strftime("%Y-%m-%d")}/arrivals",
            )
        ).json()

    async def get_train_calendars(self, brand_name: str, number: int, name: str | None = None) -> TrainCalendarResponse:
        # https://koleo.pl/pl/train_calendars?brand=REG&nr=10417
        # https://koleo.pl/pl/train_calendars?brand=IC&nr=1106&name=ESPERANTO ; WHY!!!! WHY!!!!!!1
        params = {"brand": brand_name, "nr": number}
        if name:
            params["name"] = name.upper()  # WHY!!!!!!!!!
        return (await self.get("https://koleo.pl/pl/train_calendars", params=params)).json()

    async def get_train(self, id: int) -> TrainDetailResponse:
        # https://koleo.pl/pl/trains/142821312
        return (await self.get(f"https://koleo.pl/pl/trains/{id}")).json()

    async def get_connections(
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
            "query[only_purchasable]": str(purchasable).lower(),
            "query[only_direct]": str(direct).lower(),
            "query[brand_ids][]": brand_ids,
        }
        return (await self.get("/v2/main/connections", params=params)).json()["connections"]

    async def get_connection(self, id: int) -> ConnectionDetail:
        return (
            await self.get(
                f"/v2/main/connections/{id}",
            )
        ).json()

    async def get_brands(self) -> list[ApiBrand]:
        # https://koleo.pl/api/v2/main/brands
        return (
            await self.get(
                "/v2/main/brands",
            )
        ).json()

    async def get_carriers(self) -> list[Carrier]:
        # https://koleo.pl/api/v2/main/carriers
        return (
            await self.get(
                "/v2/main/carriers",
            )
        ).json()

    async def get_discounts(self) -> list[DiscountInfo]:
        # https://koleo.pl/api/v2/main/discounts
        return (
            await self.get(
                "/v2/main/discounts",
            )
        ).json()

    async def get_nested_train_place_types(self, connection_id: int) -> SeatsAvailabilityResponse:
        # https://koleo.pl/api/v2/main/seats_availability/connection_id/train_nr/place_type
        await self._require_auth()
        if self._auth and "_koleo_token" not in self._auth:
            res = await self.post(f"/prices/{connection_id}/passengers")
            self._auth["_koleo_token"] = koleo_token = res.response.cookies["_koleo_token"].value
        return (
            await self.get(
                f"/v2/main/nested_train_place_types/{connection_id}",
                headers={"Authorization": f"Bearer {koleo_token}"},
                use_auth=True,
            )
        ).json()

    async def get_seats_availability(
        self, connection_id: int, train_nr: int, place_type: int
    ) -> SeatsAvailabilityResponse:
        # https://koleo.pl/api/v2/main/seats_availability/connection_id/train_nr/place_type
        return (
            await self.get(
                f"/v2/main/seats_availability/{connection_id}/{train_nr}/{place_type}",
            )
        ).json()

    async def get_train_composition(
        self, connection_id: int, train_nr: int, place_type: int
    ) -> SeatsAvailabilityResponse:
        # https://koleo.pl/api/v2/main/train_composition/connection_id/train_nr/place_type
        return (
            await self.get(
                f"/v2/main/train_composition/{connection_id}/{train_nr}/{place_type}",
            )
        ).json()

    async def get_carriage_type(self, id: int) -> CarriageType:
        # https://koleo.pl/api/v2/main/carriage_types/id
        return (
            await self.get(
                f"/v2/main/carriage_types/{id}",
            )
        ).json()

    async def get_carriage_types(self) -> list[CarriageType]:
        return (await self.get("/v2/main/carriage_types")).json()

    async def get_station_keywoards(self) -> list[StationKeyword]:
        return (await self.get("/v2/main/station_keywords")).json()

    async def get_price(self, connection_id: int) -> Price | None:
        res = await self.get(
            f"https://koleo.pl/pl/prices/{connection_id}",
        )
        return res.json().get("price")

    async def get_current_session(self) -> CurrentSession:
        return (await self.get("/sessions/current", use_auth=True)).json()

    async def get_current_user(self) -> CurrentUser:
        return (await self.get("/users/current", use_auth=True)).json()

    async def v3_connection_search(
        self,
        start_station_id: int,
        end_station_id: int,
        brand_ids: list[int],
        date: datetime,
        direct: bool = False,
    ) -> list[V3ConnectionResult]:
        data = {
            "start_id": start_station_id,
            "end_id": end_station_id,
            "departure_after": date.isoformat(),
            "only_direct": direct,
        }
        if brand_ids:
            data["allowed_brands"] = brand_ids
        return (
            await self.post("/v2/main/eol_connections/search", json=data, headers={"accept-eol-response-version": "1"})
        ).json()

    async def v3_get_price(self, id: str) -> V3Price | None:
        try:
            return (await self.get(f"/v2/main/eol_connections/{id}/price")).json()
        except self.errors.KoleoNotFound:
            return None

    async def get_carrier_lines(self, carrier_slug: str) -> list[CarrierLine]:
        return (await self.get(f"/v2/main/carrier_lines/{carrier_slug}")).json()["list"]

    async def v3_get_connection_id(self, id: str) -> int:
        return (await self.put(f"/v2/main/eol_connections/{id}/connection_id")).json()["connection_id"]

    async def get_train_attributes(self) -> list[TrainAttribute]:
        # https://koleo.pl/api/v2/main/train_atributes
        return (
            await self.get(
                "/v2/main/train_attributes",
            )
        ).json()
