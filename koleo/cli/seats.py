import typing as t
from asyncio import gather
from datetime import datetime, timedelta

from koleo.api import SeatState, SeatsAvailabilityResponse, V3ConnectionResult, TrainTimetable
from koleo.utils import BRAND_SEAT_TYPE_MAPPING, koleo_time_to_dt, find_empty_compartments, find_empty_doubles

from .train_info import TrainInfo
from .utils import CLASS_COLOR_MAP


class Seats(TrainInfo):
    async def connection_from_train_calendar(
        self,
        brand: str,
        name: str,
        date: datetime,
        stations: tuple[str, str] | None = None,
    ) -> tuple[V3ConnectionResult, TrainTimetable]:
        train_calendars = await self.get_train_calendars(brand, name)
        if not (train_id := train_calendars[0]["date_train_map"].get(date.strftime("%Y-%m-%d"))):
            await self.error_and_exit(
                f"This train doesn't run on the selected date: [underline]{date.strftime("%Y-%m-%d")}[/underline]"
            )
        train_timetable = await self.client.get_train_timetable(train_id, date)
        if train_timetable["internal_brand_id"] not in BRAND_SEAT_TYPE_MAPPING:
            await self.error_and_exit(f"Brand [underline]{brand}[/underline] is not supported.")
        if stations:
            first_station_index, last_station_index = await self.select_train_stops(train_timetable, *stations)
        else:
            first_station_index, last_station_index = 0, -1
        connections = await self.client.v3_connection_search(
            train_timetable["stops"][first_station_index]["station_id"],
            train_timetable["stops"][last_station_index]["station_id"],
            brand_ids=[train_timetable["commercial_brand_id"]],
            direct=True,
            date=koleo_time_to_dt(train_timetable["stops"][first_station_index]["departure"], base_date=date),
        )
        connection = next(
            iter(i for i in connections if i["legs"][0].get("train_id") == train_timetable["train_id"]), None
        )
        if connection is None:
            await self.error_and_exit("Train connection not found:<\nplease try clearing the cache")
        return connection, train_timetable

    async def connection_from_stations(
        self,
        brand: str,
        name: str,
        date: datetime,
        stations: tuple[str, str],
    ) -> tuple[V3ConnectionResult, TrainTimetable] | tuple[None, None]:
        name = name.strip().lower()
        first_station, last_station = [i["id"] for i in await gather(*(self.get_station(i) for i in stations))]

        brand = brand.lower().strip()
        api_brands = await self.get_brands()
        api_brand = next(
            iter(
                i for i in api_brands if i["name"].lower().strip() == brand or i["logo_text"].lower().strip() == brand
            ),
            None,
        )
        if not api_brand:
            await self.error_and_exit(f"Brand [underline]{brand}[/underline] not found!")

        date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        prev_date = None

        while date != prev_date:
            prev_date = date
            connections = await self.client.v3_connection_search(
                first_station,
                last_station,
                brand_ids=[api_brand["id"]],
                direct=True,
                date=date,
            )
            for i in connections:
                if isinstance(i["departure"], dict) or (date := koleo_time_to_dt(i["departure"])).date() != date.date():
                    break
                if i["legs"][0].get("train_full_name", "").strip().lower() == name:
                    train_timetable = await self.client.get_train_timetable(i["legs"][0]["train_id"], date)
                    return i, train_timetable
        return None, None

    async def train_passenger_stats_view(
        self,
        brand: str,
        name: str,
        date: datetime,
        stations: tuple[str, str] | None = None,
        type: str | None = None,
        detailed: bool = False,
        force: bool = False,
    ):
        if force:
            if stations:
                connection, train_timetable = await self.connection_from_stations(brand, name, date, stations)
                if not connection or not train_timetable:
                    await self.error_and_exit(
                        f"Train [underline]{brand} {name}[/underline] not found at {date.strftime("%Y-%m-%d")} "
                    )
            else:
                await self.error_and_exit(
                    f"[underline]force[/underline] can only be used with stations (-s / --show_stations)"
                )
        else:
            connection, train_timetable = await self.connection_from_train_calendar(brand, name, date, stations)
        if train_timetable["commercial_brand_id"] not in BRAND_SEAT_TYPE_MAPPING:
            await self.error_and_exit(
                f"Brand [underline]{train_timetable["commercial_brand_id"]}[/underline] is not supported."
            )

        if stations:
            first_station_index, last_station_index = await self.select_train_stops(train_timetable, *stations)
        else:
            first_station_index, last_station_index = 0, -1

        legacy_connection_id = await self.client.v3_get_connection_id(connection["uuid"])

        await self.show_train_header(
            train_timetable, train_timetable["stops"][first_station_index], train_timetable["stops"][last_station_index]
        )
        await self.train_seat_info(
            legacy_connection_id,
            type,
            train_timetable["commercial_brand_id"],
            train_timetable["train_nr"],
            detailed=detailed,
        )

    async def train_connection_stats_view(self, connection_id: int, type: str | None, detailed: bool = False):
        connection = await self.client.get_connection(connection_id)
        train_details = connection["trains"][0]
        if train_details["brand_id"] not in BRAND_SEAT_TYPE_MAPPING:
            await self.error_and_exit(f'Brand [underline]{train_details["brand_id"]}[/underline] is not supported.')
        train_timetable = await self.client.get_train_timetable(
            train_details["train_id"], koleo_time_to_dt(connection["departure"])
        )
        first_stop = next(
            iter(i for i in train_timetable["stops"] if i["station_id"] == connection["start_station_id"])
        )
        last_stop = next(iter(i for i in train_timetable["stops"] if i["station_id"] == connection["end_station_id"]))
        await self.show_train_header(train_timetable, first_stop, last_stop)
        await self.train_seat_info(
            connection_id, type, train_details["brand_id"], train_details["train_nr"], detailed=detailed
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
