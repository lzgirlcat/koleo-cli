from typing import Literal
from shutil import which
from orjson import dumps
from datetime import datetime

from rich.prompt import Prompt

from koleo.storage import Auth
from koleo.api.types import LoginTokenResponse
from .base import BaseCli
from .utils import format_currency

SECRET_TOOL_UPDATER = ["secret-tool", "store", "--label='Koleo-CLI Auth'", "service", "koleo-cli", "account", "default"]
SECRET_TOOL_GETTER = ["secret-tool", "lookup", "service", "koleo-cli", "account", "default"]


CLIENT_ID_TYPE = Literal["web", "android"] | str


class UserManagement(BaseCli):
    async def login(
        self,
        username: str | None,
        password: str | None,
        client_id: CLIENT_ID_TYPE = "web",
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

        credentials = self.auth_from_login_response(res, client_id)
        self.print_auth_info(credentials)

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

    @staticmethod
    def auth_from_login_response(
        res: LoginTokenResponse,
        client_id: CLIENT_ID_TYPE = "web",
    ) -> dict:
        return {
            "_koleo_token": res["access_token"],
            "_koleo_refresh_token": res["refresh_token"],
            "_koleo_token_expiry": res["created_at"] + res["expires_in"],
            "_koleo_client_id": client_id,
        }

    async def refresh_auth_token(
        self,
        refresh_token: str | None = None,
        client_id: CLIENT_ID_TYPE = "web",
        dump: bool = False,
    ):
        if not self.storage.auth:
            return await self.error_and_exit("auth is not set")
        token = refresh_token or self.storage.auth.value["_koleo_refresh_token"]
        if not token:
            return await self.error_and_exit("the refresh token isn't available in the auth provider")

        self.print(f"refreshing token [bold red]{token[-5:]}[/bold red]")

        res = await self.client.refresh_token(token, client_id)
        if dump:
            self.console.print(dumps(res).decode())
            return
        credentials = self.auth_from_login_response(res, client_id)
        self.storage.auth.update(credentials)

        self.print_auth_info(credentials)

    def print_auth_info(self, credentials: dict):
        has_expiry = "_koleo_token_expiry" in credentials
        self.print(f"Token: [bold red]{credentials["_koleo_token"][-5:]}[/bold red]", end="" if has_expiry else "\n")
        if has_expiry:
            self.print(
                f", [green]valid until [bold]{datetime.fromtimestamp(credentials["_koleo_token_expiry"]).strftime("%d-%m-%Y %H:%M:%S")}[/bold]"
            )

    async def get_me(
        self,
    ):
        me = await self.client.get_user()
        self.print(f"Logged in as [green][bold]{me["name"]} {me["surname"]}, {me["email"]}[/bold][/green]")
        self.print(
            f"Koleo Wallet: [red underline bold]{format_currency(me["koleo_wallet_balance"])}[/red underline bold]"
        )
        if me["masscollect_account_number"]:
            colors = ["blue", "magenta", "cyan", "yellow"]
            masscollect = ""
            for idx, part in enumerate(me["masscollect_account_number"].split(" ")):
                if idx > len(colors) - 1:
                    idx = idx - len(colors)
                masscollect += f" [{colors[idx]}]{part}[/{colors[idx]}]"

            self.print(f"Masscollect:[bold]{masscollect}[/bold]")

        self.print_auth_info(self.storage.auth.value)
