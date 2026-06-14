from asyncio import gather
from datetime import datetime, timedelta

from koleo.api.types import TrainCalendar, TrainTimetable, RealtimeTrainStop
from koleo.utils import koleo_time_to_dt

from .base import BaseCli


class TrainInfo(BaseCli):
    async def get_train_calendars(self, brand: str, name: str) -> list[TrainCalendar]:
        brand = await self.get_brand_by_shortcut(brand, name=name)
        name = name.lower()
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
        await self.train_detail_view(train_id, date=date, show_stations=show_stations)

    async def train_detail_view(self, train_id: int, date: datetime, show_stations: tuple[str, str] | None = None):
        train_timetable = await self.client.get_train_timetable(train_id, date)

        if show_stations:
            first_stop_index, last_stop_index = await self.select_train_stops(train_timetable, *show_stations)
        else:
            first_stop_index, last_stop_index = 0, len(train_timetable["stops"]) - 1

        await self.show_train_header(
            train_timetable, train_timetable["stops"][first_stop_index], train_timetable["stops"][last_stop_index]
        )
        await self.train_route_table(train_timetable["stops"][first_stop_index : last_stop_index + 1])

    async def show_train_header(
        self,
        train_timetable: TrainTimetable,
        first_stop: RealtimeTrainStop,
        last_stop: RealtimeTrainStop,
    ):
        brands, attributes = await gather(self.get_brands(), self.get_train_attributes())
        brand_obj = next(iter(i for i in brands if i["id"] == train_timetable["commercial_brand_id"]), {})
        brand = brand_obj.get("logo_text", "")
        url_brand = await self.get_brand_by_shortcut(brand, name=train_timetable["train_full_name"])

        url = f"https://koleo.pl/pociag/{url_brand}/{train_timetable["train_full_name"].replace(" ", "-", 1).replace(" ", "%20")}/{train_timetable["operating_day"]}"

        self.print(f"[link={url}][red]{brand}[/red] [bold blue]{train_timetable["train_full_name"]}[/bold blue][/link]")

        route_start = koleo_time_to_dt(first_stop["departure"])
        route_end = koleo_time_to_dt(last_stop["arrival"])

        if route_start.day == route_end.day and (
            route_end.hour < route_start.hour
            or (route_end.hour == route_start.hour and route_end.minute < route_end.minute)
        ):
            route_end += timedelta(days=1)

        travel_time = int((route_end - route_start).total_seconds())
        self.print(f"[white]  {travel_time//3600}h{int((travel_time % 3600)/60)}m[/white]")
        if train_timetable["constrictions"]:
            groups: dict[int, list[str]] = {}
            for constriction in train_timetable["constrictions"]:
                groups.setdefault(constriction["attribute_definition_id"], [])
                groups[constriction["attribute_definition_id"]].append(constriction["annotation"])
            for id, annotations in groups.items():
                ann = (
                    (": " + annotations[0] if annotations[0] else "")
                    if len(annotations) == 1
                    else f":\n   • {"\n   • ".join(annotations)}"
                )
                self.print(f"[yellow bold]  ! {attributes[str(id)]["short_name"]}{ann}[/yellow bold]")
