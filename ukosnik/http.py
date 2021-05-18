"""Small wrapper around Discord endpoints.
Requests should not be handled in any other module.
"""

from typing import Any, Dict, List, Optional
import requests
from requests.models import Response

from ukosnik import __version__
from ukosnik.document import Command


class HTTPRequestException(Exception):
    """Raised when something failed while performing a request."""


class Client:
    """Small Discord HTTP client."""
    def __init__(
        self,
        token: str,
        base_url: str = "https://discord.com/api/v9",
    ) -> None:
        assert token is not None, "Token required"
        assert base_url is not None and base_url.startswith("https://"), "Base URL must use HTTPS"

        self.base_url = base_url.rstrip('/')
        self.headers = {
            "Authorization": token,
            "User-Agent": f"https://github.com/Unoqwy/ukosnik (v{__version__})",
            "Content-Type": "application/json"
        }

    @staticmethod
    def __handle(response: Response) -> Response:
        if response.status_code == 401:
            raise HTTPRequestException(
                "The bot token does not grant access to the required API endpoints.",
                "Possible reasons include: expired token, ungranted scopes.",
            )
        return response

    def get(self, endpoint: str) -> Response:
        return self.__handle(requests.get(f"{self.base_url}/{endpoint}", headers=self.headers))

    def post(self, endpoint: str, data: Dict[str, Any]) -> Response:
        return self.__handle(requests.post(f"{self.base_url}/{endpoint}", headers=self.headers, json=data))

    def delete(self, endpoint: str) -> Response:
        return self.__handle(requests.delete(f"{self.base_url}/{endpoint}", headers=self.headers))

    def get_application_id(self) -> int:
        return self.get("oauth2/applications/@me").json()["id"]


class CommandManager:
    """Contextual wrapper arround command endpoints."""
    def __init__(self, client: Client, application_id: int, guild_id: Optional[int]) -> None:
        self.client = client
        self.application_id = application_id
        self.guild_id = guild_id

        base = f"applications/{self.application_id}"
        if self.guild_id is not None:
            base = f"{base}/guilds/{self.guild_id}"
        self.endpoint = f"{base}/commands"

    def command_endpoint(self, command_id: int) -> str:
        return f"{self.endpoint}/{command_id}"

    def fetch_commands(self) -> List[Command]:
        return self.client.get(self.endpoint).json()

    def upsert_command(self, command: Command) -> Command:
        return self.client.post(self.endpoint, command).json()  # type: ignore

    def delete_command(self, command_id: int):
        self.client.delete(self.command_endpoint(command_id))
