import re
from datetime import datetime

from koleo.api import KoleoAPI
from koleo.api.types import ExtendedStationInfo, TrainOnStationInfo, TrainStop, TrainAttribute
from koleo.storage import Storage
from koleo.utils import convert_platform_number, koleo_time_to_dt, name_to_slug
from .utils import GŁÓWNX_STATIONS


class BaseCli:
    def __init__(
        self,
        no_color: bool = False,
        client: KoleoAPI | None = None,
        storage: Storage | None = None,
    ) -> None:
        self._client = client
        self._storage = storage
        self.no_color = no_color

    def init_console(self, no_color: bool | None = None):
        if no_color is not None:
            self.no_color = no_color
        if not self.no_color:
            from rich.console import Console

            self.console = Console(color_system="standard", highlight=False)

    def print(self, text: str, *args, **kwargs):
        if not text.strip():
            return
        if self.no_color:
            result = re.sub(r"\[[^\]]*\]", "", text)
            print(result)
        else:
            self.console.print(text, *args, **kwargs)

    async def error_and_exit(self, text: str, *args, **kwargs):
        self.print(f"[bold red]{text}[/bold red]", *args, **kwargs)
        await self.client.close()
        exit(2)

    @property
    def client(self) -> KoleoAPI:
        if not self._client:
            raise ValueError("Client not set!")
        return self._client

    @client.setter
    def client(self, client: KoleoAPI):
        self._client = client

    @property
    def storage(self) -> Storage:
        if not self._storage:
            raise ValueError("Storage not set!")
        return self._storage

    @storage.setter
    def storage(self, storage: Storage):
        self._storage = storage

    def ftime(self, dt: datetime):
        return dt.strftime("%H:%M:%S") if self.storage.show_seconds else dt.strftime("%H:%M")

    async def trains_on_station_table(
        self, trains: list[TrainOnStationInfo], type: int = 1, show_connection_id: bool | None = None
    ):
        show_connection_id = self.storage.show_connection_id if show_connection_id is None else show_connection_id
        brands = await self.get_brands()
        for train in trains:
            time, color = (train["departure"], "green") if type == 1 else (train["arrival"], "yellow")
            assert time
            dt = koleo_time_to_dt(time)
            brand = next(iter(i for i in brands if i["id"] == train["brand_id"]), {}).get("logo_text")
            tid = (f"{train["stations"][0]["train_id"]} ") if show_connection_id else ""
            self.print(
                f"{tid}[bold {color}]{self.ftime(dt)}[/bold {color}] [red]{brand}[/red] {train["train_full_name"]}[purple] {train["stations"][0]["name"]} {self.format_position(train["platform"], train["track"])}[/purple]"
            )

    def train_route_table(self, stops: list[TrainStop]):
        last_real_distance = stops[0]["distance"]
        for stop in stops:
            arr = koleo_time_to_dt(stop["arrival"])
            dep = koleo_time_to_dt(stop["departure"])
            distance = stop["distance"] - last_real_distance
            self.print(
                f"[white underline]{distance / 1000:^5.1f}km[/white underline] [bold green]{self.ftime(arr)}[/bold green] - [bold red]{self.ftime(dep)}[/bold red] [purple]{stop["station_display_name"]} {self.format_position(stop["platform"])} [/purple]"
            )

    def format_position(self, platform: str, track: str | None = None):
        res = str(convert_platform_number(platform) or "" if not self.storage.use_roman_numerals else platform)
        if track is not None and track != "":
            if self.storage.platform_first:
                res += f"/{track}"
            else:
                res = f"{track}/{res}"
        return res

    async def get_station(self, station: str) -> ExtendedStationInfo:
        if station in self.storage.aliases:
            slug = self.storage.aliases[station]
        elif station.isnumeric():
            try:
                return await self.get_station_by_id(int(station))
            except self.client.errors.KoleoNotFound:
                await self.error_and_exit(f"Station not found: [underline]{station}[/underline]")
        else:
            slug = name_to_slug(station)
            if self.storage.auto_głównx and slug in GŁÓWNX_STATIONS:
                slug = GŁÓWNX_STATIONS[slug]
        try:
            return self.storage.get_cache(f"st-{slug}") or self.storage.set_cache(
                f"st-{slug}", await self.client.get_station_by_slug(slug)
            )
        except self.client.errors.KoleoNotFound:
            await self.error_and_exit(f"Station not found: [underline]{station}[/underline]")

    async def get_brands(self):
        return self.storage.get_cache("brands") or self.storage.set_cache("brands", await self.client.get_brands())

    async def get_station_by_id(self, id: int):
        key = f"st-{id}"
        return self.storage.get_cache(key) or self.storage.set_cache(key, await self.client.get_station_by_id(id))

    async def get_brand_by_shortcut(self, s: str, *, name: str | None = None):
        brands = await self.get_brands()
        s = s.upper()
        if name and "SŁONECZNY" in name and s == "KM":
            return "SLONECZNY"  # OH MY FUCKING GOD
        if s == "AR":
            return "ARRIVARP"
        if s not in [i["name"] for i in brands]:
            res = {i["logo_text"]: i["name"] for i in brands}.get(s)
            if not res:
                await self.error_and_exit(f"Invalid brand name not found: [underline]{s},[/underline]")
            return res
        return s

    async def get_train_attributes(self) -> dict[str, TrainAttribute]:
        if not (train_attributes := self.storage.get_cache("train_attributes")):
            train_attributes = {str(i["id"]): i for i in await self.client.get_train_attributes()}
            self.storage.set_cache("train_attributes", train_attributes)
        return train_attributes

    async def get_stations(self) -> dict[str, ExtendedStationInfo]:
        if not (stations := self.storage.get_cache("stations")):
            stations = {str(i["id"]): i for i in await self.client.get_stations()}
            self.storage.set_cache("stations", stations)
        return stations
