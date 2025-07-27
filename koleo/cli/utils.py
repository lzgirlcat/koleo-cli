from koleo.api.types import Price


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
    "": ("pl", "🇵🇱"),  # we have to assume...
}


def format_price(price: str | Price):
    if isinstance(price, dict):
        price = price["value"]
    return f"{float(price):.2f} zł"
