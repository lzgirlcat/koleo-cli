import typing as t
from time import time
from datetime import datetime

from aiohttp import ClientResponse

from koleo.api.types import *

from .base import BaseAPIClient
from .errors import errors

if t.TYPE_CHECKING:
    from koleo.storage import Auth

WEB_CLIENT_ID = "83a8978d16b584621b9f9b2f7662a441f51ac39133d4441f34f08d0c79ad5042"
ANDROID_CLIENT_ID = "626bf916f7a8782e6c1ba0410b784d142867737a9ccd87def8e705b3a039bfe3"

OLD_BASIC_AUTH_IOS = "YzQ0NWNhMjg5NzhlODc2OWU3ZDdmZjFiZDkzNDFlNzJkZGQ0ZWE5NDJkYWU1NzM3NWJjNjk1OWZkMTFjYTMzZDo4NTZkZTFlYmZhNmU5NTUzMzYxZGQ3YTBkN2UzYWUzNWVmYTBjZWM0ZjhkNjMwYmY0MGE4ZDNiM2E0MGMxNmRjYzQ0NWNhMjg5NzhlODc2OWU3ZDdmZjFiZDkzNDFlNzJkZGQ0ZWE5NDJkYWU1NzM3NWJjNjk1OWZkMTFjYTMzZDo4NTZkZTFlYmZhNmU5NTUzMzYxZGQ3YTBkN2UzYWUzNWVmYTBjZWM0ZjhkNjMwYmY0MGE4ZDNiM2E0MGMxNmRj"


