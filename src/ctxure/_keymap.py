from collections.abc import Iterable, Mapping
from functools import reduce
from typing import Any

from ctxure._util import itemref_path
from ctxure.context import CtxImpl
from ctxure.error import ValidationError
from ctxure.keypath import KeyPath

Keymap = Mapping[str, str | KeyPath]

KeyTuple = tuple[str, ...]


def resolve_keys(ctx: CtxImpl, data: Any, names: Iterable[str], keymap: Keymap | None) -> list[KeyTuple]:
    if not keymap:
        return [(name,) for name in names]
    keys = []
    for name in names:
        value = keymap.get(name, name)
        if isinstance(value, str):
            keys.append((value,))
        elif isinstance(value, KeyPath):
            keys.append(value.keys)
        else:
            raise ValidationError(
                ctx, data, f"keymap value for {name!r} must be str or KeyPath, got {type(value).__name__}: {value!r}"
            )
    return keys


def needs_path_exe(keys: list[KeyTuple]) -> bool:
    # Duplicates also go to the path Exe: the fast Exe's extras check assumes distinct keys.
    return any(len(k) > 1 for k in keys) or len(set(keys)) < len(keys)


def format_keys(keys: KeyTuple) -> str:
    return "".join(f"[{k!r}]" for k in keys)


def keys_path(parent_path: str, keys: KeyTuple) -> str:
    return reduce(itemref_path, keys, parent_path)
