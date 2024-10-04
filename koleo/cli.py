import re
from argparse import ArgumentParser
from datetime import datetime, timedelta

from rich.console import Console
from rich.traceback import install

from .api import KoleoAPI
from .storage import DEFAULT_CONFIG_PATH, Storage
from .types import ExtendedBaseStationInfo, TrainDetailResponse, TrainOnStationInfo
from .utils import RemainderString, arr_dep_to_dt, convert_platform_number, name_to_slug, parse_datetime


install(show_locals=True, max_frames=2)


class CLI:
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

    def print(self, text, *args, **kwargs):
        if self.no_color:
            result = re.sub(r"\[[^\]]*\]", "", text)
            print(result)
        else:
            self.console.print(text, *args, **kwargs)

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

    def get_departures(self, station_id: int, date: datetime):
        cache_id = f"dep-{station_id}-{date.strftime("%Y-%m-%d")}"
        trains = self.storage.get_cache(cache_id) or self.storage.set_cache(
            cache_id, self.client.get_departures(station_id, date)
        )
        trains = [
            i
            for i in trains
            if datetime.fromisoformat(i["departure"]).timestamp() > date.timestamp()  # type: ignore
        ]
        table = self.trains_on_station_table(trains)
        self.print(table)
        return table

    def get_arrivals(self, station_id: int, date: datetime):
        cache_id = f"arr-{station_id}-{date.strftime("%Y-%m-%d")}"
        trains = self.storage.get_cache(cache_id) or self.storage.set_cache(
            cache_id, self.client.get_arrivals(station_id, date)
        )
        trains = [
            i
            for i in trains
            if datetime.fromisoformat(i["arrival"]).timestamp() > date.timestamp()  # type: ignore
        ]
        table = self.trains_on_station_table(trains, type=2)
        self.print(table)
        return table

    def full_departures(self, station: str, date: datetime):
        st = self.get_station(station)
        station_info = f"[bold blue][link=https://koleo.pl/dworzec-pkp/{st["name_slug"]}/{date.strftime("%Y-%m-%d")}]{st["name"]} at {date.strftime("%d-%m %H:%M")}[/bold blue] ID: {st["id"]}[/link]"
        self.print(station_info)
        self.get_departures(st["id"], date)

    def full_arrivals(self, station: str, date: datetime):
        st = self.get_station(station)
        station_info = f"[bold blue][link=https://koleo.pl/dworzec-pkp/{st["name_slug"]}/{date.strftime("%Y-%m-%d")}]{st["name"]} at {date.strftime("%d-%m %H:%M")}[/bold blue] ID: {st["id"]}[/link]"
        self.print(station_info)
        self.get_arrivals(st["id"], date)

    def find_station(self, query: str | None):
        if query:
            stations = self.client.find_station(query)
        else:
            stations = self.storage.get_cache("stations") or self.storage.set_cache(
                "stations", self.client.get_stations()
            )
        for st in stations:
            self.print(
                f"[bold blue][link=https://koleo.pl/dworzec-pkp/{st["name_slug"]}]{st["name"]}[/bold blue] ID: {st["id"]}[/link]"
            )

    def train_info(self, brand: str, name: str, date: datetime):
        brand = brand.upper().strip()
        name_parts = name.split(" ")
        if len(name_parts) == 1 and name_parts[0].isnumeric():
            number = int(name_parts[0])
            train_name = ""
        elif len(name) > 1:
            number = int(name_parts.pop(0))
            train_name = " ".join(name_parts)
        else:
            raise ValueError("Invalid train name!")
        brands = self.storage.get_cache("brands") or self.storage.set_cache("brands", self.client.get_brands())
        if brand not in [i["name"] for i in brands]:
            res = {i["logo_text"]: i["name"] for i in brands}.get(brand)
            if not res:
                raise ValueError("Invalid brand name!")
            brand = res
        cache_id = f"tc-{brand}-{number}-{name}"
        try:
            train_calendars = self.storage.get_cache(cache_id) or self.storage.set_cache(
                cache_id, self.client.get_train_calendars(brand, number, train_name)
            )
        except self.client.errors.KoleoNotFound:
            self.print(f'[bold red]Train not found: nr={number}, name="{train_name}"[/bold red]')
            exit(2)
        train_id = train_calendars["train_calendars"][0]["date_train_map"][date.strftime("%Y-%m-%d")]
        train_details = self.client.get_train(train_id)
        brand = next(iter(i for i in brands if i["id"] == train_details["train"]["brand_id"]), {}).get("logo_text", "")
        parts = [f"[red]{brand}[/red] [bold blue]{train_details["train"]["train_full_name"]}[/bold blue]"]
        route_start = arr_dep_to_dt(train_details["stops"][0]["departure"])
        route_end = arr_dep_to_dt(train_details["stops"][-1]["arrival"])
        if route_end.hour < route_start.hour or (
            route_end.hour == route_start.hour and route_end.minute < route_end.minute
        ):
            route_end += timedelta(days=1)
        travel_time = route_end - route_start
        speed = train_details["stops"][-1]["distance"] / 1000 / travel_time.seconds * 3600
        parts.append(
            f"[white]  {travel_time.seconds//3600}h{(travel_time.seconds % 3600)/60:.0f}m {speed:^4.1f}km/h [/white]"
        )
        vehicle_types: dict[str, str] = {
            stop["station_display_name"]: stop["vehicle_type"]
            for stop in train_details["stops"]
            if stop["vehicle_type"]
        }
        if vehicle_types:
            keys = list(vehicle_types.keys())
            start = keys[0]
            for i in range(1, len(keys)):
                if vehicle_types[keys[i]] != vehicle_types[start]:
                    parts.append(f"  {start} - {keys[i]}: [bold green]{vehicle_types[start]}[/bold green]")
                    start = keys[i]
            parts.append(f"  {start} - {keys[-1]}: [bold green]{vehicle_types[start]}[/bold green]")
        self.print("\n".join(parts))
        self.print(self.train_route_table(train_details))

    def connections(self, start: str, end: str, date: datetime, brands: list[str], direct: bool, purchasable: bool):
        start_station = self.get_station(start)
        end_station = self.get_station(end)
        brands = [i.lower().strip() for i in brands]
        api_brands = self.storage.get_cache("brands") or self.storage.set_cache("brands", self.client.get_brands())
        if not brands:
            connection_brands = [i["id"] for i in api_brands]
        else:
            connection_brands = [
                i["id"]
                for i in api_brands
                if i["name"].lower().strip() in brands or i["logo_text"].lower().strip() in brands
            ]
            if not connection_brands:
                self.print(f'[bold red]No brands match: "{', '.join(brands)}"[/bold red]')
                exit(2)
        connections = self.client.get_connections(
            start_station["name_slug"], end_station["name_slug"], connection_brands, date, direct, purchasable
        )
        parts = [
            f"[bold blue]{start_station["name"]} → {end_station["name"]} at {date.strftime("%H:%M %d-%m")}[/bold blue]"
        ]
        for i in connections:
            arr = arr_dep_to_dt(i["arrival"])
            dep = arr_dep_to_dt(i["departure"])
            travel_time = (arr - dep).seconds
            parts.append(
                f"[bold green][link=https://koleo.pl/travel-options/{i["id"]}]{dep.strftime("%H:%M")} - {arr.strftime("%H:%M")}[/bold green] {travel_time//3600}h{(travel_time % 3600)/60:.0f}m {i['distance']}km: [/link]"
            )
            if i["constriction_info"]:
                for constriction in i["constriction_info"]:
                    parts.append(f" [bold red]- {constriction} [/bold red]")
            if len(i["trains"]) == 1:
                train = i["trains"][0]
                stop = next(iter(i for i in train["stops"] if i["station_id"] == train["start_station_id"]), {})
                stop_station = (
                    start_station
                    if stop["station_id"] == start_station["id"]
                    else self.storage.get_cache(f"st-{stop['station_id']}")
                    or self.storage.set_cache(
                        f"st-{stop['station_id']}", self.client.get_station_by_id(stop["station_id"])
                    )
                )
                brand = next(iter(i for i in api_brands if i["id"] == train["brand_id"]), {}).get("logo_text")
                parts[-1] += (
                    f" [red]{brand}[/red] {train["train_full_name"]}[purple] {stop_station['name']} {self.format_position(stop["platform"], stop["track"])}[/purple]"
                )
            else:
                previous_arrival: datetime | None = None
                for train in i["trains"]:
                    brand = next(iter(i for i in api_brands if i["id"] == train["brand_id"]), {}).get("logo_text")

                    fs = next(iter(i for i in train["stops"] if i["station_id"] == train["start_station_id"]), {})
                    fs_station = (
                        start_station
                        if fs["station_id"] == start_station["id"]
                        else self.storage.get_cache(f"st-{fs['station_id']}")
                        or self.storage.set_cache(
                            f"st-{fs['station_id']}", self.client.get_station_by_id(fs["station_id"])
                        )
                    )
                    # fs_arr = arr_dep_to_dt(fs["arrival"])
                    fs_dep = arr_dep_to_dt(fs["departure"])
                    fs_info = f"[bold green]{fs_dep.strftime("%H:%M")} [/bold green][purple]{fs_station['name']} {self.format_position(fs["platform"], fs["track"])}[/purple]"

                    ls = next(iter(i for i in train["stops"] if i["station_id"] == train["end_station_id"]), {})
                    ls_station = (
                        start_station
                        if ls["station_id"] == start_station["id"]
                        else self.storage.get_cache(f"st-{ls['station_id']}")
                        or self.storage.set_cache(
                            f"st-{ls['station_id']}", self.client.get_station_by_id(ls["station_id"])
                        )
                    )
                    ls_arr = arr_dep_to_dt(ls["arrival"])
                    # ls_dep = arr_dep_to_dt(ls["departure"])
                    ls_info = f"[bold green]{ls_arr.strftime("%H:%M")} [/bold green][purple]{ls_station['name']} {self.format_position(ls["platform"], ls["track"])}[/purple]"
                    connection_time = (fs_dep - previous_arrival).seconds if previous_arrival else ""
                    previous_arrival = ls_arr
                    if connection_time:
                        parts.append(
                            f"  {connection_time//3600}h{(connection_time % 3600)/60:.0f}m at [purple]{fs_station['name']}[/purple]"
                        )
                    parts.append(f"  [red]{brand}[/red] {train["train_full_name"]} {fs_info} - {ls_info}")
        self.print("\n".join(parts))

    def trains_on_station_table(self, trains: list[TrainOnStationInfo], type: int = 1):
        parts = []
        brands = self.storage.get_cache("brands") or self.storage.set_cache("brands", self.client.get_brands())
        for train in trains:
            time = train["departure"] if type == 1 else train["arrival"]
            assert time
            brand = next(iter(i for i in brands if i["id"] == train["brand_id"]), {}).get("logo_text")
            parts.append(
                f"[bold green]{time[11:16]}[/bold green] [red]{brand}[/red] {train["train_full_name"]}[purple] {train["stations"][0]["name"]} {self.format_position(train["platform"], train["track"])}[/purple]"
            )
        return "\n".join(parts)

    def train_route_table(self, train: TrainDetailResponse):
        parts = []
        for stop in train["stops"]:
            arr = arr_dep_to_dt(stop["arrival"])
            dep = arr_dep_to_dt(stop["departure"])
            parts.append(
                f"[white underline]{stop["distance"] / 1000:^5.1f}km[/white underline] [bold green]{arr.strftime("%H:%M")}[/bold green] - [bold red]{dep.strftime("%H:%M")}[/bold red] [purple]{stop["station_display_name"]} {self.format_position(stop["platform"])} [/purple]"
            )
        return "\n".join(parts)

    def format_position(self, platform: str, track: str | None = None):
        res = str(convert_platform_number(platform) or "" if not self.storage.use_roman_numerals else platform)
        if track is not None and track != "":
            res += f"/{track}"
        return res

    def get_station(self, station: str) -> ExtendedBaseStationInfo:
        slug = name_to_slug(station)
        try:
            return self.storage.get_cache(f"st-{slug}") or self.storage.set_cache(
                f"st-{slug}", self.client.get_station_by_slug(slug)
            )
        except self.client.errors.KoleoNotFound:
            self.print(f'[bold red]Station not found: "{station}"[/bold red]')
            exit(2)


