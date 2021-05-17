"""Small wrapper around Discord endpoints.
Requests should not be handled in any other module.
"""

from typing import Any, Dict, List
from ukosnik.document import Command
import requests
from requests.models import Response

from ukosnik import __version__


class HTTPRequestException(Exception):
    """Raised when something failed while performing a request."""


class Client:
    """Small Discord HTTP client."""
    def __init__(
        self,
        token: str,
        base_url: str = "https://discord.com/api/v9",
    ):
        assert token is not None, "Token required"
        assert base_url is not None and base_url.startswith("https://"), "Base URL must use HTTPS"

        self.base_url = base_url.removesuffix("/")
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

    def fetch_commands(self, application_id: int) -> List[Command]:
        return self.get(f"applications/{application_id}/commands").json()

    def upsert_command(self, application_id: int, command: Command) -> Command:
        return self.post(f"applications/{application_id}/commands", command).json() # type: ignore

    def delete_command(self, application_id: int, command_id: int):
        self.delete(f"applications/{application_id}/commands/{command_id}")