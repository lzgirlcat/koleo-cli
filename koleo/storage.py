import typing as t
from time import time
from dataclasses import dataclass, asdict, field
from sys import platform
from json import dump, load
from os import makedirs, path as ospath


def get_adequate_config_path():
    if platform == "darwin":
        # i dont fucking know nor want to
        return "~/Library/Preferences/koleo-cli/data.json"
    elif "win" in platform:
        # same with this
        return "%USERPROFILE%\\AppData\\Local\\koleo-cli\\data.json"
    else:
        return "~/.config/koleo-cli.json"


DEFAULT_CONFIG_PATH = get_adequate_config_path()


T = t.TypeVar("T")


@dataclass
class Storage:
    favourite_station: str | None = None
    last_searched_connections: list[tuple[str, str]] = field(default_factory=list)
    last_searched_stations: list[str] = field(default_factory=list)
    cache: dict[str, tuple[int, t.Any]] = field(default_factory=dict)

    def __post_init__(self):
        self._path: str

    @classmethod
    def load(cls, *, path: str = DEFAULT_CONFIG_PATH) -> t.Self:
        expanded = ospath.expanduser(path)
        if ospath.exists(expanded):
            with open(expanded, "r") as f:
                data = load(f)
        else:
            data = {}
        storage = cls(**data)
        storage._path = path
        return storage

    def get_cache(self, id: str) -> t.Any | None:
        cache_result = self.cache.get(id)
        if not cache_result:
            return
        expiry, item = cache_result
        if expiry > time():
            return item
        else:
            self.cache.pop(id)
            self.save()

    def set_cache(self, id: str, item: T, ttl: int = 86400) -> T:
        self.cache[id] = (int(time() + ttl), item)
        self.save()
        return item

    def save(self):
        expanded = ospath.expanduser(self._path)
        dir = ospath.dirname(expanded)
        if dir:
            if not ospath.exists(dir):
                makedirs(dir)
        with open(expanded, "w+") as f:
            dump(asdict(self), f)
