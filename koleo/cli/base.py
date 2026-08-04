import re
from datetime import datetime
from typing import overload, Literal

from koleo.api import KoleoAPI
from koleo.api.types import ExtendedStationInfo, TrainOnStationInfo, RealtimeTrainStop, TrainAttribute, TrainTimetable
from koleo.storage import Storage
from koleo.utils import convert_platform_number, koleo_time_to_dt, name_to_slug
from .utils import GŁÓWNX_STATIONS, is_index, STATION_NAME_REPLACEMENTS


class BaseCli:
    def __init__(
        self,
        no_color: bool = False,
        client: KoleoAPI | None = None,
        storage: Storage | None = None,
        quiet: bool = False,
    ) -> None:
        self._client = client
        self._storage = storage
        self.no_color = no_color
        self.quiet = quiet

    def init_console(self, no_color: bool | None = None):
        if no_color is not None:
            self.no_color = no_color
        if not self.no_color:
            from rich.console import Console

            self.console = Console(color_system="standard", highlight=False)

    def indent_lines(self, text: str, indent: int = 2):
        for line in text.splitlines():
            self.print(f"{" " * indent}{line}")

    def print(self, text: str, *args, **kwargs):
        if not isinstance(text, str):
            text = repr(text)
        if not text.strip():
            return
        if self.no_color:
            result = re.sub(r"\[[^\]]*\]", "", text)
            print(result)
        else:
            self.console.print(text, *args, **kwargs)

    async def error_and_exit(self, text: str, *args, color: bool = True, **kwargs):
        self.print(f"[bold red]{text}[/bold red]" if color else text, *args, **kwargs)
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

    async def train_route_table(self, stops: list[RealtimeTrainStop]):
        stations = await self.get_stations()
        for idx, stop in enumerate(stops):
            arr = koleo_time_to_dt(stop["arrival"])
            arr_diff = (
                f"[white underline] +{int((koleo_time_to_dt(stop["actual_arrival"]) - arr).total_seconds() / 60)}m[/white underline]"
                if stop["actual_arrival"]
                else ""
            )
            dep = koleo_time_to_dt(stop["departure"])
            dep_diff = (
                f"[white underline] +{int((koleo_time_to_dt(stop["actual_departure"]) - dep).total_seconds() / 60)}m[/white underline]"
                if stop["actual_departure"]
                else arr_diff
                if idx == len(stops) - 1
                else ""
            )
            arr_diff = dep_diff if idx == 0 else arr_diff
            name = stations[stop["station_id"]]["name"]
            self.print(
                f"[bold green]{self.ftime(arr)}{arr_diff}[/bold green] - [bold red]{self.ftime(dep)}{dep_diff}[/bold red] [purple]{name} {self.format_position(stop["platform"])} [/purple]"
            )

    def format_position(self, platform: str, track: str | None = None):
        res = str(convert_platform_number(platform) or "" if not self.storage.use_roman_numerals else platform)
        if track is not None and track != "":
            if self.storage.platform_first:
                res += f"/{track}"
            else:
                res = f"{track}/{res}"
        return res

    @overload
    async def get_station(self, station: str, quit_on_failure: Literal[True] = True) -> ExtendedStationInfo: ...

    @overload
    async def get_station(
        self, station: str, quit_on_failure: Literal[False] = False
    ) -> ExtendedStationInfo | None: ...

    async def get_station(self, station: str, quit_on_failure: bool = True) -> ExtendedStationInfo | None:
        stations = await self.get_stations()
        stations_by_slugs = await self.get_stations_by_slugs()
        if station in self.storage.aliases:
            slug = self.storage.aliases[station]
        elif station.isnumeric():
            if res := stations.get(int(station)):
                return res
            else:
                if quit_on_failure:
                    await self.error_and_exit(f"Station not found: [underline]{station}[/underline]")
                return
        else:
            slug = name_to_slug(station)
            if self.storage.auto_głównx and slug in GŁÓWNX_STATIONS:
                slug = GŁÓWNX_STATIONS[slug]
            if slug in STATION_NAME_REPLACEMENTS:
                slug = STATION_NAME_REPLACEMENTS[slug]
        try:
            return stations[stations_by_slugs[slug]]
        except KeyError:
            if quit_on_failure:
                await self.error_and_exit(f"Station not found: [underline]{station}[/underline]")
            return

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
        if s == "LEO":
            return "LEO_PLUS"
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

    async def get_stations(self) -> dict[int, ExtendedStationInfo]:
        if not (stations := self.storage.get_cache("stations", convert_keys=int)):
            stations = {i["id"]: i for i in await self.client.get_stations()}
            self.storage.set_cache("stations", stations)

            # its more efficient to do it this way...
            stations_by_slugs = {i["name_slug"]: i["id"] for i in stations.values()}
            self.storage.set_cache("stations_by_slugs", stations_by_slugs)

        return stations

    async def get_stations_by_slugs(self) -> dict[str, int]:
        if not (stations := self.storage.get_cache("stations_by_slugs")):
            await self.get_stations()
            stations = self.storage.get_cache("stations_by_slugs")

        return stations  # type: ignore

    async def select_train_stops(self, train: TrainTimetable, a: str, b: str) -> tuple[int, int]:
        stop_ids = [i["station_id"] for i in train["stops"]]
        stops_len = len(stop_ids)
        if is_index(a) and (stops_len > (a_idx := int(a))):
            a_station = stop_ids[a_idx]
            a_idx = stop_ids.index(a_station)
        else:
            station = await self.get_station(a)
            if station["id"] not in stop_ids:
                await self.error_and_exit(
                    f"Train [underline]{train["train_full_name"]}[/underline] doesn't stop at [underline]{station["name"]}[/underline]"
                )
            else:
                a_station = station["id"]
        a_idx = stop_ids.index(a_station)
        if is_index(b) and (stops_len > (b_idx := int(b))):
            b_station = stop_ids[b_idx]
            b_idx = stop_ids.index(b_station)
            if b_idx == a_idx:
                await self.error_and_exit("Station B has to be after station A (-s / --show_stations)")
        else:
            station = await self.get_station(b)
            if station["id"] not in stop_ids:
                await self.error_and_exit(
                    f"Train [underline]{train["train_full_name"]}[/underline] doesn't stop at [underline]{station["name"]}[/underline]"
                )
            else:
                b_station = station["id"]
        b_idx = stop_ids.index(b_station, a_idx)
        return a_idx, b_idx
