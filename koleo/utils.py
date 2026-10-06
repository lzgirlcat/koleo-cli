from argparse import Action
from datetime import datetime, time, timedelta, date
from typing import TYPE_CHECKING, Any
from enum import Enum
from copy import deepcopy
# from secrets import token_bytes
# from hashlib import sha256
from statistics import mean

from .api.types import SeatsAvailabilityResponse, TimeDict, TrainComposition, CarriageType, CarriageSeat

if TYPE_CHECKING:
    from argparse import ArgumentParser, _SubParsersAction


def maybe_skip_year(now: datetime, target: datetime):
    if now.month > target.month:
        return now.year + 1
    return now.year


def parse_datetime(s: str):
    now = datetime.now()
    try:
        dt = datetime.strptime(s, "%d-%m")
        return dt.replace(year=maybe_skip_year(now, dt), hour=0, minute=0)
    except ValueError:
        pass
    try:
        return datetime.strptime(s, "%Y-%m-%d").replace(hour=0, minute=0)
    except ValueError:
        pass
    if s[0] in "+-":
        to_zero = []
        num = int("".join([i for i in s if i.isnumeric()]))
        if s[-1] == "h":
            to_zero = ["minute"]
            td = timedelta(hours=num)
        elif s[-1] == "m":
            td = timedelta(minutes=num)
        else:
            to_zero = ["hour", "minute"]
            td = timedelta(days=num)
        start = datetime.now()
        if s[0] != s[1]:
            start = start.replace(**{k: 0 for k in to_zero})  # type: ignore
        if s[0] == "+":
            return start + td
        if s[0] == "-":
            return start - td
    if s[0] == "-":
        return datetime.now().replace(hour=0, minute=0) - timedelta(days=int(s[1:]))
    try:
        dt = datetime.strptime(s, "%d-%m %H:%M")
        return dt.replace(year=maybe_skip_year(now, dt))
    except ValueError:
        pass
    try:
        dt = datetime.strptime(s, "%H:%M %d-%m")
        return dt.replace(year=maybe_skip_year(now, dt))
    except ValueError:
        pass
    try:
        dt = datetime.strptime(s, "%Y-%m-%d %H:%M")
        return dt.replace(year=maybe_skip_year(now, dt))
    except ValueError:
        pass
    return datetime.combine(datetime.today(), datetime.strptime(s, "%H:%M").time())


def koleo_time_to_dt(i: TimeDict | str, *, base_date: datetime | None = None):
    if isinstance(i, str):
        return datetime.fromisoformat(i)
    if not base_date:
        base_date = datetime.today()
    return datetime.combine(base_date, time(i["hour"], i["minute"], i["second"]))


TRANSLITERATIONS = {
    "ł": "l",
    "ń": "n",
    "ą": "a",
    "ę": "e",
    "ś": "s",
    "ć": "c",
    "ó": "o",
    "ź": "z",
    "ż": "z",
    " ": "-",
    "/": "-",
    "_": "-",
    " - ": "-",
}


def name_to_slug(name: str) -> str:
    return "".join([TRANSLITERATIONS.get(char, char) for char in name.lower()])


NUMERAL_TO_ARABIC = {
    "I": 1,
    "II": 2,
    "III": 3,
    "IV": 4,
    "V": 5,
    "VI": 6,
    "VII": 7,
    "VIII": 8,
    "IX": 9,
    "X": 10,
    "XI": 11,  # wtf poznań???
    "XII": 12,  # just to be safe
    "BUS": "BUS",
}


def convert_platform_number(number: str) -> int | None | str:
    if number and number[-1] in "abcdefghi":  # just to be safe...
        arabic = NUMERAL_TO_ARABIC.get(number[:-1])
        return f"{arabic}{number[-1]}" if arabic else None
    return NUMERAL_TO_ARABIC.get(number)


class RemainderString(Action):
    def __call__(self, _, namespace, values: list[str], __):
        setattr(namespace, self.dest, " ".join(values) if values else self.default)


