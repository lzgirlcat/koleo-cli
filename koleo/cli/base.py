from koleo.api import KoleoAPI
from koleo.storage import Storage
from koleo.api.types import ExtendedStationInfo, TrainOnStationInfo, TrainStop
from koleo.utils import koleo_time_to_dt, name_to_slug, convert_platform_number

from rich.console import Console
import re


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
        self.console = Console(color_system="standard", no_color=no_color, highlight=False)

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

    async def trains_on_station_table(
        self, trains: list[TrainOnStationInfo], type: int = 1, show_connection_id: bool | None = None
    ):
        show_connection_id = self.storage.show_connection_id if show_connection_id is None else show_connection_id
        brands = await self.get_brands()
        for train in trains:
            time, color = (train["departure"], "green") if type == 1 else (train["arrival"], "yellow")
            assert time
            brand = next(iter(i for i in brands if i["id"] == train["brand_id"]), {}).get("logo_text")
            tid = (f"{train["stations"][0]["train_id"]} ") if show_connection_id else ""
            self.print(
                f"{tid}[bold {color}]{time[11:16]}[/bold {color}] [red]{brand}[/red] {train["train_full_name"]}[purple] {train["stations"][0]["name"]} {self.format_position(train["platform"], train["track"])}[/purple]"
            )

    def train_route_table(self, stops: list[TrainStop]):
        last_real_distance = stops[0]["distance"]
        for stop in stops:
            arr = koleo_time_to_dt(stop["arrival"])
            dep = koleo_time_to_dt(stop["departure"])
            distance = stop["distance"] - last_real_distance
            self.print(
                f"[white underline]{distance / 1000:^5.1f}km[/white underline] [bold green]{arr.strftime("%H:%M")}[/bold green] - [bold red]{dep.strftime("%H:%M")}[/bold red] [purple]{stop["station_display_name"]} {self.format_position(stop["platform"])} [/purple]"
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
        else:
            slug = name_to_slug(station)
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
