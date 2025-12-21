from asyncio import gather
from datetime import datetime, timedelta

from .base import BaseCli
from koleo.utils import koleo_time_to_dt


class StationBoard(BaseCli):
    async def get_arrivals(self, station_id: int, date: datetime):
        cache_id = f"arr-{station_id}-{date.strftime("%Y-%m-%d")}"
        return self.storage.get_cache(cache_id) or self.storage.set_cache(
            cache_id, await self.client.get_arrivals(station_id, date)
        )

    async def get_departures(self, station_id: int, date: datetime):
        cache_id = f"dep-{station_id}-{date.strftime("%Y-%m-%d")}"
        return self.storage.get_cache(cache_id) or self.storage.set_cache(
            cache_id, await self.client.get_departures(station_id, date)
        )

    async def full_departures_view(self, station: str, date: datetime):
        st = await self.get_station(station)
        station_info = f"[bold blue][link=https://koleo.pl/dworzec-pkp/{st["name_slug"]}/odjazdy/{date.strftime("%Y-%m-%d")}]{st["name"]} at {date.strftime("%d-%m")} {self.ftime(date)}[/bold blue] ID: {st["id"]}[/link]"
        self.print(station_info)
        trains = [
            i
            for i in await self.get_departures(st["id"], date)
            if datetime.fromisoformat(i["departure"]).timestamp() > date.timestamp()  # type: ignore
        ]
        await self.trains_on_station_table(trains)

    async def full_arrivals_view(self, station: str, date: datetime):
        st = await self.get_station(station)
        station_info = f"[bold blue][link=https://koleo.pl/dworzec-pkp/{st["name_slug"]}/przyjazdy/{date.strftime("%Y-%m-%d")}]{st["name"]} at {date.strftime("%d-%m")} {self.ftime(date)}[/bold blue] ID: {st["id"]}[/link]"
        self.print(station_info)
        trains = [
            i
            for i in await self.get_arrivals(st["id"], date)
            if datetime.fromisoformat(i["arrival"]).timestamp() > date.timestamp()  # type: ignore
        ]
        await self.trains_on_station_table(trains, type=2)

    async def all_trains_view(self, station: str, date: datetime):
        st = await self.get_station(station)
        station_info = f"[bold blue][link=https://koleo.pl/dworzec-pkp/{st["name_slug"]}/odjazdy/{date.strftime("%Y-%m-%d")}]{st["name"]} at {date.strftime("%d-%m")} {self.ftime(date)}[/bold blue] ID: {st["id"]}[/link]"
        self.print(station_info)
        departures, arrivals, brands = await gather(
            self.get_departures(st["id"], date), self.get_arrivals(st["id"], date), self.get_brands()
        )

        trains = sorted(
            [(i, 1) for i in departures] + [(i, 2) for i in arrivals],
            key=lambda train: (
                datetime.fromisoformat(train[0]["departure"]) + timedelta(microseconds=1)  # type: ignore
                if train[1] == 1
                else (datetime.fromisoformat(train[0]["arrival"]))  # type: ignore
            ).timestamp(),
        )
        trains = [
            (i, type)
            for i, type in trains
            if datetime.fromisoformat(i["departure"] if type == 1 else i["arrival"]).timestamp() > date.timestamp()  # type: ignore
        ]
        for train, type in trains:
            time = (
                f"[bold green]{self.ftime(koleo_time_to_dt(train['departure']))}[/bold green]"  # type: ignore
                if type == 1
                else f"[bold yellow]{self.ftime(koleo_time_to_dt(train['arrival']))}[/bold yellow]"  # type: ignore
            )
            if self.no_color:
                time = ("o" if type == 1 else "p") + time
            brand = next(iter(i for i in brands if i["id"] == train["brand_id"]), {}).get("logo_text")
            self.print(
                f"{time} [red]{brand}[/red] {train["train_full_name"]}[purple] {train["stations"][0]["name"]} {self.format_position(train["platform"], train["track"])}[/purple]"
            )