BRAND_SEAT_TYPE_MAPPING = {
    45: {30: "Klasa 2", 31: "Z rowerem"},  # kd premium
    28: {4: "Klasa 1", 5: "Klasa 2"},  # ic
    1: {4: "Klasa 1", 5: "Klasa 2"},  # tlk
    29: {4: "Klasa 1", 5: "Klasa 2"},  # eip
    2: {4: "Klasa 1", 5: "Klasa 2"},  # eic
    43: {  # łs
        11: "Klasa 2",
    },
    47: {  # leo
        17: "Economy",
        18: "Business",
        19: "Premium",
        20: "Economy Plus",
    },
    52: {  # leo plus
        17: "Economy",
        18: "Business",
        19: "Premium",
        20: "Economy Plus",
    },
}


def find_empty_compartments(seats: SeatsAvailabilityResponse) -> list[tuple[str, str]]:
    num_taken_seats_in_group: dict[tuple[str, str], int] = {}
    num_seats_in_group: dict[tuple[str, str], int] = {}
    for seat in seats["seats"]:
        key = (seat["carriage_nr"], seat["seat_nr"][:-1])
        num_taken_seats_in_group.setdefault(key, 0)
        num_seats_in_group.setdefault(key, 0)
        num_seats_in_group[key] += 1
        if seat["state"] != "FREE":
            num_taken_seats_in_group[key] += 1
    return [k for k, v in num_taken_seats_in_group.items() if v == 0 and num_seats_in_group[k] == 6]


SEAT_GROUPS = {
    "1": "1",
    "3": "1",
    "2": "2",
    "8": "2",
    "5": "3",
    "7": "3",
    "4": "4",
    "6": "4",
    "0": "5",
    "9": "5",
}


def get_double_key(seat: str) -> tuple[str, str]:
    # x1, x3 -> x, 1
    # x2, x8 -> x, 2
    # x5, x7 -> x, 3
    # x4, x6 -> x, 4
    # x0, x9 > x, 5
    return seat[:-1], SEAT_GROUPS[seat[-1]]


def seats_from_double_key(key: tuple[str, str]) -> tuple[str, str]:
    reverse_seat_groups: dict[str, list[str]] = {}
    for k, v in SEAT_GROUPS.items():
        reverse_seat_groups.setdefault(v, [])
        reverse_seat_groups[v].append(k)
    endings = reverse_seat_groups[key[1]]
    return f"{key[0]}{endings[0]}", f"{key[0]}{endings[1]}"


def find_empty_doubles(
    seats: SeatsAvailabilityResponse,
) -> list[tuple[str, str, str]]:
    num_taken_seats_in_double: dict[tuple[str, str, str], int] = {}
    num_seats_in_group: dict[tuple[str, str, str], int] = {}
    for seat in seats["seats"]:
        key = (seat["carriage_nr"], *get_double_key(seat["seat_nr"]))
        num_taken_seats_in_double.setdefault(key, 0)
        num_seats_in_group.setdefault(key, 0)
        num_seats_in_group[key] += 1
        if seat["state"] != "FREE":
            num_taken_seats_in_double[key] += 1
    return [(k[0], *seats_from_double_key(k[-2:])) for k, v in num_taken_seats_in_double.items() if v == 0 and num_seats_in_group[k] == 2]


def find_empty_quads(
    seats: SeatsAvailabilityResponse,
) -> list[tuple[str, str, str, str, str]]:
    num_taken_seats_in_double: dict[tuple[str, str, str], int] = {}
    num_seats_in_group: dict[tuple[str, str, str], int] = {}
    for seat in seats["seats"]:
        key = (seat["carriage_nr"], *get_double_key(seat["seat_nr"]))
        num_taken_seats_in_double.setdefault(key, 0)
        num_seats_in_group.setdefault(key, 0)
        num_seats_in_group[key] += 1
        if seat["state"] != "FREE":
            num_taken_seats_in_double[key] += 1
    return [(k[0], *seats_from_double_key(k[-2:])) for k, v in num_taken_seats_in_double.items() if v == 0 and num_seats_in_group[k] == 2]


class SeatingGroupType(int, Enum):
    airline_2_plus_2 = 1
    airline_2_plus_1_right = 2
    airline_2_plus_1_left = 3
    airline_2_left = 4
    airline_2_right = 5
    airline_1_left = 6
    airline_1_right = 7
    compartment_left = 8
    compartment_right = 9
    compartment_8_left = 10
    compartment_8_right = 11
    airline_1_plus_1 = 12

