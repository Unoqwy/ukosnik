"""Configuration document.
This module contains class definitions and functions to read from parsed file.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TypedDict, Union, get_args
import re
from enum import Enum
import ukosnik.docent as doc


# Errors
class ContextualError(doc.ReadError):
    """Error adding context to a child error that was raised."""


class ValidationError(doc.ReadError):
    """Raised when a value doesn't pass validation (e.g. pattern restriction)."""


class InvalidOptionTypeError(doc.ReadError):
    """Raised when an option type cannot be parsed (e.g. has a typo)."""


# Constants
NAME_PATTERN = re.compile(r"^[\w-]{1,32}$")


class MetaType(Enum):
    """Meta class type. Used to print more context in errors."""

    COMMAND = "command"
    OPTION = "option"


class CommandOptionType(Enum):
    """docs/interactions/slash-commands#applicationcommandoptiontype"""

    SUB_COMMAND = 1
    SUB_COMMAND_GROUP = 2
    STRING = 3
    INTEGER = 4
    BOOLEAN = 5
    USER = 6
    CHANNEL = 7
    ROLE = 8
    MENTIONABLE = 9

    @staticmethod
    def from_str(name: str):
        """Parses an option type from string. Case do not matter.
        Aliases: SUBCOMMAND/SUB_COMMAND, SUBCOMMAND_GROUP/SUB_COMMAND_GROUP.
        """

        key = name.upper()
        if key.startswith("SUBCOMMAND"):
            key = "SUB_COMMAND" + key[len("SUBCOMMAND"):]
        if key in CommandOptionType.__dict__:
            return CommandOptionType[key]
        raise InvalidOptionTypeError(f"'{name.upper()}' is not a known command option type.")


# Typed dicts
class Meta(TypedDict):
    """Shared meta fields for other typed dicts. Related to `MetaType`."""

    name: str
    description: str


class Command(Meta):
    """docs/interactions/slash-commands#applicationcommand
    Fields `id` and `application_id` are present only when fetched from the API.
    """

    id: int
    application_id: int
    options: Optional[List["CommandOption"]]
    default_permission: Optional[bool]


class CommandOption(Meta):
    """docs/interactions/slash-commands#applicationcommandoption"""

    type: int
    required: Optional[bool]
    choices: Optional[List["CommandOptionChoice"]]
    options: Optional[List["CommandOption"]]


class CommandOptionChoice(TypedDict):
    """docs/interactions/slash-commands#applicationcommandoptionchoice"""

    name: str
    value: Union[str, int]


# Classes
@dataclass
class Document:
    """Main configuration document.
    Attributes' dictionnaries can be sent raw to the Discord API. The Typed Dicts are
    conform to types described on https://discord.com/developers/docs/interactions/slash-commands.

    Attributes:
        commands — command list, already validated, command dicts can be sent raw to Discord API
    """

    commands: List[Command]


# Readers
def read(doc_dict: Dict[str, Any]) -> Document:
    """Reads a dictionary representing a document into a document.
    The dict may come from parsed yaml, json, toml, and whatnot.
    """
    commands = doc.read(doc_dict, "commands", doc.with_default(read_commands, []))
    return Document(commands)


def read_commands(doc_commands: Dict[str, Any]) -> List[Command]:
    """Reads a list of commands from a raw dict."""
    commands = []
    for name, doc_command in doc_commands.items():
        try:
            description = doc.read(doc_command, "description", doc.typed(str))
            validate_meta(MetaType.COMMAND, name, description)
            command = {
                "name": name,
                "description": description,
            }
            doc.read_to(doc_command, "options", doc.with_default(read_options, None), to=command)
            doc.read_to(
                doc_command,
                "default-permission",
                doc.typed(bool, optional=True),
                to=command,
                to_key="default_permission",
            )
            commands.append(command)
        except doc.ReadError as err:
            raise ContextualError(f"While reading command '{name}': {err}.")
    return commands


def read_options(doc_options: Dict[str, Any]) -> List[CommandOption]:
    """Reads a list of command options from a raw dict"""
    options = []
    for name, doc_option in doc_options.items():
        try:
            description = doc.read(doc_option, "description", doc.typed(str))
            validate_meta(MetaType.OPTION, name, description)
            kind = doc.read(doc_option, "type", doc.typed(str))
            option = {
                "name": name,
                "description": description,
                "type": CommandOptionType.from_str(kind).value,
            }
            doc.read_to(doc_option, "required", doc.typed(bool, optional=True), to=option)
            if "choices" in doc_option and isinstance(doc_option["choices"], list):
                choices = []
                for doc_choice in doc_option["choices"]:
                    if isinstance(doc_choice, str) or isinstance(doc_choice, int):
                        doc_choice = {"name": doc_choice}
                    if not isinstance(doc_choice, dict):
                        raise doc.ValueTypeError(f"Choice of unexpected type '{type(doc_choice).__name__}'")
                    choice_name = doc.read(doc_choice, "name", doc.typed(str))
                    validate_length("Choice name", choice_name)
                    choices.append({
                        "name":
                        choice_name,
                        "value":
                        doc.read(doc_choice, ["value", "name"], doc.typed(get_args(Union[str, int])))  # type: ignore
                    })
                option["choices"] = choices
            doc.read_to(doc_option, "options", doc.with_default(read_options, None), to=option)
            options.append(option)
        except doc.ReadError as err:
            raise ContextualError(f"option '{name}' — {err}.")
    return options


def validate_meta(kind: MetaType, name: str, description: str):
    """Validates meta fields, raise an exception if a validation fails."""
    if not NAME_PATTERN.match(name):
        raise ValidationError(f"Command name '{name}' must be alphanumeric and less than 32 chars long.")
    if description is None:
        raise ValidationError(f"Description is required for {kind.value} '{name}'.")
    validate_length("Description", description)


def validate_length(kind: str, value: str, min: int = 1, max: int = 100):
    """Validates length of a value."""
    if len(value) < min:
        raise ValidationError(f"{kind} '{value}' must be at least {min} chars long.")
    if len(value) > max:
        raise ValidationError(f"{kind} '{value}' must be strictly less than {max + 1} chars long.")
