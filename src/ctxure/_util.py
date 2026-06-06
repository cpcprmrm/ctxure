from enum import Enum
from typing import Any, Literal, get_args, get_origin

from typing_extensions import TypeForm

from ctxure.context import CtxImpl
from ctxure._location import format_field
from ctxure._typeutil import literal_values_contain, normalize_type


def get_type_param(ctx: CtxImpl, index) -> Any:
    if type_params := get_args(ctx.structured_type):
        return type_params[index]
    else:
        return Any


def itemref_path(parent_path: str, k: Any | None, is_indexed: bool = True) -> str:
    return f"{parent_path}[{repr(k) if k is not None and is_indexed else '?'}]"


def key_repr(declared_key_type: Any, k: Any) -> str:
    declared_key_type = normalize_type(declared_key_type)
    while hasattr(declared_key_type, "__supertype__"):
        declared_key_type = normalize_type(declared_key_type.__supertype__)
    if declared_key_type is Any:
        declared_key_type = type(k)
    if get_origin(declared_key_type) is Literal:
        if literal_values_contain(get_args(declared_key_type), k):
            declared_key_type = type(k)
        else:
            return "?"
    if isinstance(k, bool):
        return "?"
    if declared_key_type is str or declared_key_type is int:
        if isinstance(k, int) and k < 0:
            return "?"
        return repr(k)
    elif isinstance(declared_key_type, type) and issubclass(declared_key_type, Enum):
        # Assume compatibility of the runtime type of `k` with the declared key type.
        return f"{type(k).__name__}.{k.name}"  # type: ignore
    else:
        return "?"


def typeddict_key_path(parent_path: str, key: Any) -> str:
    if isinstance(key, str):
        return f"{parent_path}.{format_field(key)}"
    return itemref_path(parent_path, key)


def format_typeform(t: TypeForm) -> str:
    if isinstance(t, type):
        return t.__qualname__
    origin = get_origin(t)
    args = get_args(t)
    if origin is not None and args:
        origin_str = origin.__qualname__ if isinstance(origin, type) else format_typeform(origin)
        return f"{origin_str}[{', '.join(format_typeform(a) for a in args)}]"
    return str(t).replace("typing.", "")
