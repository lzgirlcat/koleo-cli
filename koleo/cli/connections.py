from asyncio import gather
from datetime import datetime, timedelta

from koleo.api.types import ConnectionDetail
from koleo.utils import koleo_time_to_dt

from .base import BaseCli
from .utils import format_price


class Connections(BaseCli):
    async def connections_view(
        self,
        start: str,
        end: str,
        date: datetime,
        brands: list[str],
        direct: bool,
        include_prices: bool,
        only_purchasable: bool,
        length: int = 1,
    ):
        start_station, end_station, api_brands = await gather(
            self.get_station(start), self.get_station(end), self.get_brands()
        )
        brands = [i.lower().strip() for i in brands]
        if not brands:
            connection_brands = {i["name"]: i["id"] for i in api_brands}
        else:
            connection_brands = {
                i["name"]: i["id"]
                for i in api_brands
                if i["name"].lower().strip() in brands or i["logo_text"].lower().strip() in brands
            }
            if not connection_brands:
                await self.error_and_exit(f'No brands match: [underline]{", ".join(brands)}[/underline]')
        results: list[ConnectionDetail] = []
        fetch_date = date
        while len(results) < length:
            connections = await self.client.get_connections(
                start_station["name_slug"],
                end_station["name_slug"],
                list(connection_brands.values()),
                fetch_date,
                direct,
                only_purchasable,
            )
            if connections:
                fetch_date = koleo_time_to_dt(connections[-1]["departure"]) + timedelta(seconds=(30 * 60) + 1)  # wtf
                results.extend(connections)
            else:
                break
        if include_prices:
            res = await gather(
                *(self.client.get_price(i["id"]) for i in results),
            )
            price_dict = {k: v for k, v in zip((i["id"] for i in results), res)}
        else:
            price_dict = {}
        link = (
            f"https://koleo.pl/rozklad-pkp/{start_station["name_slug"]}/{end_station["name_slug"]}"
            + f"/{date.strftime("%d-%m-%Y_%H:%M")}"
            + f"/{"all" if not direct else "direct"}/{"-".join(connection_brands.keys()) if brands else "all"}"
        )
        parts = [
            f"[bold blue][link={link}]{start_station["name"]} → {end_station["name"]} at {date.strftime("%H:%M %d-%m")}[/link][/bold blue]"
        ]

        for i in results:
            arr = koleo_time_to_dt(i["arrival"])
            dep = koleo_time_to_dt(i["departure"])
            travel_time = (arr - dep).seconds
            date_part = f"{arr.strftime("%d-%m")} " if arr.date() != date.date() else ""
            if price := price_dict.get(i["id"]):
                price_str = f" [bold red]{format_price(price)}[/bold red]"
            else:
                price_str = ""
            parts.append(
                f"[bold green][link=https://koleo.pl/p/{i["id"]}]{date_part}{dep.strftime("%H:%M")} - {arr.strftime("%H:%M")}[/bold green] {travel_time//3600}h{(travel_time % 3600)/60:.0f}m {i['distance']}km{price_str}:[/link]"
            )
            if len(i["trains"]) == 1:
                train = i["trains"][0]
                brand = next(iter(i for i in api_brands if i["id"] == train["brand_id"]), {}).get("logo_text")

                fs = next(iter(i for i in train["stops"] if i["station_id"] == train["start_station_id"]), {})
                fs_station = (
                    start_station
                    if fs["station_id"] == start_station["id"]
                    else await self.get_station_by_id(fs["station_id"])
                )

                ls = next(iter(i for i in train["stops"] if i["station_id"] == train["end_station_id"]), {})
                ls_station = (
                    start_station
                    if ls["station_id"] == start_station["id"]
                    else await self.get_station_by_id(ls["station_id"])
                )

                parts[-1] += (
                    f" [red]{brand}[/red] {train["train_full_name"]}[purple] {fs_station['name']} {self.format_position(fs["platform"], fs["track"])}[/purple] - [purple]{ls_station['name']} {self.format_position(ls["platform"], ls["track"])}[/purple]"
                )
                for constriction in i["constriction_info"]:
                    parts.append(f" [bold red]- {constriction}[/bold red]")
            else:
                for constriction in i["constriction_info"]:
                    parts.append(f" [bold red]- {constriction}[/bold red]")
                previous_arrival: datetime | None = None
                for train in i["trains"]:
                    brand = next(iter(i for i in api_brands if i["id"] == train["brand_id"]), {}).get("logo_text")

                    # first stop

                    fs = next(iter(i for i in train["stops"] if i["station_id"] == train["start_station_id"]), {})
                    fs_station = (
                        start_station
                        if fs["station_id"] == start_station["id"]
                        else await self.get_station_by_id(fs["station_id"])
                    )
                    # fs_arr = arr_dep_to_dt(fs["arrival"])
                    fs_dep = koleo_time_to_dt(fs["departure"])
                    fs_info = f"[bold green]{fs_dep.strftime("%H:%M")} [/bold green][purple]{fs_station['name']} {self.format_position(fs["platform"], fs["track"])}[/purple]"

                    # last stop

                    ls = next(iter(i for i in train["stops"] if i["station_id"] == train["end_station_id"]), {})
                    ls_station = (
                        start_station
                        if ls["station_id"] == start_station["id"]
                        else self.storage.get_cache(f"st-{ls['station_id']}")
                        or await self.get_station_by_id(ls["station_id"])
                    )
                    ls_arr = koleo_time_to_dt(ls["arrival"])
                    # ls_dep = arr_dep_to_dt(ls["departure"])
                    ls_info = f"[bold green]{ls_arr.strftime("%H:%M")} [/bold green][purple]{ls_station['name']} {self.format_position(ls["platform"], ls["track"])}[/purple]"
                    connection_time = (fs_dep - previous_arrival).seconds if previous_arrival else ""
                    previous_arrival = ls_arr
                    if connection_time:
                        parts.append(
                            f"  {connection_time//3600}h{(connection_time % 3600)/60:.0f}m at [purple]{fs_station['name']}[/purple]"
                        )
                    parts.append(f"  [red]{brand}[/red] {train["train_full_name"]} {fs_info} - {ls_info}")
        self.print("\n".join(parts))
