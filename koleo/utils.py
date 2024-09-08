from datetime import datetime, time

from .types import TimeDict


def parse_datetime(s: str):
    now = datetime.today()
    try:
        dt = datetime.strptime(s, "%d-%m")
        return dt.replace(year=now.year, hour=0, minute=0)
    except ValueError:
        pass
    try:
        return datetime.strptime(s, "%Y-%m-%d").replace(hour=0, minute=0)
    except ValueError:
        pass
    return datetime.combine(now, datetime.strptime(s, "%H:%M").time())


def time_dict_to_dt(s: TimeDict):
    now = datetime.today()
    return datetime.combine(now, time(s["hour"], s["minute"], s["second"]))


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
