from asyncio import gather
from datetime import datetime, timedelta

from koleo.api.types import (
    ConnectionDetail,
    V3ConnectionResult,
    V3ConnectionLeg,
    TrainAttribute,
    ApiBrand,
    ExtendedStationInfo,
)
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
            f"[bold blue][link={link}]{start_station["name"]} → {end_station["name"]} at {self.ftime(date)} {date.strftime("%d-%m")}[/link][/bold blue]"
        ]

        for i in results:
            arr = koleo_time_to_dt(i["arrival"])
            dep = koleo_time_to_dt(i["departure"])
            travel_time = int((arr - dep).total_seconds())
            date_part = f"{dep.strftime("%d-%m")} " if dep.date() != date.date() else ""
            date_part_2 = f"{arr.strftime("%d-%m")} " if arr.date() != dep.date() else ""
            if price := price_dict.get(i["id"]):
                price_str = f" [bold red]{format_price(price)}[/bold red]"
            else:
                price_str = ""
            parts.append(
                f"[bold green][link=https://koleo.pl/p/{i["id"]}]{date_part}{self.ftime(dep)} - {date_part_2}{self.ftime(arr)}[/bold green] {travel_time//3600}h{(travel_time % 3600)/60:.0f}m {i['distance']}km{price_str}:[/link]"
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
                    fs_info = f"[bold green]{self.ftime(fs_dep)} [/bold green][purple]{fs_station['name']} {self.format_position(fs["platform"], fs["track"])}[/purple]"

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
                    ls_info = f"[bold green]{self.ftime(ls_arr)} [/bold green][purple]{ls_station['name']} {self.format_position(ls["platform"], ls["track"])}[/purple]"
                    connection_time = int((fs_dep - previous_arrival).total_seconds()) if previous_arrival else ""
                    previous_arrival = ls_arr
                    if connection_time:
                        parts.append(
                            f"  {connection_time//3600}h{(connection_time % 3600)/60:.0f}m at [purple]{fs_station['name']}[/purple]"
                        )
                    parts.append(f"  [red]{brand}[/red] {train["train_full_name"]} {fs_info} - {ls_info}")
        self.print("\n".join(parts))

    async def connections_view_workaround(
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
        include_prices = include_prices or only_purchasable
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
        results: list[V3ConnectionResult] = []
        fetch_date = date
        while len(results) < length:
            connections = await self.client.v3_connection_search(
                start_station["id"],
                end_station["id"],
                list(connection_brands.values()),
                fetch_date,
                direct,
            )
            if connections:
                fetch_date = koleo_time_to_dt(connections[-1]["departure"]) + timedelta(seconds=(30 * 60) + 1)  # wtf
                results.extend(connections)
            else:
                break

        results = results[:3]
        res = res = await gather(
            *(self.get_connection_detail(i["uuid"]) for i in results),
        )
        v2_results = {k: v for k, v in zip((i["uuid"] for i in results), res) if v is not None}

        if include_prices:
            res = await gather(
                *(self.client.v3_get_price(i["uuid"]) for i in results),
            )
            price_dict = {k: v for k, v in zip((i["uuid"] for i in results), res) if v is not None}
        else:
            price_dict = {}
        link = (
            f"https://koleo.pl/rozklad-pkp/{start_station["name_slug"]}/{end_station["name_slug"]}"
            + f"/{date.strftime("%d-%m-%Y_%H:%M")}"
            + f"/{"all" if not direct else "direct"}/{"-".join(connection_brands.keys()) if brands else "all"}"
        )
        parts = [
            f"[bold blue][link={link}]{start_station["name"]} → {end_station["name"]} at {self.ftime(date)} {date.strftime("%d-%m")}[/link][/bold blue]"
        ]

        for j in results:
            i = v2_results[j["uuid"]]
            arr = koleo_time_to_dt(i["arrival"])
            dep = koleo_time_to_dt(i["departure"])
            travel_time = int((arr - dep).total_seconds())
            date_part = f"{dep.strftime("%d-%m")} " if dep.date() != date.date() else ""
            date_part_2 = f"{arr.strftime("%d-%m")} " if arr.date() != dep.date() else ""
            if price := price_dict.get(j["uuid"]):
                price_str = f" [bold red]{format_price(price)}[/bold red]"
            elif only_purchasable:
                continue
            else:
                price_str = ""
            parts.append(
                f"[bold green][link=https://koleo.pl/connection/{j["uuid"]}]{date_part}{self.ftime(dep)} - {date_part_2}{self.ftime(arr)}[/bold green] {travel_time//3600}h{(travel_time % 3600)/60:.0f}m {i['distance']}km{price_str}:[/link]"
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
                    fs_info = f"[bold green]{self.ftime(fs_dep)} [/bold green][purple]{fs_station['name']} {self.format_position(fs["platform"], fs["track"])}[/purple]"

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
                    ls_info = f"[bold green]{self.ftime(ls_arr)} [/bold green][purple]{ls_station['name']} {self.format_position(ls["platform"], ls["track"])}[/purple]"
                    connection_time = int((fs_dep - previous_arrival).total_seconds()) if previous_arrival else ""
                    previous_arrival = ls_arr
                    if connection_time:
                        parts.append(
                            f"  {connection_time//3600}h{(connection_time % 3600)/60:.0f}m at [purple]{fs_station['name']}[/purple]"
                        )
                    parts.append(f"  [red]{brand}[/red] {train["train_full_name"]} {fs_info} - {ls_info}")
        self.print("\n".join(parts))

    async def connections_view_v3(
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
        include_prices = include_prices or only_purchasable
        start_station, end_station, api_brands, train_attributes, stations = await gather(
            self.get_station(start),
            self.get_station(end),
            self.get_brands(),
            self.get_train_attributes(),
            self.get_stations(),
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
        results: list[V3ConnectionResult] = []
        fetch_date = date
        while len(results) < length:
            connections = await self.client.v3_connection_search(
                start_station["id"],
                end_station["id"],
                list(connection_brands.values()),
                fetch_date,
                direct,
            )
            if connections:
                fetch_date = koleo_time_to_dt(connections[-1]["departure"]) + timedelta(seconds=(30 * 60) + 1)  # wtf
                results.extend(connections)
            else:
                break
        if include_prices:
            res = await gather(
                *(self.client.v3_get_price(i["uuid"]) for i in results),
            )
            price_dict = {k: v for k, v in zip((i["uuid"] for i in results), res) if v is not None}
        else:
            price_dict = {}
        link = (
            f"https://koleo.pl/rozklad-pkp/{start_station["name_slug"]}/{end_station["name_slug"]}"
            + f"/{date.strftime("%d-%m-%Y_%H:%M")}"
            + f"/{"all" if not direct else "direct"}/{"-".join(connection_brands.keys()) if brands else "all"}"
        )
        parts = [
            f"[bold blue][link={link}]{start_station["name"]} → {end_station["name"]} at {self.ftime(date)} {date.strftime("%d-%m")}[/link][/bold blue]"
        ]

        for i in results:
            arr = koleo_time_to_dt(i["arrival"])
            dep = koleo_time_to_dt(i["departure"])
            travel_time = int((arr - dep).total_seconds())
            date_part = f"{self.ftime(dep)} " if dep.date() != date.date() else ""
            date_part_2 = f"{self.ftime(arr)} " if arr.date() != dep.date() else ""
            if price := price_dict.get(i["uuid"]):
                price_str = f" [bold red]{format_price(price)}[/bold red]"
            elif only_purchasable:
                continue
            else:
                price_str = ""
            parts.append(
                f"[bold green][link=https://koleo.pl/connection/{i["uuid"]}]{date_part}{self.ftime(dep)} - {date_part_2}{self.ftime(arr)}[/bold green] {travel_time//3600}h{(travel_time % 3600)/60:.0f}m{price_str}:[/link]"
            )
            for constriction in i["constrictions"]:
                parts.append(
                    f" [bold red]- {train_attributes[str(constriction["attribute_definition_id"])]["name"]}: {constriction["annotation"]}[/bold red]"
                )
            if len(i["legs"]) == 1 and not i["constrictions"]:
                parts[-1] += " " + self.format_leg(i["legs"][0], api_brands, stations)
            else:
                for leg in i["legs"]:
                    parts.append("  " + self.format_leg(leg, api_brands, stations))

        self.print("\n".join(parts))

    def format_leg(
        self,
        leg: V3ConnectionLeg,
        api_brands: list[ApiBrand],
        stations: dict[str, ExtendedStationInfo],
    ) -> str:
        if leg["leg_type"] == "walk_leg":
            return f"[yellow underline]WALK[/yellow underline] {leg["footpath_duration"]//60}h{(leg["footpath_duration"] % 60):.0f}m from [purple]{stations[str(leg["origin_station_id"])]['name']}[/purple] to [purple]{stations[str(leg["destination_station_id"])]['name']}[/purple]"
        elif leg["leg_type"] == "train_leg":
            brand = next(iter(i for i in api_brands if i["id"] == leg["commercial_brand_id"]), {}).get("logo_text")

            fs = leg["stops_in_leg"][0]
            fs_station = stations[str(fs["station_id"])]
            fs_dep = koleo_time_to_dt(fs["departure"])
            fs_info = f"[bold green]{self.ftime(fs_dep)} [/bold green][purple]{fs_station['name']} {self.format_position(fs["platform"], fs["track"])}[/purple]"

            ls = leg["stops_in_leg"][-1]
            ls_station = stations[str(ls["station_id"])]
            ls_arr = koleo_time_to_dt(ls["arrival"])
            ls_info = f"[bold green]{self.ftime(ls_arr)} [/bold green][purple]{ls_station['name']} {self.format_position(ls["platform"], ls["track"])}[/purple]"

            return f"[red]{brand}[/red] {leg["train_full_name"]} {fs_info} - {ls_info}"
        elif leg["leg_type"] == "station_change_leg":
            return f"{leg["duration"]//60}h{(leg["duration"] % 60):.0f}m at [purple]{stations[str(leg["station_id"])]['name']}[/purple]"
        else:
            return f"Unknown leg: {leg}"

    async def get_connection_detail(self, id: str) -> ConnectionDetail:
        connection_id = await self.client.v3_get_connection_id(id)
        return await self.client.get_connection(connection_id)
