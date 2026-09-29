import typing as t
from asyncio import gather
from datetime import datetime, timedelta

from koleo.api.types import (
    SeatState,
    SeatsAvailabilityResponse,
    V3ConnectionResult,
    TrainTimetable,
    SpecialCompartmentType,
    CarriageType,
    TrainComposition,
    Seat,
)
from koleo.utils import (
    BRAND_SEAT_TYPE_MAPPING,
    koleo_time_to_dt,
    find_empty_compartments,
    find_empty_doubles,
    find_empty_quads,
    group_seats,
    SeatingGroupType,
)

from .train_info import TrainInfo
from .utils import CLASS_COLOR_MAP


class Seats(TrainInfo):
    async def get_carriage_types(self) -> dict[int, CarriageType]:
        return {
            i["id"]: i
            for i in self.storage.get_cache("ct")
            or self.storage.set_cache("ct", await self.client.get_carriage_types())
        }

    async def connection_from_train_calendar(
        self,
        brand: str,
        name: str,
        date: datetime,
        stations: tuple[str, str] | None = None,
    ) -> tuple[V3ConnectionResult, TrainTimetable]:
        train_calendars = await self.get_v2_train_calendars(brand, name)
        if not (
            train_id := {i["operating_day"]: i["trains"][0] for i in train_calendars}.get(date.strftime("%Y-%m-%d"))[
                "train_id"
            ]
        ):
            self.error_and_exit(
                f"This train doesn't run on the selected date: [underline]{date.strftime("%Y-%m-%d")}[/underline]"
            )
        train_timetable = await self.client.get_train_timetable(train_id, date)
        if train_timetable["internal_brand_id"] not in BRAND_SEAT_TYPE_MAPPING:
            self.error_and_exit(f"Brand [underline]{brand}[/underline] is not supported.")
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
            self.error_and_exit("Train connection not found:<\nplease try clearing the cache")
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
            self.error_and_exit(f"Brand [underline]{brand}[/underline] not found!")

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

    async def get_train_seat_info(
        self, connection_id: int, type: str | None, brand_id: int, train_nr: int
    ) -> tuple[dict[int, SeatsAvailabilityResponse], dict[int, str], dict[int, SpecialCompartmentType]]:
        seat_name_map = BRAND_SEAT_TYPE_MAPPING[brand_id]
        if type is not None:
            if type.isnumeric() and int(type) in seat_name_map:
                types = [int(type)]
            elif type_id := {v: k for k, v in seat_name_map.items()}.get(type):
                types = [type_id]
            else:
                self.error_and_exit(f"Invalid seat type [underline]{type}[/underline].")
        else:
            types = seat_name_map.keys()
        data = {
            seat_type: await self.client.get_seats_availability(connection_id, train_nr, seat_type)
            for seat_type in types
        }
        return (
            data,
            seat_name_map,
            {j["id"]: j for i in data.values() for j in i["special_compartment_types"] if not j["icon"] == "quiet"},
        )

    async def train_seats_view(
        self,
        brand: str,
        name: str,
        date: datetime,
        stations: tuple[str, str] | None = None,
        type: str | None = None,
        mode: t.Literal[0,1,2,3,4] = 0,
        force: bool = False,
    ):
        if force:
            if stations:
                connection, train_timetable = await self.connection_from_stations(brand, name, date, stations)
                if not connection or not train_timetable:
                    self.error_and_exit(
                        f"Train [underline]{brand} {name}[/underline] not found at {date.strftime("%Y-%m-%d")} "
                    )
            else:
                self.error_and_exit(
                    f"[underline]force[/underline] can only be used with stations (-s / --show_stations)"
                )
        else:
            connection, train_timetable = await self.connection_from_train_calendar(brand, name, date, stations)
        if train_timetable["commercial_brand_id"] not in BRAND_SEAT_TYPE_MAPPING:
            self.error_and_exit(
                f"Brand [underline]{train_timetable["commercial_brand_id"]}[/underline] is not supported."
            )

        if stations:
            first_station_index, last_station_index = await self.select_train_stops(train_timetable, *stations)
        else:
            first_station_index, last_station_index = 0, -1

        legacy_connection_id = await self.client.v3_get_connection_id(connection["uuid"])

        await self.show_train_header(
            train_timetable,
            train_timetable["stops"][first_station_index],
            train_timetable["stops"][last_station_index],
            show_basic_route_info=True,
        )
        train_seat_info = await self.get_train_seat_info(
            legacy_connection_id, type, train_timetable["commercial_brand_id"], train_timetable["train_nr"]
        )
        if mode == 0:
            await self.seat_stats_info(*train_seat_info)
        elif mode == 1:
            await self.seat_list(*train_seat_info)
        else:
            # composition = await self.client.get_train_composition(
            #     legacy_connection_id, train_timetable["train_nr"], list(train_seat_info[1].keys())[0]
            # )
            if mode == 2:
                composition = await self.client.get_train_composition(
                    legacy_connection_id, train_timetable["train_nr"], list(train_seat_info[1].keys())[0]
                )
                await self.prettyprint(*train_seat_info, composition)
            elif mode == 3:
                await self.double_finder(*train_seat_info)
            elif mode == 4:
                await self.compartment_finder(*train_seat_info)

    async def train_connection_stats_view(self, connection_id: int, type: str | None, mode: t.Literal[0, 1,2,3,4] = 0):
        connection = await self.client.get_connection(connection_id)
        train_details = connection["trains"][0]
        if train_details["brand_id"] not in BRAND_SEAT_TYPE_MAPPING:
            self.error_and_exit(f'Brand [underline]{train_details["brand_id"]}[/underline] is not supported.')
        train_timetable = await self.client.get_train_timetable(
            train_details["train_id"], koleo_time_to_dt(connection["departure"])
        )
        first_stop = next(
            iter(i for i in train_timetable["stops"] if i["station_id"] == connection["start_station_id"])
        )
        last_stop = next(iter(i for i in train_timetable["stops"] if i["station_id"] == connection["end_station_id"]))
        await self.show_train_header(train_timetable, first_stop, last_stop, show_basic_route_info=True)
        train_seat_info = await self.get_train_seat_info(
            connection_id, type, train_details["brand_id"], train_details["train_nr"]
        )
        if mode == 0:
            await self.seat_stats_info(*train_seat_info)
        elif mode == 1:
            await self.seat_list(*train_seat_info)
        else:
            # composition = await self.client.get_train_composition(
            #     connection_id, train_details["train_nr"], list(train_seat_info[1].keys())[0]
            # )
            if mode == 2:
                composition = await self.client.get_train_composition(
                    connection_id, train_details["train_nr"], list(train_seat_info[1].keys())[0]
                )
                await self.prettyprint(*train_seat_info, composition)
            elif mode == 3:
                await self.double_finder(*train_seat_info)
            elif mode == 4:
                await self.compartment_finder(*train_seat_info)

    async def seat_stats_info(
        self,
        data: dict[int, SeatsAvailabilityResponse],
        seat_name_map: dict[int, str],
        special_compartment_types: dict[int, SpecialCompartmentType],
    ):
        for seat_type, result in data.items():
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
            self.print(f"  Reserved: [{color}]{counters["RESERVED"]}[/{color}]")
            self.print(f"  Blocked: [underline {color}]{counters["BLOCKED"]}[/underline {color}]")
            taken = counters["BLOCKED"] + counters["RESERVED"]
            self.print(f"  Total: [underline {color}]{taken}/{total}, ~{taken/total*100:.1f}%[/underline {color}]")

    async def seat_list(
        self,
        data: dict[int, SeatsAvailabilityResponse],
        seat_name_map: dict[int, str],
        special_compartment_types: dict[int, SpecialCompartmentType],
    ):
        for seat_type, result in data.items():
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

    async def compartment_finder(
        self,
        data: dict[int, SeatsAvailabilityResponse],
        seat_name_map: dict[int, str],
        special_compartment_types: dict[int, SpecialCompartmentType],
    ):
        for seat_type, seats in data.items():
            type_color = CLASS_COLOR_MAP.get(seat_name_map[seat_type], "")
            compartments = find_empty_compartments(seats)
            grouped_result: dict[str, list[str]] = {}
            for carriage, group in compartments:
                grouped_result.setdefault(carriage, [])
                grouped_result[carriage].append(group)
        if not grouped_result:
            return self.print("[bold red]No empty compartments found:<[/bold red]")
        for carriage, compartments in grouped_result.items():
            self.print(
                f" [{type_color}]{carriage}[/{type_color}]: {", ".join([f"{i}x" for i in compartments])}"
                )

    async def double_finder(
        self,
        data: dict[int, SeatsAvailabilityResponse],
        seat_name_map: dict[int, str],
        special_compartment_types: dict[int, SpecialCompartmentType],
    ):
        doubles = []
        grouped_seats: dict[str, dict[str, tuple[Seat, int]]] = {}
        for seat_type, result in data.items():
            for seat in result["seats"]:
                grouped_seats.setdefault(seat["carriage_nr"], {})
                grouped_seats[seat["carriage_nr"]][seat["seat_nr"]] = (seat, seat_type)
            res = find_empty_doubles(
                result
            )
            doubles.extend(res)

        if not doubles:
            return self.print("[bold red]No empty doubles found:<[/bold red]")
        for carriage, *seats in doubles:
            seat_type = grouped_seats[carriage][seats[0]][1]
            type_color = CLASS_COLOR_MAP.get(seat_name_map[seat_type], "")
            specials = [seat["special_compartment_type_id"] for i in seats if (seat:=grouped_seats[carriage][i][0])["special_compartment_type_id"] in special_compartment_types]
            specials = ", ".join(set([special_compartment_types[i]["icon"].upper().replace("_", " ") for i in specials]))
            if specials:
                specials = ": " + specials
            self.print(
                f" [{type_color}]{carriage}[/{type_color}] {"[yellow]" if specials else ""}{" ".join(seats)}{specials}{"[/yellow]" if specials else ""}"
            )

    async def prettyprint(
        self,
        data: dict[int, SeatsAvailabilityResponse],
        seat_name_map: dict[int, str],
        special_compartment_types: dict[int, SpecialCompartmentType],
        train_compostion: TrainComposition,
    ):
        carriage_types = await self.get_carriage_types()
        grouped_seats: dict[str, dict[str, Seat]] = {}
        carriage_seat_types: dict[str, list[int]] = {}
        for seat_type, result in data.items():
            for seat in result["seats"]:
                grouped_seats.setdefault(seat["carriage_nr"], {})
                grouped_seats[seat["carriage_nr"]][seat["seat_nr"]] = seat
                carriage_seat_types.setdefault(seat["carriage_nr"], [])
                if seat_type not in carriage_seat_types[seat["carriage_nr"]]:
                    carriage_seat_types[seat["carriage_nr"]].append(seat_type)
        rendered_composition = []
        previous_carriage_bottom = None
        for carriage in sorted(train_compostion["carriages"], key=lambda x: x["position"]):
            carriage_type = carriage_types[carriage["carriage_type_id"]]
            if (
                carriage_type["key"].endswith("-WR")
                and carriage_type["key"].startswith("IC-")
                and not carriage_type["seats"]
            ):
                rendered_composition.append(RESTAURANT_CAR)
                continue
            elif any(i in carriage_type["image_key"] for i in LOCOMOTIVES):
                rendered_composition.append(LOCOMOTIVE)
            elif not carriage_type["seats"]:
                rendered_composition.append(UNKNOWN_CARRIAGE)
            else:
                carriage_seats = grouped_seats[carriage["number"]]
                res, previous_carriage_bottom = self.render_passenger_carriage(
                    carriage,
                    carriage_type,
                    previous_carriage_bottom,
                    carriage_seats,
                    [seat_name_map[i] for i in carriage_seat_types[carriage["number"]]],
                    special_compartment_types,
                )
                rendered_composition.append(res)
        self.print("\n".join(rendered_composition))

    def render_passenger_carriage(
        self,
        carriage,
        carriage_type: CarriageType,
        previous_carriage_bottom: str | None,
        carriage_seats: dict[str, Seat],
        seat_types: list[str],
        special_compartment_types: dict[int, SpecialCompartmentType],
    ):
        out = ""
        groups = group_seats(carriage_type)
        if any(i in carriage_type["image_key"] for i in MU_TOPS) or any(
            i in carriage_type["image_key"] for i in MU_BOTTOMS
        ):
            if not previous_carriage_bottom or previous_carriage_bottom == MU_BOTTOM:
                carriage_top = MU_TOP
                carriage_bottom = CARRIAGE_BOTTOM
            else:
                carriage_top = CARRIAGE_TOP
                carriage_bottom = MU_BOTTOM

        elif any(i in carriage_type["image_key"] for i in COMBINED_MUS):
            carriage_top, carriage_bottom = MU_TOP, MU_BOTTOM
        else:
            carriage_top, carriage_bottom = CARRIAGE_TOP, CARRIAGE_BOTTOM
        out += carriage_top + "\n"
        if any(i in carriage_type["image_key"] for i in PARTIAL_RESTAURANT_CARS):
            out += RESTAURANT_CAR_SEGMENT
        for idx, (seats, group) in enumerate(groups):
            row, is_reverse = {
                SeatingGroupType.compartment_8_left: (COMPARTMENT_8_SEATS_ROW, False),
                SeatingGroupType.compartment_8_right: (COMPARTMENT_8_SEATS_ROW, True),
                SeatingGroupType.compartment_left: (COMPARTMENT_6_SEATS_ROW, False),
                SeatingGroupType.compartment_right: (COMPARTMENT_6_SEATS_ROW, True),
                SeatingGroupType.airline_2_plus_2: (AIRLINE_2_PLUS_2__ROW, False),
                SeatingGroupType.airline_2_plus_1_left: (AIRLINE_2_PLUS_1__ROW, True),
                SeatingGroupType.airline_2_plus_1_right: (AIRLINE_2_PLUS_1__ROW, False),
                SeatingGroupType.airline_2_left: (AIRLINE_2_ROW, True),
                SeatingGroupType.airline_2_right: (AIRLINE_2_ROW, False),
                SeatingGroupType.airline_1_left: (AIRLINE_1_ROW, True),
                SeatingGroupType.airline_1_right: (AIRLINE_1_ROW, False),
                SeatingGroupType.airline_1_plus_1: (AIRLINE_1_PLUS_1_ROW, False),
            }[group]

            row_seats = []
            special_types = []
            if is_reverse:
                row = reverser(row)
                seats = reversed(seats)
            for i in seats:
                seat = carriage_seats.get(str(i))
                if not seat:
                    color = ""
                elif seat["state"] == "FREE":
                    color = "green"
                elif seat["state"] == "BLOCKED":
                    color = "italic red"
                elif seat["state"] == "RESERVED":
                    color = "red"
                if seat and (special_type := special_compartment_types.get(seat["special_compartment_type_id"])):
                    special_types.append(f"{special_type["icon"].upper().replace("_", " ")}")
                    if color == "green":
                        color = "yellow"
                row_seats.append(f"[{color}]{pad_string(i, is_reverse)}[/{color}]")
            # print(group, row, row_seats)
            out += row.format(*row_seats)
            if special_types:
                out += f" [yellow]{", ".join(special_types)}[/yellow]"
            if (ref := (len(groups) - 1) // 2) == idx:
                out += f" {carriage["number"]}"
            elif ref + 1 == idx:
                for seat_type in seat_types:
                    type_color = CLASS_COLOR_MAP.get(seat_type, "")
                    out += f" [{type_color}]{seat_type}[/{type_color}]"
            elif ref + 2 == idx:
                out += f" {carriage_type["key"]}"
            out += "\n"
        out += carriage_bottom
        return out, carriage_bottom

def pad_string(s: str | int, reverse: bool = False):
    if isinstance(s, int):
        s = str(s)
    if len(s) == 1:
        return s.center(3)
    elif len(s) == 2:
        return s.ljust(3) if not reverse else s.rjust(3)
    return s


LOCOMOTIVE = """
┏━━━━━━━━━━━━━━━━━┓
┃        ●        ┃
┃      ┏━━━┓      ┃
┃      ┃   ┃      ┃
┃      ┗━━━┛      ┃
┃        ●        ┃
┃      ┃   ┃      ┃
┃      ┃   ┃      ┃
┃      ┃   ┃      ┃
┃      ┃   ┃      ┃
┃      ┃   ┃      ┃
┃        ●        ┃
┃        ●        ┃
┃      ┏━━━┓      ┃
┃      ┃   ┃      ┃
┃      ┗━━━┛      ┃
┃        ●        ┃
┗━━━━━━━━━━━━━━━━━┛
""".strip()
MU_TOP = """
┏━━━━━━━━━━━━━━━━━┓
┃      ┏━━━┓      ┃
┃      ┃   ┃      ┃
┃      ┗━━━┛      ┃
┃        ●        ┃
┃      ┃   ┃      ┃
┣━━━━━━━━━━━━━━━━━┫
""".strip()

MU_BOTTOM = """
┣━━━━━━━━━━━━━━━━━┫
┃      ┃   ┃      ┃
┃        ●        ┃
┃      ┏━━━┓      ┃
┃      ┃   ┃      ┃
┃      ┗━━━┛      ┃
┗━━━━━━━━━━━━━━━━━┛
""".strip()


CARRIAGE_TOP = "┏━━━━━━━━━━━━━━━━━┓"
CARRIAGE_BOTTOM = "┗━━━━━━━━━━━━━━━━━┛"
CARRIAGE_ROW = "┃                 ┃"
COMPARTMENT_8_SEATS_ROW = "┃{} {} {} {}  ┃"
COMPARTMENT_6_SEATS_ROW = "┃ {} {} {}     ┃"
AIRLINE_2_PLUS_1__ROW = "┃ {} {}      {}┃"
AIRLINE_2_PLUS_2__ROW = "┃ {} {}  {} {}┃"
AIRLINE_1_ROW = "┃ {}             ┃"
AIRLINE_1_PLUS_1_ROW = "┃ {}          {}┃"
AIRLINE_2_ROW = "┃ {} {}         ┃"
RESTAURANT_CAR = (
    CARRIAGE_TOP
    + "\n"
    + 5 * (CARRIAGE_ROW + "\n")
    + """┃        🍴       ┃"""
    + "\n"
    + 5 * (CARRIAGE_ROW + "\n")
    + CARRIAGE_BOTTOM
)

RESTAURANT_CAR_SEGMENT = 2 * (CARRIAGE_ROW + "\n") + """┃        🍴       ┃""" + "\n" + 2 * (CARRIAGE_ROW + "\n")

UNKNOWN_CARRIAGE = CARRIAGE_TOP + 5 * CARRIAGE_ROW + """┃     unknown     ┃""" + 5 * CARRIAGE_ROW + CARRIAGE_BOTTOM


def reverser(s: str) -> str:
    return s.replace("{}", "123")[::-1].replace("321", "{}")


LOCOMOTIVES = ["IC-locomotive"]

RESTAURANT_CARS = [
    "IC-generic-UIC-Z1-WR",
]

MU_TOPS = [
    "IC-SD85-134",
    "IC-ED160a",
    "IC-ED161a",
    "IC-ED250a",
    "IC-SN84a",
    "IC-ED74a",
    "LEO_PLUS_STADLER_A",
    "KD-NEWAG-45WE-A",
    "ŁKA-36WEd-A",
    "ŁKA-LM-4268-A",
    "PESA-48WEc-B",
]

MU_BOTTOMS = [
    "IC-SD85-133",
    "IC-ED160b",  # lol
    "IC-ED161h",
    "IC-ED250g",
    "IC-SN84b",
    "IC-ED74d",
    "LEO_PLUS_STADLER_B",  # lol two electric boogaloo,
    "KD-NEWAG-45WE-E",
    "ŁKA-36WEd-B",
    "ŁKA-LM-4268-B",
    "PESA-48WEc-A",
]

COMBINED_MUS = ["ŁKA-LM-4268-combined", "ŁKA-L-4268-combined", "ŁKA-36WEd-combined"]


PARTIAL_RESTAURANT_CARS = [
    "IC-ED160d",
    "IC-ED161c",
    "IC-ED250c",
]
