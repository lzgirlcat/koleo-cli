from argparse import Action
from datetime import datetime, time, timedelta

from .types import TimeDict


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
    if s[0] == "+":
        return datetime.now().replace(hour=0, minute=0) + timedelta(days=int(s[1:]))
    try:
        now = datetime.now()
        dt = datetime.strptime(s, "%d-%m %H:%M")
        return dt.replace(year=now.year)
    except ValueError:
        pass
    return datetime.combine(datetime.now(), datetime.strptime(s, "%H:%M").time())


def arr_dep_to_dt(i: TimeDict | str):
    if isinstance(i, str):
        return datetime.fromisoformat(i)
    now = datetime.today()
    return datetime.combine(now, time(i["hour"], i["minute"], i["second"]))


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
    return NUMERAL_TO_ARABIC.get(number)


class RemainderString(Action):
    def __call__(self, _, namespace, values: list[str], __):
        setattr(namespace, self.dest, " ".join(values) if values else self.default)
