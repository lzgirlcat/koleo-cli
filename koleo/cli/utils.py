from koleo.api.types import Price, V3Price, ReservationDataPlace


CLASS_COLOR_MAP = {
    "Klasa 2": "bright_green",
    "Economy": "bright_green",
    "Economy Plus": "bright_green",
    "Klasa 1": "bright_cyan",
    "Business": "bright_cyan",
    "Premium": "bright_cyan",
}


COUNTRY_MAP = {
    "Słowacja": ("sk", "🇸🇰"),
    "Ukraina": ("ua ", "🇺🇦"),
    "Niemcy": ("de", "🇩🇪"),
    "Czechy": ("cz", "🇨🇿"),
    "Polska": ("pl", "🇵🇱"),
    "Litwa": ("lt", "🇱🇹"),
    "Węgry": ("hu", "🇭🇺"),
    "Francja": ("fr", "🇫🇷"),
    "Austria": ("at", "🇦🇹"),
    "Anglia": ("en", "🏴󠁧󠁢󠁥󠁮󠁧󠁿"),
    "Belgia": ("be", "🇧🇪"),
    "Niderlandy": ("nl", "🇳🇱"),
    "Estonia": ("ee", "🇪🇪"),
    "Chorwacja": ("hr", "🇭🇷"),
    "Dania": ("dk", "🇩🇰"),
    "Finlandia": ("fi", "🇫🇮"),
    "Luksemburg": ("lu", "🇱🇺"),
    "Rumunia": ("ro", "🇷🇴"),
    "Szwajcaria": ("ch", "🇨🇭"),
    "Szwecja": ("se", "🇸🇪"),
    "Słowenia": ("si", "🇸🇮"),
    "Wielka Brytania": ("gb", "🇬🇧"),
    "Włochy": ("it", "🇮🇹"),
    "Łotwa": ("lv", "🇱🇻"),
    "": ("pl", "🇵🇱"),  # we have to assume...
}

GŁÓWNX_STATIONS = {
    "opole": "opole-glowne",
    "szczecin": "szczecin-glowny",
    "gdynia": "gdynia-glowna",
    "pila": "pila-glowna",
    "bydgoszcz": "bydgoszcz-glowna",
    "ilawa": "ilawa-glowna",
    "zielona-gora": "zielona-gora-glowna",
    "poznan": "poznan-glowny",
    "lowicz": "lowicz-glowny",
    "radom": "radom-glowny",
    "lublin": "lublin-glowny",
    # "kłodzko": "kłodzko-miasto",
    "wroclaw": "wroclaw-glowny",
    "kielce": "kielce-glowne",
    "przemysl": "przemysl-glowny",
    "rzeszow": "rzeszow-glowny",
}


STATION_NAME_REPLACEMENTS = {"zgierz-kontrewers": "zgierz-kontrew", "zajezierze-kolo-deblina": "zajezierze-k-deblina"}


def format_currency(price: str | Price | V3Price):
    if isinstance(price, dict):
        s: str | None = price.get("price") or price.get("value")
        if not s:
            return ""
    else:
        s = price
    return f"{float(s):.2f} zł"


def is_index(s: str):
    return s.isnumeric() or (s[0] == "-" and s[1:].isnumeric())


def format_places(places: list[ReservationDataPlace]):
    res = []
    for place in places:
        type = {"okno": "o", "środek": "ś", "korytarz": "k"}.get(place["type"].lower(), "")
        res.append(f"{place["seat_nr"]}{type}")
    return ", ".join(res)
