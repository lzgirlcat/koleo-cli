import typing as t
from dataclasses import asdict, dataclass, field
from os import makedirs
from os import path as ospath
from sys import platform
from time import time
from subprocess import run

from orjson import dumps, loads, OPT_NON_STR_KEYS


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


class KoleoAuthLike(t.TypedDict):
    _koleo_token: str
    _koleo_refresh_token: t.Optional[str]
    _koleo_token_expiry: t.Optional[int]


@dataclass
class Auth:
    def __post_init__(self):
        self._storage: "Storage"
        self._cache: KoleoAuthLike | None = None

    type: t.Literal["cleartext", "command"]
    data: dict | list
    on_update: list | None = None

    @property
    def value(self) -> KoleoAuthLike:
        if self._cache:
            return self._cache
        elif self.type == "command":
            if not isinstance(self.data, list):
                raise ValueError(f"auth.type==command requires data to be an args list")
            process = run(self.data, capture_output=True)
            process.check_returncode()
            self._cache = loads(process.stdout)
        elif self.type == "cleartext":
            if not isinstance(self.data, dict):
                raise ValueError(f"auth.type==cleartext requires data to be a dict of values")
            self._cache = t.cast(KoleoAuthLike, self.data)
        else:
            raise ValueError(f"invalid auth.type: {self.type}")
        return self._cache  # type: ignore

    def update(self, data):
        self._cache = data
        if self.type == "command" and self.on_update:
            if not isinstance(self.data, list):
                raise ValueError(f"on_update needs to be an args list")
            process = run(self.on_update, input=dumps(data))
            process.check_returncode()
        elif self.type == "cleartext":
            self.data = data
            self._storage._dirty = True
            self._storage.save()


@dataclass
class Storage:
    cache: dict[str, tuple[int, t.Any]] = field(default_factory=dict)
    favourite_station: str | None = None
    disable_cache: bool = False
    use_roman_numerals: bool = False
    aliases: dict[str, str] = field(default_factory=dict)
    show_connection_id: bool = False
    use_country_flags_emoji: bool = True
    use_station_type_emoji: bool = True
    platform_first: bool = False
    auto_głównx: bool = True
    show_seconds: bool = False
    auth: Auth | None = None

    def __post_init__(self):
        self._path: str
        self._dirty = False
        self._ignore_cache = False

    @property
    def dirty(self) -> bool:
        return self._dirty

    @classmethod
    def load(cls, *, path: str = DEFAULT_CONFIG_PATH, ignore_cache: bool = False) -> t.Self:
        expanded = ospath.expanduser(path)
        if ospath.exists(expanded):
            with open(expanded, "rb") as f:
                data = {k: v for k, v in loads(f.read()).items() if k in cls.__dataclass_fields__}
        else:
            data = {}
        storage = cls(**data)
        storage._path = expanded
        storage._ignore_cache = ignore_cache
        if data.get("auth"):
            auth = Auth(**data["auth"])
            auth._storage = storage
            storage.auth = auth
        return storage

    def get_cache(self, id: str, *, convert_keys: t.Any | None = None) -> t.Any | None:
        if self.disable_cache or self._ignore_cache:
            return None
        cache_result = self.cache.get(id)
        if not cache_result:
            return None
        expiry, item = cache_result
        if expiry > time():
            if convert_keys:
                item = {convert_keys(k): v for k, v in item.items()}
                self.cache[id] = (expiry, item)
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

    def clean_cache(self):
        now = time()
        copy = self.cache.copy()
        self.cache = {k: data for k, data in copy.items() if data[0] > now}
        if copy != self.cache:
            self._dirty = True

    def clear_cache(self):
        self.cache = {}
        self._dirty = True

    def save(self):
        dir = ospath.dirname(self._path)
        if dir:
            if not ospath.exists(dir):
                makedirs(dir)
        with open(self._path, "wb") as f:
            self.clean_cache()
            f.write(dumps(asdict(self), option=OPT_NON_STR_KEYS))

    def add_alias(self, alias: str, station: str):
        self.aliases[alias] = station
        self._dirty = True

    def remove_alias(self, alias: str):
        self.aliases.pop(alias, None)
        self._dirty = True
