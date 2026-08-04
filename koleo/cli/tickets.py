from base64 import b64decode
from asyncio import gather
from datetime import datetime
from .base import BaseCli
from .utils import format_currency, is_index

from koleo.api.types import (
    FullOrder,
    Order,
    OrderStatus,
    OrderTravelSummaryLegTypes,
    Brand,
    ExtendedStationInfo,
    Ticket,
)
from koleo.datagrid import DataGrid, create_datagrid, load_image

FULL_CELL, UPPER_CELL, LOWER_CELL, EMPTY_CELL = "\u2588", "\u2580", "\u2584", " "


COLOR_MAP: dict[OrderStatus, str] = {
    "finished": "blue",
    "created": "yellow",
    "paid": "green",
    "refunded": "red",
    "exchanged": "purple",
}


class Tickets(BaseCli):
    async def get_active_orders(self) -> list[Order]:
        return self.storage.get_cache("active_orders") or self.storage.set_cache(
            "active_orders", await self.client.get_active_orders(), 30
        )

    async def active_tickets(
        self,
    ):
        orders = await self.get_active_orders()
        await self.list_orders(orders)

    async def historical_tickets(
        self,
        page: int = 1,
        per_page: int = 20,
    ):
        orders = await self.client.get_inactive_orders(page, per_page)
        await self.list_orders(orders["orders"])

    async def list_orders(self, orders: list[Order]):
        stations, brands = await gather(self.get_stations(), self.get_brands())
        brands_map = {i["id"]: i for i in brands}
        now = datetime.now().astimezone()
        for order in orders:
            start_dt, end_dt = (
                datetime.fromisoformat(order["start_datetime"]),
                datetime.fromisoformat(order["end_datetime"]),
            )
            date_part_2 = f"{end_dt.strftime("%d-%m")} " if start_dt.date() != end_dt.date() else ""
            self.print(
                f"[green bold]{start_dt.strftime("%d-%m")}[/green bold] {self.ftime(start_dt)} [blue bold]{stations[order["start_station_id"]]["name"]}[/blue bold] → [blue bold]{stations[order["end_station_id"]]["name"]}[/blue bold] {date_part_2}{self.ftime(end_dt)}"
            )

            self.print(f" [green]ID: [bold underline]{order["id"]}[/bold underline][/green]")
            refund_possibility_info = (
                f", {format_currency(order["returnable_price"])} refundable until {order["refund_deadline"]}"
                if order["refund_deadline"] and datetime.fromisoformat(order["refund_deadline"]) > now
                else ""
            )
            self.print(
                f" Paid [red underline]{format_currency(order["price"])}[/red underline]{refund_possibility_info}"
            )
            is_unavailable = order["status"] in ("refunded", "exchanged", "being_refunded")
            if order["status"] != "paid":
                refund_info = (
                    f" [underline]{format_currency(order["returnable_price"])}[/underline]"
                    if order["status"] == "refunded"
                    else ""
                )
                self.print(
                    f" [bold {COLOR_MAP[order["status"]]}]{order["status"]}{refund_info}[/bold {COLOR_MAP[order["status"]]}]"
                )

            if not is_unavailable:
                if order["exchange_deadline"] and (until := datetime.fromisoformat(order["exchange_deadline"])) > now:
                    self.print(f" Exchangable until: {order["exchange_deadline"]}")
                elif (
                    order["name_change_deadline"]
                    and (until := datetime.fromisoformat(order["name_change_deadline"])) > now
                ):
                    self.print(f" Name change possible until: {order["name_change_deadline"]}")
            for i in order["travel_summary"]["legs"]:
                self.print(" " + self.format_order_leg(i, brands, stations))

    async def get_order_from_selector(self, selector: str | None) -> FullOrder | None:
        station = None
        index = None
        if selector:
            if selector.isnumeric() and (int_selector := int(selector)) > 50:
                try:
                    return await self.client.get_active_order(int_selector)
                except self.client.errors.KoleoForbidden:
                    return await self.client.get_inactive_order(int_selector)
                except self.client.errors.KoleoNotFound:
                    station = await self.get_station(selector, quit_on_failure=False)
            if not station and is_index(selector):
                index = int_selector
            elif selector.isalpha():
                station = await self.get_station(selector, quit_on_failure=False)

        orders = await self.get_active_orders()
        if not orders:
            resp = await self.client.get_inactive_orders(per_page=20)
            orders = resp["orders"]
        if index is not None:
            return await self.client.get_active_order(orders[index]["id"])
        for i in orders:
            if station and (i["end_station_id"] == station["id"] or i["start_station_id"] == station["id"]):
                return await self.client.get_active_order(i["id"])

    async def show_order(self, selector: str | None, print_codes: bool = True):
        now = datetime.now().astimezone()
        order, brands, stations = await gather(
            self.get_order_from_selector(selector), self.get_brands(), self.get_stations()
        )
        if not order:
            await self.error_and_exit("Order not found :<")

        start_dt, end_dt = (
            datetime.fromisoformat(order["start_datetime"]),
            datetime.fromisoformat(order["end_datetime"]),
        )
        date_part_2 = f"{end_dt.strftime("%d-%m")} " if start_dt.date() != end_dt.date() else ""
        self.print(
            f"[green bold]{start_dt.strftime("%d-%m")}[/green bold] {self.ftime(start_dt)} [blue bold]{stations[order["start_station_id"]]["name"]}[/blue bold] → [blue bold]{stations[order["end_station_id"]]["name"]}[/blue bold] {date_part_2}{self.ftime(end_dt)}"
        )

        refund_possibility_info = (
            f", {format_currency(order["returnable_price"])} refundable until {order["refund_deadline"]}"
            if order["refund_deadline"] and datetime.fromisoformat(order["refund_deadline"]) > now
            else ""
        )
        self.print(f" Paid [red underline]{format_currency(order["price"])}[/red underline]{refund_possibility_info}")
        is_unavailable = order["status"] in ("refunded", "exchanged", "being_refunded")
        if order["status"] != "paid":
            refund_info = (
                f" [underline]{format_currency(order["returnable_price"])}[/underline]"
                if order["status"] == "refunded"
                else ""
            )
            self.print(
                f" [bold {COLOR_MAP[order["status"]]}]{order["status"]}{refund_info}[/bold {COLOR_MAP[order["status"]]}]"
            )

        if not is_unavailable:
            if order["exchange_deadline"] and (until := datetime.fromisoformat(order["exchange_deadline"])) > now:
                self.print(f" Exchangable until: {order["exchange_deadline"]}")
            elif (
                order["name_change_deadline"] and (until := datetime.fromisoformat(order["name_change_deadline"])) > now
            ):
                self.print(f" Name change possible until: {order["name_change_deadline"]}")

        tickets_by_sections: dict[tuple[int, int], list[Ticket]] = {}
        for i in order["tickets"]:
            tickets_by_sections.setdefault((i["start_station_id"], i["end_station_id"]), [])
            tickets_by_sections[(i["start_station_id"], i["end_station_id"])].append(i)
        for leg in order["travel_summary"]["legs"]:
            self.print(
                f" {self.format_order_leg(leg, brands, stations, len([i for i in order["travel_summary"]["legs"] if i["leg_type"] == "train_leg"]) != 1)}"
            )
            if leg["leg_type"] != "train_leg":
                continue

            for ticket in tickets_by_sections[(leg["origin_station_id"], leg["destination_station_id"])]:
                if ticket["normal_passengers_count"] and ticket["discounted_passengers_count"]:
                    passenger_info = f"{ticket["normal_passengers_info"]} + {ticket["discounted_passengers_info"]}"
                elif ticket["normal_passengers_count"]:
                    passenger_info = ticket["normal_passengers_info"]
                else:
                    passenger_info = ticket["discounted_passengers_info"]
                self.print(f"  [blue bold]{ticket["owner_name"]}[/blue bold]: {passenger_info}")
                self.print(
                    f"  [green]{ticket["tariff_name"]}[/green]: [red underline]{format_currency(ticket["total_price"])}[/red underline], {ticket["distance"]}km"
                )
                self.print(f"  Numer Seryjny: [blue bold]{ticket["serial_number"]}[/blue bold]")
                if ticket["seats_info"]:
                    self.indent_lines(self.strip_seats_junk(ticket["seats_info"]))
                if ticket["bike_info"]:
                    self.print(f"  {ticket["bike_info"]}")
                if ticket["bus_info"]:
                    self.print(f"  {ticket["bus_info"]}")
                if print_codes:
                    if ticket["full_extract"] != ticket["seats_info"]:
                        self.indent_lines(ticket["full_extract"].replace(f"\n{ticket["seats_info"]}", ""))
                    try:
                        image = load_image(b64decode(ticket["base64_img"]))
                    except ModuleNotFoundError:
                        await self.error_and_exit(
                            "[bold red]Pillow is needed for printing 2D ticket codes.[/bold red]\nPlease install Pillow or reinstall koleo-cli with Pillow by running:\npip install koleo-cli\\[tickets]",
                            color=False,
                        )
                    data_grid = create_datagrid(image)
                    self.print_data_grid(data_grid)
                    if ticket["emergency_code"]:
                        self.print(
                            f"{ticket["serial_number"]}, [bold]Kod Awaryjny: [underline]{ticket["emergency_code"]}[/underline][/bold]"
                        )

    async def get_order_pdf(self, selector: str | None, output: str):
        order = await self.get_order_from_selector(selector)
        pdf = await self.client.get_order_pdf(order["id"])
        if output == "-":
            from sys import stdout

            stdout.buffer.write(pdf)
        else:
            with open(output, "wb") as f:
                f.write(pdf)

    async def get_order_google_wallet_url(self, selector: str | None, try_open: bool = True):
        order = await self.get_order_from_selector(selector)
        if not order["is_wallet_pass_available"]:
            return await self.error_and_exit("wallet tickets are unavailable for this carrier:<")
        resp = await self.client.get_order_google_wallet_token(order["id"])
        url = f"https://pay.google.com/gp/v/save/{resp["jwt"]}"
        if try_open:
            from shutil import which
            from subprocess import run

            if which("termux-open-url"):
                run(["termux-open-url", url])
            else:
                from webbrowser import open as open_url

                if not open_url(url):
                    self.print(url)
        else:
            self.print(url)

    async def get_order_pkpass(self, selector: str | None, output: str):
        order = await self.get_order_from_selector(selector)
        if not order["is_wallet_pass_available"]:
            return await self.error_and_exit("wallet tickets are unavailable for this carrier:<")
        pkpass = await self.client.get_order_apple_wallet_pass(order["id"])
        if output == "-":
            from sys import stdout

            stdout.buffer.write(pkpass)
        else:
            with open(output, "wb") as f:
                f.write(pkpass)

    def print_data_grid(self, data: DataGrid):
        out = ""
        for y in range(0, len(data), 2):
            for x in range(len(data[y])):
                top = data[y][x]
                if y + 1 < len(data):
                    bottom = data[y + 1][x]
                else:
                    bottom = False
                if top and bottom:
                    out += FULL_CELL
                elif top and not bottom:
                    out += UPPER_CELL
                elif not top and bottom:
                    out += LOWER_CELL
                else:
                    out += EMPTY_CELL
            out += "\n"

        self.print(out.strip())

    @staticmethod
    def strip_seats_junk(s: str) -> str:
        return s.replace("Wagon: 0 ()\nBrak gwarancji miejsca do siedzenia", "Brak gwarancji miejsca do siedzenia")

    def format_order_leg(
        self,
        leg: OrderTravelSummaryLegTypes,
        api_brands: list[Brand],
        stations: dict[int, ExtendedStationInfo],
        show_time: bool = False,
    ) -> str:
        if leg["leg_type"] == "walk_leg":
            return f"[yellow underline]WALK[/yellow underline] {leg["footpath_duration"]//60}h{(leg["footpath_duration"] % 60)}m from [purple]{stations[leg["origin_station_id"]]['name']}[/purple] to [purple]{stations[leg["destination_station_id"]]['name']}[/purple]"
        elif leg["leg_type"] == "train_leg":
            brand = next(iter(i for i in api_brands if i["id"] == leg["train_brand_id"]), {}).get("logo_text")

            time = (
                f"[bold green]{self.ftime(datetime.fromisoformat(leg["departure"]))} [/bold green]" if show_time else ""
            )
            pos = f" {pos}" if (pos := self.format_position(leg["departure_platform"], leg["departure_track"])) else ""
            fs_info = f"{time}[purple]{leg["origin_station_name"]}{pos}[/purple]"

            time = (
                f"[bold green]{self.ftime(datetime.fromisoformat(leg["arrival"]))} [/bold green]" if show_time else ""
            )
            pos = f" {pos}" if (pos := self.format_position(leg["arrival_platform"], leg["arrival_track"])) else ""
            ls_info = f"{time}[purple]{leg["destination_station_name"]}{pos}[/purple]"

            return f"[red]{brand}[/red] {leg["train_full_name"]} {fs_info} - {ls_info}"
        elif leg["leg_type"] == "station_change_leg":
            return f"{leg["duration"]//60}h{int((leg["duration"] % 60))}m at [purple]{stations[leg["station_id"]]['name']}[/purple]"
        else:
            return f"Unknown leg: {leg}"
