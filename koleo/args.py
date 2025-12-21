from argparse import ArgumentParser
from asyncio import run
from datetime import datetime
from inspect import isawaitable

from .api import KoleoAPI
from .cli import CLI
from .storage import DEFAULT_CONFIG_PATH, Storage
from .utils import RemainderString, parse_datetime, duplicate_parser


def main():
    cli = CLI()

    parser = ArgumentParser("koleo", description="Koleo CLI")
    parser.add_argument("-c", "--config", help="Custom config path.", default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--ignore_cache", action="store_true", default=False)

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
    departures.set_defaults(func=cli.full_departures_view, pass_=["station", "date"])

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
    arrivals.set_defaults(func=cli.full_arrivals_view, pass_=["station", "date"])

    all_trains = subparsers.add_parser(
        "all", aliases=["w", "wszystkie", "all_trains", "pociagi"], help="Allows you to list all station trains"
    )
    all_trains.add_argument(
        "station",
        help="The station name",
        default=None,
        nargs="*",
        action=RemainderString,
    )
    all_trains.add_argument(
        "-d",
        "--date",
        help="the date",
        type=lambda s: parse_datetime(s),
        default=datetime.now(),
    )
    all_trains.add_argument("-s", "--save", help="save the station as your default one", action="store_true")
    all_trains.set_defaults(func=cli.all_trains_view, pass_=["station", "date"])

    train_route = subparsers.add_parser(
        "trainroute",
        aliases=["r", "tr", "t", "poc", "pociąg"],
        help="Allows you to check the train's route",
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
    train_route.add_argument(
        "-c",
        "--closest",
        help="ignores date, fetches closest date from the train calendar",
        action="store_true",
        default=False,
    )
    train_route.add_argument(
        "-s", "--show_stations", help="limit the result to A->B", action="extend", nargs=2, type=str, default=None
    )
    train_route.set_defaults(func=cli.train_info_view, pass_=["brand", "name", "date", "closest", "show_stations"])

    train_calendar = subparsers.add_parser(
        "traincalendar",
        aliases=["kursowanie", "tc", "k"],
        help="Allows you to check what days the train runs on",
    )
    train_calendar.add_argument("brand", help="The brand name", type=str)
    train_calendar.add_argument("name", help="The train name", nargs="+", action=RemainderString)
    train_calendar.set_defaults(func=cli.train_calendar_view, pass_=["brand", "name"])

    train_detail = subparsers.add_parser(
        "traindetail",
        aliases=["td", "tid", "id", "idpoc"],
        help="Allows you to show the train's route given it's koleo ID",
    )
    train_detail.add_argument(
        "-s", "--show_stations", help="limit the result to A->B", action="extend", nargs=2, type=str, default=None
    )
    train_detail.add_argument("train_id", help="The koleo ID", type=int)
    train_detail.set_defaults(func=cli.train_detail_view, pass_=["train_id", "show_stations"])

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
    stations.add_argument(
        "-t",
        "--type",
        help="filter results by type[rail, bus, group]",
        type=str,
        default=None,
    )
    stations.add_argument(
        "-c",
        "--country",
        help="filter results by country code[pl, de, ...]",
        type=str,
        default=None,
    )
    stations.set_defaults(func=cli.find_station_view, pass_=["query", "type", "country"])

    connections = subparsers.add_parser(
        "connections",
        aliases=["z", "szukaj", "path"],
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
        "-n",
        "--direct",
        help="whether the result should only include direct trains",
        action="store_true",
        default=False,
    )
    connections.add_argument(
        "-p",
        "--include_prices",
        help="whether the result should include the price",
        action="store_true",
        default=False,
    )
    connections.add_argument(
        "--only_purchasable",
        help="whether the result should include only purchasable connections",
        action="store_true",
        default=False,
    )
    connections.add_argument(
        "-l",
        "--length",
        help="fetch at least n connections",
        type=int,
        default=1,
    )
    connections.set_defaults(
        func=cli.connections_view,
        pass_=["start", "end", "brands", "date", "direct", "include_prices", "only_purchasable", "length"],
    )
    destination_connections = duplicate_parser(
        connections,
        subparsers,
        "connections",
        "destination_connections",
        ["destinations", "do", "to"],
        help="Allows you to search for connections from favourite_station to x",
        defaults_overwrites={"start": None, "func": cli.connections_view},
    )
    destination_connections._actions = [i for i in destination_connections._actions if i.dest != "start"]
    destination_connections._positionals._group_actions = [
        i for i in destination_connections._positionals._group_actions if i.dest != "start"
    ]
    v3_connections = duplicate_parser(
        connections,
        subparsers,
        "connections",
        "v3_connections",
        ["z3"],
        help="Allows you to search for connections from a to b using V3 Koleo Search",
        defaults_overwrites={"func": cli.connections_view_v3},
    )

    train_passenger_stats = subparsers.add_parser(
        "trainstats",
        aliases=["ts", "tp", "miejsca", "frekwencja"],
        help="Allows you to check seat allocation info for a train.",
    )
    train_passenger_stats.add_argument("brand", help="The brand name", type=str)
    train_passenger_stats.add_argument("name", help="The train name", nargs="+", action=RemainderString)
    train_passenger_stats.add_argument(
        "-d",
        "--date",
        help="the date",
        type=lambda s: parse_datetime(s),
        default=datetime.now(),
    )
    train_passenger_stats.add_argument(
        "-s", "--stations", help="A->B", action="extend", nargs=2, type=str, default=None
    )
    train_passenger_stats.add_argument(
        "-t", "--type", help="limit the result to seats of a given type", type=str, required=False
    )
    train_passenger_stats.add_argument(
        "--detailed",
        help="whether to display occupancy status for each seat",
        action="store_true",
        default=False,
    )
    train_passenger_stats.set_defaults(
        func=cli.train_passenger_stats_view, pass_=["brand", "name", "date", "stations", "type", "detailed"]
    )

    train_connection_stats = subparsers.add_parser(
        "trainconnectionstats",
        aliases=["tcs"],
        help="Allows you to check the seat allocations on the train connection given it's koleo ID",
    )
    train_connection_stats.add_argument(
        "-t", "--type", help="limit the result to seats of a given type", type=str, required=False
    )
    train_connection_stats.add_argument(
        "--detailed",
        help="whether to display occupancy status for each seat",
        action="store_true",
        default=False,
    )
    train_connection_stats.add_argument("connection_id", help="The koleo ID", type=int)
    train_connection_stats.set_defaults(
        func=cli.train_connection_stats_view, pass_=["connection_id", "type", "detailed"]
    )

    aliases = subparsers.add_parser("aliases", help="Save quick aliases for station names!")
    aliases.set_defaults(func=cli.alias_list_view)
    aliases_subparser = aliases.add_subparsers()
    aliases_add = aliases_subparser.add_parser("add", aliases=["a"], help="add an alias")
    aliases_add.add_argument("alias", help="The alias")
    aliases_add.add_argument(
        "station",
        help="The station name",
        nargs="*",
        action=RemainderString,
    )
    aliases_add.set_defaults(func=cli.alias_add_view, pass_=["alias", "station"])

    aliases_remove = aliases_subparser.add_parser("remove", aliases=["r", "rm"], help="remove an alias")
    aliases_remove.add_argument("alias", help="The alias")
    aliases_remove.set_defaults(func=cli.alias_remove_view, pass_=["alias"])

    clear_cache = subparsers.add_parser(
        "clear_cache",
        help="Allows you to clear koleo-cli cache",
    )
    clear_cache.set_defaults(func="clear_cache")

    args = parser.parse_args()

    storage = Storage.load(path=args.config, ignore_cache=args.ignore_cache)
    client = KoleoAPI()

    async def run_view(func, *args, **kwargs):
        res = func(*args, **kwargs)
        if isawaitable(res):
            try:
                await res
            except SystemExit:
                ...
        await client.close()

    cli.client, cli.storage = client, storage
    cli.init_console(args.nocolor)
    if hasattr(args, "station") and args.station is None:
        if storage.favourite_station is None:
            raise ValueError("favourite_station is not set!")
        args.station = storage.favourite_station
    if hasattr(args, "start") and args.start is None:
        if storage.favourite_station is None:
            raise ValueError("favourite_station is not set!")
        args.start = storage.favourite_station
    elif hasattr(args, "station") and getattr(args, "save", False):
        storage.favourite_station = args.station
        storage._dirty = True
    if not hasattr(args, "func"):  # todo: fix
        if storage.favourite_station:
            run(run_view(cli.full_departures_view, storage.favourite_station, datetime.now()))
        else:
            parser.print_help()
    else:
        if args.func == "clear_cache":
            storage.clear_cache()
        else:
            run(run_view(args.func, **{k: v for k, v in args.__dict__.items() if k in getattr(args, "pass_", [])}))
    if storage.dirty:
        storage.save()
