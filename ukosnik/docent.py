"""Docent, the guiding module.
Contains helper functions to read from a dict.

The functions in this module should most likely not be used externally.
"""

from inspect import signature
from types import FunctionType
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union


# Error
class ReadError(Exception):
    """Base error for when a given dict cannot be read into a document."""


class ValueTypeError(ReadError):
    """Raised when a value has an unexpected type."""


class MissingValueError(ReadError):
    """Raised when a required value is missing."""


# Functions
T = TypeVar("T")

# FIXME: typings are completely unreadable


def read(doc_dict: Dict[str, Any], keys: Union[str, List[str]], fn: Callable[[str, Any], T]) -> T:
    assert isinstance(fn, FunctionType), "fn must be a valid function"
    if isinstance(keys, str):
        keys = [keys]
    for key in keys:
        if key in doc_dict:
            return fn(key, doc_dict[key])
    return fn(keys[0] if len(keys) > 0 else None, None)


def read_to(
    doc_dict: Dict[str, Any],
    key: str,
    fn: Callable[[str, Any], Any],
    to: Dict[str, Any],
    to_key: Optional[str] = None,
):
    value = read(doc_dict, key, fn)
    if value is not None:
        to[to_key if to_key is not None else key] = value


def typed(kind: Type[T], optional: bool = False) -> Callable[[str, Any], T]:
    def __fn(key, value):
        if optional and value is None:
            return value
        if value is None:
            raise ValueTypeError(f"'{key}' is required yet missing.")
        if not isinstance(value, kind):
            raise ValueTypeError(f"Expected value from '{key}' to be of type '{kind.__name__}' but is it \
                        of type '{type(value).__name__}' instead.")
        return value

    return __fn  # type: ignore


def with_default(fn: Union[Callable[[str, Any], T], Callable[[Any], T]], default: T) -> Callable[[str, Any], T]:
    if len(signature(fn).parameters) == 1:
        return lambda _, value: fn(value) if value is not None else default  # type: ignore
    return lambda key, value: fn(key, value) if value is not None else default  # type: ignore
