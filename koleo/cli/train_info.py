from asyncio import gather
from datetime import datetime, timedelta

from koleo.api.types import TrainCalendar, TrainDetailResponse, TrainStop
from koleo.utils import koleo_time_to_dt

from .base import BaseCli


class TrainInfo(BaseCli):
    async def get_train_calendars(self, brand: str, name: str) -> list[TrainCalendar]:
        brand = await self.get_brand_by_shortcut(brand, name=name)
        name_parts = name.split(" ")
        if len(name_parts) == 1 and name_parts[0].isnumeric():
            number = int(name_parts[0])
            train_name = ""
        elif len(name_parts) > 1:
            number = int(name_parts.pop(0))
            train_name = " ".join(name_parts)
        else:
            raise ValueError("Invalid train name!")

        cache_id = f"tc-{brand}-{number}-{name}"
        try:
            train_calendars = self.storage.get_cache(cache_id) or self.storage.set_cache(
                cache_id, await self.client.get_train_calendars(brand, number, train_name), ttl=3600
            )
        except self.client.errors.KoleoNotFound:
            await self.error_and_exit(f"Train not found: [underline]nr={number}, name={train_name}[/underline]")
        return train_calendars["train_calendars"]

    async def train_calendar_view(self, brand: str, name: str):
        train_calendars = await self.get_train_calendars(brand, name)
        brands = await self.get_brands()
        for calendar in train_calendars:
            brand_obj = next(iter(i for i in brands if i["id"] == calendar["trainBrand"]), {})
            link = f"https://koleo.pl/pociag/{brand_obj["name"]}/{name.replace(" ", "-", 1).replace(" ", "%20")}"
            brand = brand_obj.get("logo_text", "")
            self.print(
                f"[red][link={link}]{brand}[/red] [bold blue]{calendar['train_nr']}{" "+ v if (v:=calendar.get("train_name")) else ""}[/bold blue]:[/link]"
            )
            for k, v in sorted(calendar["date_train_map"].items(), key=lambda x: datetime.strptime(x[0], "%Y-%m-%d")):
                self.print(f"  [bold green]{k}[/bold green]: [purple]{v}[/purple]")

    async def train_info_view(
        self, brand: str, name: str, date: datetime, closest: bool, show_stations: tuple[str, str] | None = None
    ):
        train_calendars = await self.get_train_calendars(brand, name)
        if closest:
            dates = sorted([datetime.strptime(i, "%Y-%m-%d") for i in train_calendars[0]["dates"]])
            date = next(iter(i for i in dates if i > date)) or next(iter(i for i in reversed(dates) if i < date))
        if not (train_id := train_calendars[0]["date_train_map"].get(date.strftime("%Y-%m-%d"))):
            await self.error_and_exit(
                f"This train doesn't run on the selected date: [underline]{date.strftime("%Y-%m-%d")}[/underline]"
            )
        await self.train_detail_view(train_id, date=date.strftime("%Y-%m-%d"), show_stations=show_stations)

    async def train_detail_view(
        self, train_id: int, date: str | None = None, show_stations: tuple[str, str] | None = None
    ):
        train_details = await self.client.get_train(train_id)

        if show_stations:
            first_stop_slug, last_stop_slug = [
                i["name_slug"] for i in await gather(*(self.get_station(i) for i in show_stations))
            ]
            train_stops_slugs = [i["station_slug"] for i in train_details["stops"]]
            if first_stop_slug not in train_stops_slugs:
                await self.error_and_exit(
                    f"Train [underline]{train_details["train"]["train_name"]}[/underline] doesn't stop at [underline]{first_stop_slug}[/underline]"
                )
            elif last_stop_slug not in train_stops_slugs:
                await self.error_and_exit(
                    f"Train [underline]{train_details["train"]["train_name"]}[/underline] doesn't stop at [underline]{last_stop_slug}[/underline]"
                )
            first_stop, first_stop_index = next(
                iter((i, n) for n, i in enumerate(train_details["stops"]) if i["station_slug"] == first_stop_slug)
            )
            last_stop, last_stop_index = next(
                iter((i, n + 1) for n, i in enumerate(train_details["stops"]) if i["station_slug"] == last_stop_slug)
            )
            if first_stop_index >= last_stop_index:
                await self.error_and_exit("Station B has to be after station A (-s / --show_stations)")
        else:
            first_stop, last_stop = train_details["stops"][0], train_details["stops"][-1]
            first_stop_index, last_stop_index = 0, len(train_details["stops"]) + 1

        await self.show_train_header(train_details, first_stop, last_stop, date)
        self.train_route_table(train_details["stops"][first_stop_index:last_stop_index])

    async def show_train_header(
        self, train_details: TrainDetailResponse, first_stop: TrainStop, last_stop: TrainStop, date: str | None = None
    ):
        brands = await self.get_brands()
        brand_obj = next(iter(i for i in brands if i["id"] == train_details["train"]["brand_id"]), {})
        brand = brand_obj.get("logo_text", "")
        url_brand = await self.get_brand_by_shortcut(brand, name=train_details["train"]["train_full_name"])

        link = f"https://koleo.pl/pociag/{url_brand}/{train_details["train"]["train_full_name"].replace(" ", "-", 1).replace(" ", "%20")}"
        if date:
            link += f"/{date}"
        self.print(
            f"[link={link}][red]{brand}[/red] [bold blue]{train_details["train"]["train_full_name"]}[/bold blue][/link]"
        )

        if train_details["train"]["run_desc"]:
            self.print(f"  {train_details["train"]["run_desc"]}")

        route_start = koleo_time_to_dt(first_stop["departure"])
        route_end = koleo_time_to_dt(last_stop["arrival"])

        if route_start.day == route_end.day and (
            route_end.hour < route_start.hour
            or (route_end.hour == route_start.hour and route_end.minute < route_end.minute)
        ):
            route_end += timedelta(days=1)

        travel_time = int((route_end - route_start).total_seconds())
        speed = (last_stop["distance"] - first_stop["distance"]) / 1000 / travel_time * 3600
        self.print(f"[white]  {travel_time//3600}h{(travel_time % 3600)/60:.0f}m {speed:^4.1f}km/h [/white]")

        vehicle_types: dict[str, str] = {
            stop["station_display_name"]: stop["vehicle_type"]
            for stop in train_details["stops"]
            if stop["vehicle_type"]
            and (koleo_time_to_dt(stop["departure"]) >= route_start and koleo_time_to_dt(stop["arrival"]) <= route_end)
        }
        if vehicle_types:
            keys = list(vehicle_types.keys())
            start = keys[0]
            for i in range(1, len(keys)):
                if vehicle_types[keys[i]] != vehicle_types[start]:
                    self.print(f"  {start} - {keys[i]}: [bold green]{vehicle_types[start]}[/bold green]")
                    start = keys[i]
            self.print(f"  {start} - {keys[-1]}: [bold green]{vehicle_types[start]}[/bold green]")
