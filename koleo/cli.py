from datetime import datetime
from argparse import ArgumentParser

from rich.console import Console
from rich.traceback import install

from .api import KoleoAPI
from .types import TrainOnStationInfo, TrainDetailResponse
from .utils import name_to_slug, parse_datetime, time_dict_to_dt, convert_platform_number
from .storage import Storage, DEFAULT_CONFIG_PATH

install(show_locals=True)


class CLI:
    def __init__(
        self,
        no_color: bool = False,
        client: KoleoAPI | None = None,
        storage: Storage | None = None,
    ) -> None:
        self._client = client
        self._storage = storage
        self.console = Console(color_system="standard", no_color=no_color)

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

    def list_stations(self, name: str): ...

    def get_departures(self, station_id: int, date: datetime):
        trains = self.client.get_departures(station_id, date)
        trains = [
            i
            for i in trains
            if datetime.fromisoformat(i["departure"]).timestamp() > date.timestamp()  # type: ignore
        ]
        table = self.trains_on_station_table(trains)
        self.console.print(table)
        return table

    def get_arrivals(self, station_id: int, date: datetime):
        trains = self.client.get_arrivals(station_id, date)
        trains = [
            i
            for i in trains
            if datetime.fromisoformat(i["arrival"]).timestamp() > date.timestamp()  # type: ignore
        ]
        table = self.trains_on_station_table(trains, type=2)
        self.console.print(table)
        return table

    def full_departures(self, station: str, date: datetime):
        slug = name_to_slug(station)
        st = self.storage.get_cache(f"st-{slug}") or self.storage.set_cache(
            f"st-{slug}", self.client.get_station_by_slug(slug)
        )
        station_info = f"[bold blue]{st["name"]}[/bold blue] ID: {st["id"]}"
        self.console.print(station_info)
        self.get_departures(st["id"], date)

    def full_arrivals(self, station: str, date: datetime):
        slug = name_to_slug(station)
        st = self.storage.get_cache(f"st-{slug}") or self.storage.set_cache(
            f"st-{slug}", self.client.get_station_by_slug(slug)
        )
        station_info = f"[bold blue]{st["name"]}[/bold blue] ID: {st["id"]}"
        self.console.print(station_info)
        self.get_arrivals(st["id"], date)

    def train_info(self, brand: str, name: str, date: datetime):
        brand = brand.upper().strip()
        name = name.strip()
        if name.isnumeric():
            number = int(name)
            train_name = ""
        elif len((parts := name.split(" "))) == 2 or len((parts := name.split("-"))) == 2:
            number, train_name = parts
            number = int(number)
        else:
            raise ValueError("Invalid train name!")
        cache_id = f"tc-{brand}-{number}-{name}"
        train_calendars = self.storage.get_cache(cache_id) or self.storage.set_cache(
            cache_id, self.client.get_train_calendars(brand, number, train_name)
        )
        brands = self.storage.get_cache("brands") or self.storage.set_cache("brands", self.client.get_brands())
        train_id = train_calendars["train_calendars"][0]["date_train_map"][date.strftime("%Y-%m-%d")]
        train_details = self.client.get_train(train_id)
        brand = next(iter(i for i in brands if i["id"] == train_details["train"]["brand_id"]), {}).get("name", "")
        parts = [f"{brand} {train_details["train"]["train_full_name"]}"]
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
                    parts.append(f"[bold green]  {start} - {keys[i]}:[/bold green] {vehicle_types[start]}")
                    start = keys[i]
            parts.append(f"[bold green]  {start} - {keys[-1]}:[/bold green] {vehicle_types[start]}")
        self.console.print("\n".join(parts))
        self.console.print(self.train_route_table(train_details))

    def route(self, start: str, end: str, date: datetime, direct: bool = False, purchasable: bool = False):
        slug = name_to_slug(station)
        st = self.storage.get_cache(f"st-{slug}") or self.storage.set_cache(
            f"st-{slug}", self.client.get_station_by_slug(slug)
        )
        station_info = f"[bold blue]{st["name"]}[/bold blue] ID: {st["id"]}"
        self.console.print(station_info)
        self.get_arrivals(st["id"], date)

    def trains_on_station_table(self, trains: list[TrainOnStationInfo], type: int = 1):
        parts = []
        brands = self.storage.get_cache("brands") or self.storage.set_cache("brands", self.client.get_brands())
        for train in trains:
            time = train["departure"] if type == 1 else train["arrival"]
            assert time
            brand = next(iter(i for i in brands if i["id"] == train["brand_id"]), {}).get("name")
            parts.append(
                f"[bold green]{time[11:16]}[/bold green] {brand} {train["train_full_name"]}[purple] {train["stations"][0]["name"]} [/purple]"
            )
        return "\n".join(parts)

    def train_route_table(self, train: TrainDetailResponse):
        parts = []
        for stop in train["stops"]:
            arr = time_dict_to_dt(stop["arrival"])
            dep = time_dict_to_dt(stop["departure"])
            platform = convert_platform_number(stop["platform"]) or ""
            parts.append(
                f"[white underline]{stop["distance"] / 1000:^5.1f}km[/white underline] [bold green]{arr.strftime("%H:%M")}[/bold green] - [bold red]{dep.strftime("%H:%M")}[/bold red] [purple]{stop["station_display_name"]} {platform} [/purple]"
            )
        return "\n".join(parts)


def main():
    cli = CLI()

    parser = ArgumentParser("koleo", description="Koleo CLI")
    parser.add_argument("-c", "--config", help="Custom config path.", default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--nocolor", help="Disable color output", action="store_true", default=False)
    subparsers = parser.add_subparsers(title="actions", required=False)

    departures = subparsers.add_parser("departures", aliases=["d", "dep"], help="Allows you to list station departures")
    departures.add_argument(
        "station",
        help="The station name",
        default=None,
        nargs="?",
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

    arrivals = subparsers.add_parser("arrivals", aliases=["a", "arr"], help="Allows you to list station departures")
    arrivals.add_argument(
        "station",
        help="The station name",
        default=None,
        nargs="?",
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
        aliases=["r", "tr", "t"],
        help="Allows you to show the train's route",
    )
    train_route.add_argument("brand", help="The brand name", type=str)
    train_route.add_argument("name", help="The train name", type=str)
    train_route.add_argument(
        "-d",
        "--date",
        help="the date",
        type=lambda s: parse_datetime(s),
        default=datetime.now(),
    )
    train_route.set_defaults(func=cli.train_info, pass_=["brand", "name", "date"])

    args = parser.parse_args()

    storage = Storage.load(path=args.config)
    client = KoleoAPI()
    cli.client, cli.storage = client, storage
    cli.console.no_color = args.nocolor
    if hasattr(args, "station") and args.station is None:
        args.station = storage.favourite_station
    elif hasattr(args, "station") and args.save:
        storage.favourite_station = args.station
        storage.save()
    if not hasattr(args, "func"):
        if storage.favourite_station:
            cli.full_departures(storage.favourite_station, datetime.now())
        else:
            raise ValueError("favourite station not set!")
    else:
        args.func(**{k: v for k, v in args.__dict__.items() if k in getattr(args, "pass_", [])})