class KoleoAPI(BaseAPIClient):
    errors = errors

    def __init__(self, auth: "Auth | None") -> None:
        self.base_url = "https://api.koleo.pl"
        self.version = 2
        self.base_headers = {
            "x-koleo-version": str(self.version),  # 1 = android, 2 = web, 3 = ios?
            "x-koleo-client": "Nuxt-1",
            # "x-koleo-devicename": "Koleo-CLI",
            "User-Agent": "Koleo-CLI(https://pypi.org/project/koleo-cli)",
        }
        self._auth: "Auth | None" = auth

    async def _prepare_headers(self, auth: None | str, kwargs: dict):
        headers = {**self.base_headers, **kwargs.pop("headers", {})}
        if auth:
            if not auth.startswith("optional"):
                await self._require_auth()
            if auth.startswith("web"):
                headers["cookie"] = "; ".join([f"{k}={v}" for k, v in self._auth.value.items()])
            if self._auth and auth.endswith("koleo_token"):
                koleo_token = await self.get_koleo_token()
                headers["Authorization"] = f"Bearer {koleo_token}"
        return headers

    async def get(
        self,
        path: str,
        auth: None | t.Literal["any", "web", "koleo_token", "web+koleo_token", "optional_koleo_token"] = None,
        *args,
        **kwargs,
    ):
        headers = await self._prepare_headers(auth, kwargs)
        r = await self.request(
            "GET", self.base_url + path if not path.startswith("http") else path, headers=headers, *args, **kwargs
        )
        if len(r) == 0:
            raise self.errors.KoleoNotFound(r.response)
        return r

    async def post(
        self,
        path,
        auth: None | t.Literal["any", "web", "koleo_token", "web+koleo_token", "optional_koleo_token"] = None,
        *args,
        **kwargs,
    ):
        headers = await self._prepare_headers(auth, kwargs)
        r = await self.request(
            "POST", self.base_url + path if not path.startswith("http") else path, headers=headers, *args, **kwargs
        )
        if len(r) == 0:
            raise self.errors.KoleoNotFound(r.response)
        return r

    async def put(
        self,
        path,
        auth: None | t.Literal["any", "web", "koleo_token", "web+koleo_token", "optional_koleo_token"] = None,
        *args,
        **kwargs,
    ):
        headers = await self._prepare_headers(auth, kwargs)
        r = await self.request(
            "PUT", self.base_url + path if not path.startswith("http") else path, headers=headers, *args, **kwargs
        )
        if len(r) == 0:
            raise self.errors.KoleoNotFound(r.response)
        return r

    async def patch(
        self,
        path,
        auth: None | t.Literal["any", "web", "koleo_token", "web+koleo_token", "optional_koleo_token"] = None,
        *args,
        **kwargs,
    ):
        headers = await self._prepare_headers(auth, kwargs)
        r = await self.request(
            "PATCH", self.base_url + path if not path.startswith("http") else path, headers=headers, *args, **kwargs
        )
        if len(r) == 0:
            raise self.errors.KoleoNotFound(r.response)
        return r

    async def delete(
        self,
        path,
        auth: None | t.Literal["any", "web", "koleo_token", "web+koleo_token", "optional_koleo_token"] = None,
        *args,
        **kwargs,
    ):
        headers = await self._prepare_headers(auth, kwargs)
        r = await self.request(
            "DELETE", self.base_url + path if not path.startswith("http") else path, headers=headers, *args, **kwargs
        )
        return r

    async def exc_getter(self, r: ClientResponse) -> Exception | None:
        return await self.errors.from_response(r)

    async def _require_auth(self) -> t.Literal[True]:
        if self._auth is None:
            raise errors.AuthRequired()
        if (
            "_koleo_token_expiry" in self._auth.value
            and (expiry := self._auth.value["_koleo_token_expiry"] or 0) < time()
        ):
            raise errors.AuthExpired(expiry)
        return True

    async def get_koleo_token(self) -> str:
        await self._require_auth()
        if self._auth and "_koleo_token" not in self._auth.value:
            _, cookies = await self.get_current_session()
            koleo_token = cookies["_koleo_token"]
            data = {**self._auth.value, "_koleo_token": koleo_token}
            self._auth.update(data)
        return self._auth.value["_koleo_token"]

    async def get_stations(self) -> list[ExtendedStationInfo]:
        return (await self.get("/v2/main/stations")).json()

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

    # 410 GONE :<
    # async def get_train(self, id: int) -> TrainDetailResponse:
    #     # https://koleo.pl/pl/trains/142821312
    #     return (await self.get(f"https://koleo.pl/pl/trains/{id}")).json()

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

    async def get_brands(self) -> list[Brand]:
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
        return (
            await self.get(
                f"/v2/main/nested_train_place_types/{connection_id}",
                auth="koleo_token",
            )
        ).json()

    async def get_seats_availability(
        self, connection_id: int, train_nr: int, place_type: int
    ) -> SeatsAvailabilityResponse:
        # https://koleo.pl/api/v2/main/seats_availability/connection_id/train_nr/place_type
        return (
            await self.get(f"/v2/main/seats_availability/{connection_id}/{train_nr}/{place_type}", auth="koleo_token")
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

    async def get_current_session(self) -> tuple[CurrentSession, dict]:
        res = await self.get("/sessions/current", auth="web")
        return res.json(), {k: i.value for k, i in res.response.cookies.items()}

    async def get_current_user(self) -> CurrentUser:
        return (await self.get("/users/current", auth="web")).json()

    async def v3_connection_search(
        self,
        start_station_id: int,
        end_station_id: int,
        brand_ids: list[int],
        date: datetime,
        direct: bool = False,
        minimum_change_duration: int
        | None = None,  # the is weird. for values above 240 the api returns connections that don't match this filter
    ) -> list[V3ConnectionResult]:
        data = {
            "start_id": start_station_id,
            "end_id": end_station_id,
            "departure_after": date.replace(tzinfo=None).isoformat(),
            "only_direct": direct,
        }
        if brand_ids:
            data["allowed_brands"] = brand_ids
        if minimum_change_duration is not None:
            data["minimum_change_duration"] = minimum_change_duration
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

    async def get_estimated_train_times(
        self,
        station_id: int,
        date: datetime,
        train_ids: list[int],
        type: t.Literal["departures", "arrivals"] = "departures",
    ) -> list[EstimatedTrainTime]:
        return (
            await self.get(
                f"https://api.koleo.pl/v2/main/estimated-timetable/station/{station_id}/{date.strftime("%Y-%m-%d")}/{type}",
                auth="koleo_token",
                params={"train_ids[]": train_ids},
            )
        ).json()

    async def get_connection_estimated_train_times(
        self,
        connection_id: str,
    ) -> list[EstimatedV3ConnectionTimesResponse]:
        return (
            await self.get(
                f"https://api.koleo.pl/v2/main/estimated-timetable/connections/uuid/{connection_id}",
                auth="koleo_token",
            )
        ).json()

    async def login_password(
        self, username: str, password: str, client_id: t.Literal["web", "android"] | str = "web"
    ) -> LoginTokenResponse:
        client_id = WEB_CLIENT_ID if client_id == "web" else ANDROID_CLIENT_ID if client_id == "android" else client_id
        return (
            await self.post(
                f"https://api.koleo.pl/v2/main/oauth/token",
                json={"username": username, "password": password, "grant_type": "password", "client_id": client_id},
            )
        ).json()

    async def refresh_token(
        self, refresh_token: str, client_id: t.Literal["web", "android"] | str = "web"
    ) -> LoginTokenResponse:
        client_id = WEB_CLIENT_ID if client_id == "web" else ANDROID_CLIENT_ID if client_id == "android" else client_id
        return (
            await self.post(
                f"https://api.koleo.pl/v2/main/oauth/token",
                json={"refresh_token": refresh_token, "grant_type": "refresh_token", "client_id": client_id},
            )
        ).json()

    async def revoke_token(self):
        return (
            await self.post(
                f"https://api.koleo.pl/v2/main/oauth/token/revoke",
            )
        ).json()

    async def get_user(self) -> V2User:
        return (
            await self.get(
                f"https://api.koleo.pl/v2/main/user",
                auth="koleo_token",
            )
        ).json()

    async def get_train_timetable(self, train_id: int, operating_day: datetime) -> TrainTimetable:
        return (
            await self.get(
                f"https://api.koleo.pl/v2/main/train_timetable/{train_id}/{operating_day.strftime("%Y-%m-%d")}",
                auth="optional_koleo_token",
            )
        ).json()

    async def get_active_orders(self) -> list[Order]:
        return (
            await self.get(
                f"https://api.koleo.pl/v2/main/orders/active",
                auth="koleo_token",
            )
        ).json()

    # this also returns data for inactive orders, but only if they're not refunded/exchanged!
    async def get_active_order(self, id: int) -> FullOrder:
        return (
            await self.get(
                f"https://api.koleo.pl/v2/main/orders/{id}",
                auth="koleo_token",
            )
        ).json()

    # works for all orders (presumably)
    async def get_inactive_order(self, id: int) -> FullOrder:
        return (
            await self.get(
                f"https://api.koleo.pl/v2/main/orders/inactive_by_id/{id}",
                auth="koleo_token",
            )
        ).json()

    async def get_inactive_orders(self, page: int = 1, per_page: int = 50) -> PaginatedOrdersResponse:
        return (
            await self.get(
                f"https://api.koleo.pl/v2/main/paginated_orders/inactive",
                params={"page": page, "per_page": per_page},
                auth="koleo_token",
            )
        ).json()

    async def get_order_pdf(self, id: int) -> bytes:
        return await self.get(
            f"https://api.koleo.pl/v2/main/orders/mobile/{id}.pdf",
            auth="koleo_token",
        )

    async def get_order_google_wallet_token(self, id: int) -> GoogleWalletTokenResponse:
        return (
            await self.get(
                f"https://api.koleo.pl/v2/main/google_wallet/token/{id}",
                auth="koleo_token",
            )
        ).json()

    async def get_order_apple_wallet_pass(self, id: int) -> bytes:
        return await self.get(
            f"https://api.koleo.pl/v2/main/wallet_passes/{id}/",
            auth="koleo_token",
        )

    async def get_feature_flags(self, platform: t.Literal["android", "ios", "web"] | None = None):
        return (
            await self.get(
                f"https://api.koleo.pl/v2/main/user/flags/{platform if platform else ""}",
            )
        ).json()

    async def get_mobywatel_verification(self):
        return (
            await self.get(f"https://api.koleo.pl/v2/main/mobywatel/verifications/identity", auth="koleo_token")
        ).json()

    async def begin_mobywatel_verification(self) -> MobywatelVerificationCodeResponse:
        return (
            await self.post(f"https://api.koleo.pl/v2/main/mobywatel/verifications/identity", auth="koleo_token")
        ).json()

    async def begin_mobywatel_student_id_verification(self) -> MobywatelVerificationCodeResponse:
        return (
            await self.post(
                f"https://api.koleo.pl/v2/main/mobywatel/verifications/discount/student_id", auth="koleo_token"
            )
        ).json()

    async def get_mobywatel_verification_status(self) -> MobywatelVerificationStatus:
        return (
            await self.get(f"https://api.koleo.pl/v2/main/mobywatel/verifications/status", auth="koleo_token")
        ).json()

    async def unregister_mobywatel_verification(self) -> bool:
        await self.delete(f"https://api.koleo.pl/v2/main/mobywatel/device", auth="koleo_token")
        return True
