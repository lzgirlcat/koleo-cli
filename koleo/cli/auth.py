from typing import Literal
from shutil import which
from subprocess import run
from orjson import dumps

from rich.prompt import Prompt

from koleo.storage import Auth
from .base import BaseCli

SECRET_TOOL_UPDATER = ["secret-tool", "store", "--label='Koleo-CLI Auth'", "service", "koleo-cli", "account", "default"]
SECRET_TOOL_GETTER = ["secret-tool", "lookup", "service", "koleo-cli", "account", "default"]


class Login(BaseCli):
    async def login(
        self,
        username: str | None,
        password: str | None,
        client_id: Literal["web"] | Literal["android"] | str,
        dump: bool = False,
    ):
        if not dump and self.storage.auth:
            self.console.print("[yellow bold]!Auth entry found in config!\nProceeding will overwrite it![/yellow bold]")
            if not Prompt.ask("[red bold]Are you sure? y/n[/red bold]", console=self.console) in "yes":
                return
            self.storage.auth = None
        if not username:
            username = Prompt.ask("username", console=self.console)
        if not password:
            password = Prompt.ask("password", password=True, console=self.console)

        res = await self.client.login_password(username, password, client_id)
        if dump:
            self.console.print(dumps(res).decode())
            return

        credentials = {
            "_koleo_token": res["access_token"],
            "_koleo_refresh_token": res["refresh_token"],
            "_koleo_token_expiry": res["created_at"] + res["expires_in"],
        }

        if not self.storage.auth:
            if (
                which("secret-tool")
                and Prompt.ask(
                    "[blue]Secret tool was found![/blue]\nDo you want to use it for credential storage? y/n",
                    console=self.console,
                )
                in "yes"
            ):
                self.storage.auth = Auth(type="command", data=SECRET_TOOL_GETTER, on_update=SECRET_TOOL_UPDATER)
            else:
                self.storage.auth = Auth(type="cleartext", data={})
                self.storage.auth._storage = self.storage
            self.storage._dirty = True
            self.storage.auth.update(credentials)

    async def get_me(
        self,
        username: str | None,
        password: str | None,
        client_id: Literal["web"] | Literal["android"] | str,
        dump: bool = False,
    ):
        if not dump and self.storage.auth:
            self.console.print("[yellow bold]!Auth entry found in config!\nProceeding will overwrite it![/yellow bold]")
            if not Prompt.ask("[red bold]Are you sure? y/n[/red bold]", console=self.console) in "yes":
                return
            self.storage.auth = None
        if not username:
            username = Prompt.ask("username", console=self.console)
        if not password:
            password = Prompt.ask("password", password=True, console=self.console)

        res = await self.client.login_password(username, password, client_id)
        if dump:
            self.console.print(dumps(res).decode())
            return

        credentials = {
            "_koleo_token": res["access_token"],
            "_koleo_refresh_token": res["refresh_token"],
            "_koleo_token_expiry": res["created_at"] + res["expires_in"],
        }

        if not self.storage.auth:
            if (
                which("secret-tool")
                and Prompt.ask(
                    "[blue]Secret tool was found![/blue]\nDo you want to use it for credential storage? y/n",
                    console=self.console,
                )
                in "yes"
            ):
                self.storage.auth = Auth(type="command", data=SECRET_TOOL_GETTER, on_update=SECRET_TOOL_UPDATER)
            else:
                self.storage.auth = Auth(type="cleartext", data={})
                self.storage.auth._storage = self.storage
            self.storage._dirty = True
            self.storage.auth.update(credentials)
