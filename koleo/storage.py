import typing as t
from dataclasses import asdict, dataclass, field
from json import dump, load
from os import makedirs
from os import path as ospath
from sys import platform
from time import time


def get_adequate_config_path() -> str:
    if platform == "darwin":
        # i dont fucking know nor want to
        return "~/Library/Preferences/koleo-cli/data.json"
    if "win" in platform:
        # same with this
        return "%USERPROFILE%\\AppData\\Local\\koleo-cli\\data.json"
    return "~/.config/koleo-cli.json"


DEFAULT_CONFIG_PATH = get_adequate_config_path()


T = t.TypeVar("T")


@dataclass
class Storage:
    favourite_station: str | None = None
    cache: dict[str, tuple[int, t.Any]] = field(default_factory=dict)
    disable_cache: bool = False
    use_roman_numerals: bool = False

    def __post_init__(self):
        self._path: str
        self._dirty = False

    @property
    def dirty(self) -> bool:
        return self._dirty

    @classmethod
    def load(cls, *, path: str = DEFAULT_CONFIG_PATH) -> t.Self:
        expanded = ospath.expanduser(path)
        if ospath.exists(expanded):
            with open(expanded) as f:
                data = load(f)
        else:
            data = {}
        storage = cls(**data)
        storage._path = expanded
        return storage

    def get_cache(self, id: str) -> t.Any | None:
        if self.disable_cache:
            return None
        cache_result = self.cache.get(id)
        if not cache_result:
            return None
        expiry, item = cache_result
        if expiry > time():
            return item
        else:
            self.cache.pop(id)
            self._dirty = True

    def set_cache(self, id: str, item: T, ttl: int = 86400) -> T:
        if self.disable_cache:
            return item
        self.cache[id] = (int(time() + ttl), item)
        self._dirty = True
        return item

    def save(self):
        dir = ospath.dirname(self._path)
        if dir:
            if not ospath.exists(dir):
                makedirs(dir)
        with open(self._path, "w+") as f:
            self.clean()
            dump(asdict(self), f, indent=True)

    def clean(self):
        now = time()
        copy = self.cache.copy()
        self.cache = {k: data for k, data in copy.items() if data[0] > now}
        if copy != self.cache:
            self._dirty = True
