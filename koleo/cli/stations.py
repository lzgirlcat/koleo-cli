from .base import BaseCli
from .utils import COUNTRY_MAP


class Stations(BaseCli):
    async def find_station_view(self, query: str | None, type: str | None, country: str | None):
        if query:
            stations = await self.client.find_station(query)
        else:
            stations = (await self.get_stations()).values()
        for st in stations:
            result_info = ""
            if "country" in st:
                if country:
                    c_info = COUNTRY_MAP[st["country"]]
                    if not c_info[0] == country:
                        continue
                else:
                    c_info = COUNTRY_MAP[st["country"]]
                    result_info += c_info[1] if self.storage.use_country_flags_emoji else c_info[0]
            if type:
                if not st["type"].startswith(type):
                    continue
            else:
                if st["type"] == "Quay":
                    result_info += "🚏" if self.storage.use_station_type_emoji else "BUS"
                elif st["type"] == "TopographicalPlace":
                    result_info += "🏛️" if self.storage.use_station_type_emoji else "GROUP"
                else:
                    result_info += "🚉" if self.storage.use_station_type_emoji else "RAIL"
            if result_info:
                result_info += " "
            self.print(
                f"[bold blue][link=https://koleo.pl/dworzec-pkp/{st["name_slug"]}]{result_info}{st["name"]}[/bold blue] ID: {st["id"]}[/link]"
            )