def main():
    cli = CLI()

    parser = ArgumentParser("koleo", description="Koleo CLI")
    parser.add_argument("-c", "--config", help="Custom config path.", default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--nocolor", help="Disable color output and formatting", action="store_true", default=False)
    subparsers = parser.add_subparsers(title="actions", required=False)  # type: ignore

    departures = subparsers.add_parser(
        "departures", aliases=["d", "dep", "odjazdy", "o"], help="Allows you to list station departures"
    )
    departures.add_argument(
        "station",
        help="The station name",
        default=None,
        nargs="*",
        action=RemainderString,
    )
    departures.add_argument(
        "-d",
        "--date",
        help="the departure date",
        type=lambda s: parse_datetime(s),
        default=datetime.now(),
    )
    departures.add_argument("-s", "--save", help="save the station as your default one", action="store_true")
    departures.set_defaults(func=cli.full_departures, pass_=["station", "date"])

    arrivals = subparsers.add_parser(
        "arrivals", aliases=["a", "arr", "przyjazdy", "p"], help="Allows you to list station departures"
    )
    arrivals.add_argument(
        "station",
        help="The station name",
        default=None,
        nargs="*",
        action=RemainderString,
    )
    arrivals.add_argument(
        "-d",
        "--date",
        help="the arrival date",
        type=lambda s: parse_datetime(s),
        default=datetime.now(),
    )
    arrivals.add_argument("-s", "--save", help="save the station as your default one", action="store_true")
    arrivals.set_defaults(func=cli.full_arrivals, pass_=["station", "date"])

    train_route = subparsers.add_parser(
        "trainroute",
        aliases=["r", "tr", "t", "poc", "pociąg"],
        help="Allows you to show the train's route",
    )
    train_route.add_argument("brand", help="The brand name", type=str)
    train_route.add_argument("name", help="The train name", nargs="+", action=RemainderString)
    train_route.add_argument(
        "-d",
        "--date",
        help="the date",
        type=lambda s: parse_datetime(s),
        default=datetime.now(),
    )
    train_route.set_defaults(func=cli.train_info, pass_=["brand", "name", "date"])

    stations = subparsers.add_parser(
        "stations", aliases=["s", "find", "f", "stacje", "ls", "q"], help="Allows you to find stations by their name"
    )
    stations.add_argument(
        "query",
        help="The station name",
        default=None,
        nargs="*",
        action=RemainderString,
    )
    stations.set_defaults(func=cli.find_station, pass_=["query"])

    connections = subparsers.add_parser(
        "connections",
        aliases=["do", "z", "szukaj", "path"],
        help="Allows you to search for connections from a to b",
    )
    connections.add_argument("start", help="The starting station", type=str)
    connections.add_argument("end", help="The end station", type=str)
    connections.add_argument(
        "-d",
        "--date",
        help="the date",
        type=lambda s: parse_datetime(s),
        default=datetime.now(),
    )
    connections.add_argument(
        "-b", "--brands", help="Brands to include", action="extend", nargs="+", type=str, default=[]
    )
    connections.add_argument(
        "-f",
        "--direct",
        help="whether or not the result should only include direct trains",
        action="store_true",
        default=False,
    )
    connections.add_argument(
        "-p",
        "--purchasable",
        help="whether or not the result should only trains purchasable on koleo",
        action="store_true",
        default=False,
    )
    connections.set_defaults(func=cli.connections, pass_=["start", "end", "brands", "date", "direct", "purchasable"])

    args = parser.parse_args()

    storage = Storage.load(path=args.config)
    client = KoleoAPI()
    cli.client, cli.storage = client, storage
    cli.console.no_color = args.nocolor
    cli.no_color = args.nocolor
    if hasattr(args, "station") and args.station is None:
        args.station = storage.favourite_station
    elif hasattr(args, "station") and args.save:
        storage.favourite_station = args.station
        storage.save()
    if not hasattr(args, "func"):
        if storage.favourite_station:
            cli.full_departures(storage.favourite_station, datetime.now())
        else:
            parser.print_help()
            exit()
    else:
        args.func(**{k: v for k, v in args.__dict__.items() if k in getattr(args, "pass_", [])})
