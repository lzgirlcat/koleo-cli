import typing as t
from asyncio import gather
from datetime import datetime

from koleo.api import SeatState, SeatsAvailabilityResponse
from koleo.utils import BRAND_SEAT_TYPE_MAPPING, koleo_time_to_dt, find_empty_compartments, find_empty_doubles

from .train_info import TrainInfo
from .utils import CLASS_COLOR_MAP


class Seats(TrainInfo):
    async def train_passenger_stats_view(
        self,
        brand: str,
        name: str,
        date: datetime,
        stations: tuple[str, str] | None = None,
        type: str | None = None,
        detailed: bool = False,
    ):
        train_calendars = await self.get_train_calendars(brand, name)
        if not (train_id := train_calendars[0]["date_train_map"].get(date.strftime("%Y-%m-%d"))):
            await self.error_and_exit(
                f"This train doesn't run on the selected date: [underline]{date.strftime("%Y-%m-%d")}[/underline]"
            )
        train_details = await self.client.get_train(train_id)
        if train_details["train"]["brand_id"] not in BRAND_SEAT_TYPE_MAPPING:
            await self.error_and_exit(f"Brand [underline]{brand}[/underline] is not supported.")
        train_stops_slugs = [i["station_slug"] for i in train_details["stops"]]
        train_stops_by_slug = {i["station_slug"]: i for i in train_details["stops"]}
        if stations:
            first_station, last_station = [
                i["name_slug"] for i in await gather(*(self.get_station(i) for i in stations))
            ]
            if first_station not in train_stops_slugs:
                await self.error_and_exit(
                    f"Train [underline]{name}[/underline] doesn't stop at [underline]{first_station}[/underline]"
                )
            elif last_station not in train_stops_slugs:
                await self.error_and_exit(
                    f"Train [underline]{name}[/underline] doesn't stop at [underline]{last_station}[/underline]"
                )
        else:
            first_station, last_station = train_stops_slugs[0], train_stops_slugs[-1]
        connections = await self.client.get_connections(
            first_station,
            last_station,
            brand_ids=[train_details["train"]["brand_id"]],
            direct=True,
            date=koleo_time_to_dt(train_stops_by_slug[first_station]["departure"], base_date=date),
        )
        connection = next(
            iter(i for i in connections if i["trains"][0]["train_id"] == train_details["train"]["id"]), None
        )
        if connection is None:
            await self.error_and_exit("Train connection not found:<\nplease try clearing the cache")
        connection_train = connection["trains"][0]
        if connection_train["brand_id"] not in BRAND_SEAT_TYPE_MAPPING:
            await self.error_and_exit(f"Brand [underline]{connection_train["brand_id"]}[/underline] is not supported.")
        await self.show_train_header(
            train_details, train_stops_by_slug[first_station], train_stops_by_slug[last_station]
        )
        await self.train_seat_info(
            connection["id"], type, connection_train["brand_id"], connection_train["train_nr"], detailed=detailed
        )

    async def train_connection_stats_view(self, connection_id: int, type: str | None, detailed: bool = False):
        connection = await self.client.get_connection(connection_id)
        train = connection["trains"][0]
        if train["brand_id"] not in BRAND_SEAT_TYPE_MAPPING:
            await self.error_and_exit(f'Brand [underline]{train["brand_id"]}[/underline] is not supported.')
        train_details = await self.client.get_train(train["train_id"])
        first_stop = next(iter(i for i in train_details["stops"] if i["station_id"] == connection["start_station_id"]))
        last_stop = next(iter(i for i in train_details["stops"] if i["station_id"] == connection["end_station_id"]))
        await self.show_train_header(train_details, first_stop, last_stop)
        await self.train_seat_info(connection_id, type, train["brand_id"], train["train_nr"], detailed=detailed)

    async def seatfinder_view(
        self,
        brand: str,
        name: str,
        date: datetime,
        stations: tuple[str, str] | None = None,
        type: str | None = None,
        mode: t.Literal["fast", "optimized"] = "optimized",
    ):
        train_calendars = await self.get_train_calendars(brand, name)
        if not (train_id := train_calendars[0]["date_train_map"].get(date.strftime("%Y-%m-%d"))):
            await self.error_and_exit(
                f"This train doesn't run on the selected date: [underline]{date.strftime("%Y-%m-%d")}[/underline]"
            )
        train_details = await self.client.get_train(train_id)
        if train_details["train"]["brand_id"] not in BRAND_SEAT_TYPE_MAPPING:
            await self.error_and_exit(f"Brand [underline]{brand}[/underline] is not supported.")
        train_stops_slugs = [i["station_slug"] for i in train_details["stops"]]
        train_stops_by_slug = {i["station_slug"]: i for i in train_details["stops"]}
        if stations:
            first_station, last_station = [
                i["name_slug"] for i in await gather(*(self.get_station(i) for i in stations))
            ]
            if first_station not in train_stops_slugs:
                await self.error_and_exit(
                    f"Train [underline]{name}[/underline] doesn't stop at [underline]{first_station}[/underline]"
                )
            elif last_station not in train_stops_slugs:
                await self.error_and_exit(
                    f"Train [underline]{name}[/underline] doesn't stop at [underline]{last_station}[/underline]"
                )
            required_stops_num = train_stops_slugs.index(last_station) - train_stops_slugs.index(first_station) + 1
        else:
            first_station, last_station = train_stops_slugs[0], train_stops_slugs[-1]
            required_stops_num = len(train_stops_by_slug)

        connections = await self.client.get_connections(
            first_station,
            last_station,
            brand_ids=[train_details["train"]["brand_id"]],
            direct=True,
            date=koleo_time_to_dt(train_stops_by_slug[first_station]["departure"], base_date=date),
        )
        connection = next(
            iter(i for i in connections if i["trains"][0]["train_id"] == train_details["train"]["id"]), None
        )
        if connection is None:
            await self.error_and_exit("Train connection not found:<\nplease try clearing the cache")
        connection_train = connection["trains"][0]
        if connection_train["brand_id"] not in BRAND_SEAT_TYPE_MAPPING:
            await self.error_and_exit(f"Brand [underline]{connection_train["brand_id"]}[/underline] is not supported.")
        await self.show_train_header(
            train_details, train_stops_by_slug[first_station], train_stops_by_slug[last_station]
        )
        await self.train_seat_info(
            connection["id"], type, connection_train["brand_id"], connection_train["train_nr"], detailed=detailed
        )

    async def train_seat_info(
        self, connection_id: int, type: str | None, brand_id: int, train_nr: int, *, detailed: bool = False
    ):
        seat_name_map = BRAND_SEAT_TYPE_MAPPING[brand_id]
        if type is not None:
            if type.isnumeric() and int(type) in seat_name_map:
                types = [int(type)]
            elif type_id := {v: k for k, v in seat_name_map.items()}.get(type):
                types = [type_id]
            else:
                await self.error_and_exit(f"Invalid seat type [underline]{type}[/underline].")
        else:
            types = seat_name_map.keys()
        res: dict[int, SeatsAvailabilityResponse] = {}
        for seat_type in types:
            res[seat_type] = await self.client.get_seats_availability(connection_id, train_nr, seat_type)
        special_compartment_types = {
            j["id"]: j for i in res.values() for j in i["special_compartment_types"] if not j["icon"] == "quiet"
        }
        for seat_type, result in res.items():
            counters: dict[SeatState | t.Literal["SPECIAL"], int] = {
                "FREE": 0,
                "RESERVED": 0,
                "BLOCKED": 0,
                "SPECIAL": 0,
            }
            for seat in result["seats"]:
                if seat["special_compartment_type_id"] in special_compartment_types:
                    counters["SPECIAL"] += 1
                    counters[seat["state"]] += 1
                else:
                    counters[seat["state"]] += 1
            color = CLASS_COLOR_MAP.get(seat_name_map[seat_type], "")
            total = sum(i for i in counters.values())
            if not total:
                continue
            self.print(f"[bold {color}]{seat_name_map[seat_type]}: [/bold {color}]")
            self.print(f"  Free: [{color}]{counters["FREE"]}/{total}, ~{counters["FREE"]/total*100:.1f}%[/{color}]")
            # self.print(f"  Special: [{color}]{counters["SPECIAL"]}/{total}, ~{counters["SPECIAL"]/total*100:.1f}%[/{color}]")
            self.print(f"  Reserved: [{color}]{counters["RESERVED"]}[/{color}]")
            self.print(f"  Blocked: [underline {color}]{counters["BLOCKED"]}[/underline {color}]")
            taken = counters["BLOCKED"] + counters["RESERVED"]
            self.print(f"  Total: [underline {color}]{taken}/{total}, ~{taken/total*100:.1f}%[/underline {color}]")

        if detailed:  # super temporary!!!!!!
            for seat_type, result in res.items():
                type_color = CLASS_COLOR_MAP.get(seat_name_map[seat_type], "")
                self.print(f"[bold {type_color}]{seat_name_map[seat_type]}: [/bold {type_color}]")
                for seat in result["seats"]:
                    color = "green" if seat["state"] == "FREE" else "red"
                    if special := special_compartment_types.get(seat["special_compartment_type_id"]):
                        special = f", {special["icon"].upper().replace("_", " ")}"
                        if color == "green":
                            color = "yellow"
                    else:
                        special = ""
                    self.print(
                        f" [{type_color}]{seat["carriage_nr"]}[/{type_color}] {seat['seat_nr']}: [{color}]{seat["state"]}{special}[/{color}]"
                    )
