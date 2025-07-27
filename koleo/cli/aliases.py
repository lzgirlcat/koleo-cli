from .base import BaseCli


class Aliases(BaseCli):
    def alias_list_view(self):
        self.print("[bold][green]alias[/green] → [red]station[/red][/bold]:")
        for n, (k, v) in enumerate(self.storage.aliases.items()):
            self.print(f"{n}. [bold][green]{k}[/green] → [red]{v}[/red][/bold]")

    async def alias_add_view(self, alias: str, station: str):
        station_obj = await self.get_station(station)
        self.storage.add_alias(alias, station_obj["name_slug"])

    def alias_remove_view(self, alias: str):
        self.storage.remove_alias(alias)
