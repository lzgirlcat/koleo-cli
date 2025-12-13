from argparse import Action
from datetime import datetime, time, timedelta
from typing import TYPE_CHECKING, Any
from copy import deepcopy

from .api.types import SeatsAvailabilityResponse, TimeDict, TrainComposition

if TYPE_CHECKING:
    from argparse import ArgumentParser, _SubParsersAction


def parse_datetime(s: str):
    try:
        now = datetime.now()
        dt = datetime.strptime(s, "%d-%m")
        return dt.replace(year=now.year, hour=0, minute=0)
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
        now = datetime.now()
        dt = datetime.strptime(s, "%d-%m %H:%M")
        return dt.replace(year=now.year)
    except ValueError:
        pass
    try:
        now = datetime.now()
        dt = datetime.strptime(s, "%H:%M %d-%m")
        return dt.replace(year=now.year)
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
}


def find_empty_compartments(seats: SeatsAvailabilityResponse) -> list[tuple[int, int]]:
    num_taken_seats_in_group: dict[tuple[int, int], int] = {}
    for seat in seats["seats"]:
        key = (int(seat["carriage_nr"]), int(seat["seat_nr"][:-1]))
        num_taken_seats_in_group.setdefault(key, 0)
        if seat["state"] != "FREE":
            num_taken_seats_in_group[key] += 1
    return [k for k, v in num_taken_seats_in_group.items() if v == 0]


SEAT_GROUPS = {
    1: 1,
    3: 1,
    2: 2,
    8: 2,
    5: 3,
    7: 3,
    4: 4,
    6: 4,
}


def get_double_key(seat: int) -> tuple[int, int]:
    # x1, x3 -> x, 1
    # x2, x8 -> x, 2
    # x5, x7 -> x, 3
    # x4, x6 -> x, 4
    # x0, x9 nie istnieją!
    seat_nr = str(seat)
    return int(seat_nr[:-1]), SEAT_GROUPS[int(seat_nr[-1])]


def find_empty_doubles(
    seats: SeatsAvailabilityResponse,
):
    num_taken_seats_in_double: dict[tuple[int, int, int], int] = {}
    for seat in seats["seats"]:
        key = (int(seat["carriage_nr"]), *get_double_key(int(seat["seat_nr"])))
        num_taken_seats_in_double.setdefault(key, 0)
        if seat["state"] != "FREE":
            num_taken_seats_in_double[key] += 1
    return [k for k, v in num_taken_seats_in_double.items() if v == 0]


def duplicate_parser(
    a: "ArgumentParser",
    s: "_SubParsersAction[ArgumentParser]",
    orig_name: str,
    name: str,
    aliases: list[str],
    *,
    help: str | None = None,
    usage: str | None = None,
    defaults_overwrites: dict[str, Any],
):
    d = deepcopy(a)
    d.prog = d.prog.replace(f" {orig_name}", f" {name}")
    if help is not None:
        choice_action = s._ChoicesPseudoAction(name, aliases, help)
        s._choices_actions.append(choice_action)
    if usage is not None:
        d.usage = usage
    if defaults_overwrites:
        d._defaults = {**d._defaults, **defaults_overwrites}
    for i in aliases:
        s._name_parser_map[i] = d
    return d
