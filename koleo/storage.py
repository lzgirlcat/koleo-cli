import typing as t
from dataclasses import asdict, dataclass, field
from os import makedirs
from os import path as ospath
from sys import platform
from time import time

from orjson import dumps, loads, OPT_NON_STR_KEYS


if t.TYPE_CHECKING:
    from yt_dlp.cookies import YoutubeDLCookieJar


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
class Auth:
    def __post_init__(self):
        self._cache: dict | None = None

    type: t.Literal["text", "command", "yt-dlp-browser"]
    data: str

    def get_auth(self) -> dict[str, str]:
        if self._cache:
            return self._cache
        if self.type == "yt-dlp-browser":
            try:
                from yt_dlp.cookies import extract_cookies_from_browser
            except ImportError as e:
                raise ImportError(
                    "This feature requires the 'yt-dlp' package. " "Please install it with 'pip install yt-dlp'."
                ) from e
            browser, _, profile = self.data.partition(",")
            cookies: "YoutubeDLCookieJar" = extract_cookies_from_browser(browser, profile or None)
            self._cache = {
                cookie.name: cookie.value
                for cookie in cookies
                if (cookie.domain == "koleo.pl" or cookie.domain.endswith(".koleo.pl")) and cookie.value
            }
        elif self.type == "command":
            from subprocess import run

            process = run(self.data, capture_output=True)
            self._cache = loads(process.stdout)
        elif self.type == "str":
            self._cache = t.cast(dict[str, str], loads(self.data))
        else:
            raise ValueError(f"invalid auth.type: {self.type}")
        return self._cache  # type: ignore


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
        return storage

    def get_cache(self, id: str) -> t.Any | None:
        if self.disable_cache or self._ignore_cache:
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
