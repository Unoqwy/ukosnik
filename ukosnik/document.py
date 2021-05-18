"""Configuration document.
This module contains class definitions and functions to read from parsed file.
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, TypeVar, TypedDict, Union
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

    try:
        commands = doc.read(doc_dict, "commands", doc.with_default(read_commands, []))
    except doc.ReadError as err:
        raise ContextualError(f"While reading commands: {err}") from err
    return Document(commands)


def read_commands(data: Any) -> List[Command]:
    """Reads a list of commands from raw data."""
    def __fn(doc_command: Dict[str, Any]) -> Command:
        name = doc.read(doc_command, "name", doc.typed(str))
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
        return command  # type: ignore

    return __read_list_or_keyed("Command", data, __fn)


def read_options(data: Any) -> List[CommandOption]:
    """Reads a list of command options from raw data"""
    def __fn(doc_option: Dict[str, Any]) -> CommandOption:
        name = doc.read(doc_option, "name", doc.typed(str))
        description = doc.read(doc_option, "description", doc.typed(str))
        validate_meta(MetaType.OPTION, name, description)
        kind_key = doc.read(doc_option, "type", doc.typed((str, int)))  # type: ignore
        try:
            kind = CommandOptionType.from_str(kind_key) if isinstance(kind_key, str) else CommandOptionType(kind_key)
        except ValueError as err:
            raise InvalidOptionTypeError(f"{kind_key} is not a valid command option type.\
                    It must be between 1 and 9 (both inclusive).") from err
        option = {
            "name": name,
            "description": description,
            "type": kind.value,
        }
        doc.read_to(doc_option, "required", doc.typed(bool, optional=True), to=option)
        if "choices" in doc_option and isinstance(doc_option["choices"], list):
            choices = []
            for doc_choice in doc_option["choices"]:
                if isinstance(doc_choice, (str, int)):
                    doc_choice = {"name": doc_choice}
                if not isinstance(doc_choice, dict):
                    raise doc.ValueTypeError(f"Choice of unexpected type '{type(doc_choice).__name__}'")
                choice_name = doc.read(doc_choice, "name", doc.typed(str))
                validate_length("Choice name", choice_name)
                choices.append({
                    "name": choice_name,
                    "value": doc.read(doc_choice, ["value", "name"], doc.typed((str, int)))  # type: ignore
                })
            option["choices"] = choices
        doc.read_to(doc_option, "options", doc.with_default(read_options, None), to=option)
        return option  # type: ignore

    return __read_list_or_keyed("Option", data, __fn)


T = TypeVar("T")


def __read_list_or_keyed(kind: str, data: Any, fn: Callable[[Dict[str, Any]], T]) -> List[T]:
    """DRY function to read either a list or a dictionnary with value's name being the key."""
    if isinstance(data, dict):
        doc_values = []
        for name, doc_value in data.items():
            if not isinstance(doc_values, dict):
                raise doc.ValueTypeError(f"{kind} '{name}' is not an object.")
            if not "name" in doc_value:
                doc_value["name"] = name
            doc_values.append(doc_value)
    elif isinstance(data, list):
        doc_values = data
    else:
        raise doc.ValueTypeError(f"{kind}s must either be an array or an object with option names as keys.")

    options = []
    for doc_value in doc_values:
        try:
            options.append(fn(doc_value))
        except doc.ReadError as err:
            name = doc_value["name"] if "name" in doc_value else "unnamed"
            raise ContextualError(f"{kind.lower()} '{name}' — ({err})") from err
    return options


def validate_meta(kind: MetaType, name: str, description: str):
    """Validates meta fields, raise an exception if a validation fails."""
    if not NAME_PATTERN.match(name):
        raise ValidationError(f"Command name '{name}' must be alphanumeric and less than 32 chars long.")
    if description is None:
        raise ValidationError(f"Description is required for {kind.value} '{name}'.")
    validate_length("Description", description)


def validate_length(kind: str, value: str, _min: int = 1, _max: int = 100):
    """Validates length of a value."""
    if len(value) < _min:
        raise ValidationError(f"{kind} '{value}' must be at least {_min} chars long.")
    if len(value) > _max:
        raise ValidationError(f"{kind} '{value}' must be strictly less than {_max + 1} chars long.")