def group_seats(
    carriage: CarriageType
) -> list[tuple[list[str], SeatingGroupType]]:
    seats_by_row: dict[int, list[CarriageSeat]] = {}
    for seat in carriage["seats"]:
        keys = list(seats_by_row.keys())
        key = seat["x"]
        for i in keys:
            if abs(key - i) < 8:
                key = i
        seats_by_row.setdefault(key, [])
        seats_by_row[key].append(seat)
    seat_type_heights: dict[int, int] = {
        i["id"]: i["height"] for i in carriage["seat_types"]
    }
    out = []
    for row, seats in seats_by_row.items():
        num_in_row = len(seats)
        max_y = max(*[i["y"] for i in seats]) if num_in_row >1 else seats[0]["y"]
        diffs = list(set([(b["y"] - a["y"]) & ~1 for a, b in zip(seats, seats[1:])]))
        simplified_diffs = []
        for diff in diffs:
            if not simplified_diffs or abs(simplified_diffs[-1] - diff) > 3:
                simplified_diffs.append(diff)
        avg_seat_type_height = mean([seat_type_heights[i["seat_type_id"]] for i in seats])
        # yandere dev type shit lol
        if not diffs:
            if num_in_row == 1:
                if (max_y * 2) - 200 > 0:
                    type = SeatingGroupType.airline_1_right
                else:
                    type = SeatingGroupType.airline_1_left
        elif len(simplified_diffs) == 1:
            if num_in_row == 2:
                if diffs[0] > avg_seat_type_height * 2:
                    type = SeatingGroupType.airline_1_plus_1
                elif (max_y * 2) - 200 > 0:
                    type = SeatingGroupType.airline_2_right
                else:
                    type = SeatingGroupType.airline_2_left
            elif num_in_row == 3:
                if (max_y * 2) - 170 >= 0:
                    type = SeatingGroupType.compartment_right
                else:
                    type = SeatingGroupType.compartment_left
            elif num_in_row == 4:
                if (max_y * 2) - 200 > 0:
                    type = SeatingGroupType.compartment_8_right
                else:
                    type = SeatingGroupType.compartment_8_left
            else:
                raise ValueError("Failed to match row type :<")
        else:
            if num_in_row == 4:
                type = SeatingGroupType.airline_2_plus_2
            elif num_in_row == 3:
                if diffs[0] > diffs[1]:
                   type = SeatingGroupType.airline_2_plus_1_left
                else:
                    type = SeatingGroupType.airline_2_plus_1_right
            else:
                raise ValueError("Failed to match row type :<")
        out.append(([i["nr"] for i in sorted(seats, key=lambda x: x["y"], reverse=True)], type))
    return out


def duplicate_parser(
    argument_parser: "ArgumentParser",
    subparsers: "_SubParsersAction[ArgumentParser]",
    name: str,
    aliases: list[str] = [],
    *,
    help: str | None = None,
    usage: str | None = None,
    defaults_overwrites: dict[str, Any] | None = None,
):
    duplicate = deepcopy(argument_parser)
    # need for actions to be displayed in help
    choice_action = subparsers._ChoicesPseudoAction(name, aliases, help)
    subparsers._choices_actions.append(choice_action)

    duplicate._defaults = {
        **argument_parser._defaults,
        **{
            k.removeprefix("+"): (
                argument_parser._defaults[key] + v
                if k.startswith("+") and (key := k.removeprefix("+")) in argument_parser._defaults
                else v
            )
            for k, v in (defaults_overwrites or {}).items()
        },
    }
    return subparsers.add_parser(name, parents=[duplicate], aliases=aliases, usage=usage, add_help=False)


def find_continuous_sections(dates: list[date]) -> list[tuple[date, date]]:
    dates = sorted(set(dates))
    if not dates:
        return []
    sections = []
    current = previous = dates[0]
    for i in dates[1:]:
        if (i - previous).days != 1:
            sections.append((current, previous))
            current = i
        previous = i
    sections.append((current, previous))
    return sections

# def genereate_koleo_deviceid():
#    # in the android apk it's generated {android_id}-{first_installation_time}
#    return sha256(token_bytes(32) + int(datetime.now().timestamp()).to_bytes(8)).hexdigest()
