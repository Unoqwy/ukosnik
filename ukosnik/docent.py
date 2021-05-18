"""Docent, the guiding module.
Contains helper functions to read from a dict.

The functions in this module should most likely not be used externally.
"""

from inspect import signature
from types import FunctionType
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, TypeVar, Union, cast


# Errors
class ReadError(Exception):
    """Base error for when a given dict cannot be read into a document."""


class ValueTypeError(ReadError):
    """Raised when a value has an unexpected type."""


class MissingValueError(ReadError):
    """Raised when a required value is missing."""


# Generics and type aliases
T = TypeVar("T")
DocDict = Dict[str, Any]
ReadFn = Callable[[Optional[str], Any], T]  # closure taking key, value
SimpleFn = Callable[[Any], T]  # closure taking only value


# Read
def read(doc_dict: DocDict,
         keys: Union[str, List[str]],
         fn: ReadFn[T],
         to: Optional[DocDict] = None,
         to_key: Optional[str] = None) -> T:
    assert isinstance(fn, FunctionType), "fn must be a valid function"
    if isinstance(keys, str):
        keys = [keys]

    key, value = __read(doc_dict, keys, fn)
    if to is not None:
        to_key = to_key if to_key is not None else key
        if to_key is not None and value is not None:
            to[to_key] = value
    return value


def __read(doc_dict: DocDict, keys: List[str], fn: ReadFn[T]) -> Tuple[Optional[str], T]:
    for key in keys:
        if key in doc_dict:
            return key, fn(key, doc_dict[key])
    key = keys[0] if len(keys) > 0 else None
    return key, fn(key, None)


def with_default(parent: Union[ReadFn[T], SimpleFn[T]], default: T) -> ReadFn[T]:
    if len(signature(parent).parameters) == 1:
        fn = lambda _, value: parent(value)  # type: ignore
    else:
        fn = cast(ReadFn[T], parent)
    return lambda key, value: fn(key, value) if value is not None else default


def typed(type_hint: Type, optional: bool = False) -> ReadFn[Any]:
    def __fn(key: Optional[str], value: Any) -> Any:
        if optional and value is None:
            return value
        if value is None:
            raise ValueTypeError(f"'{key}' is required yet missing.")

        args = type_hint.__args__ if hasattr(type_hint, "__args__") else type_hint
        if not isinstance(value, args):
            raise ValueTypeError(" ".join([
                f"Expected value from '{key}' to be of type '{type_hint.__name__}'",
                f"but is it of type '{type(value).__name__}' instead."
            ]))
        return value

    return __fn
