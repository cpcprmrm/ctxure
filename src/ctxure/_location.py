import re
from typing import Any, Generic, Literal, TypeVar, get_args, get_origin

from typing_extensions import TypeForm

_T = TypeVar("_T")


class PathSeg: ...


class RootSeg(PathSeg, Generic[_T]): ...


class FieldSeg(PathSeg, Generic[_T]): ...


class ItemSeg(PathSeg, Generic[_T]): ...


class KeySeg(PathSeg, Generic[_T]): ...


class Identifier(Generic[_T]): ...


class LocationParseError(Exception):
    def __init__(self, message, pos: int | None = None):
        self.pos = pos
        super().__init__(message)


def get_field(t: type[FieldSeg]) -> str:
    return _strip(get_args(t)[0])


def format_field(name: str) -> str:
    if _identifier_pattern.fullmatch(name):
        return name
    return repr(name)


def get_key(t: type[ItemSeg] | type[KeySeg]) -> Any:
    return _strip(get_args(t)[0])


def _strip(arg: Any) -> Any:
    if arg is Any:
        return None
    while get_origin(arg) is not Literal:
        arg = get_args(arg)[0]
    return get_args(arg)[0]


_identifier_pattern = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:-+[A-Za-z0-9_]+)*")

_qualified_identifier_pattern = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*")

_int_pattern = re.compile(r"\d+")

_string_pattern = re.compile(
    r"""
    '(?P<sq>[^'\\]*(?:\\.[^'\\]*)*)'
    |
    "(?P<dq>[^"\\]*(?:\\.[^"\\]*)*)"
    """,
    re.VERBOSE,
)


def parse_path(expr: str) -> TypeForm[Any] | PathSeg | tuple[type[PathSeg], ...]:
    if len(expr) == 0:
        raise LocationParseError("Empty expression", 0)
    if expr.startswith("$"):
        return parse_rooted(expr)
    else:
        return parse_rootless(expr)


def _parse_key(expr: str, i: int) -> tuple[Any, int]:
    if expr[i : i + 1] == "?":
        return Any, i + 1
    if m := _string_pattern.match(expr, i):
        raw = m.group("sq") if m.group("sq") is not None else m.group("dq")
        value = bytes(raw, "utf-8").decode("unicode_escape")
        return Literal[value], m.end()
    if m := _int_pattern.match(expr, i):
        return Literal[int(m.group())], m.end()
    if m := _qualified_identifier_pattern.match(expr, i):
        return Identifier[Literal[m.group()]], m.end()
    raise LocationParseError(f"Expected int, str, or enum at {i}", i)


def _parse_field(expr: str, i: int) -> tuple[Any, int]:
    """Parse a field name after `.`: wildcard `?`, quoted string, or identifier (including kebab)."""
    if expr[i : i + 1] == "?":
        return Any, i + 1
    if m := _string_pattern.match(expr, i):
        raw = m.group("sq") if m.group("sq") is not None else m.group("dq")
        value = bytes(raw, "utf-8").decode("unicode_escape")
        return Identifier[Literal[value]], m.end()
    if m := _identifier_pattern.match(expr, i):
        return Identifier[Literal[m.group()]], m.end()
    raise LocationParseError(f"Invalid field at {i}", i)


def parse_rooted(expr: str) -> TypeForm[Any] | tuple[type[PathSeg], ...]:
    n = len(expr)
    segs = []

    segs.append(RootSeg)
    i = 1

    while i < n:
        if expr[i] == ".":
            i += 1
            if i >= n:
                raise LocationParseError(f"Expected field name after '.' at {i}", i)
            field, i = _parse_field(expr, i)
            if field is Any:
                segs.append(FieldSeg[Any])
            else:
                segs.append(FieldSeg[field])
            continue
        if expr[i] == "[":
            i += 1
            is_key_ref = False
            if i < n and expr[i] == "~":
                is_key_ref = True
                i += 1
            key, i = _parse_key(expr, i)
            if i >= n or expr[i] != "]":
                raise LocationParseError("Expected ']'", i)
            i += 1
            if is_key_ref:
                segs.append(KeySeg[key])
            else:
                segs.append(ItemSeg[key])
            continue
        raise LocationParseError(f"Unexpected character {expr[i]!r} at {i}", i)

    return tuple(segs)


def parse_rootless(expr: str) -> PathSeg | TypeForm[Any]:
    if expr == "?":
        return Any

    n = len(expr)

    # Item or Key: [...]
    if expr[0] == "[":
        i = 1
        is_key_ref = False
        if i < n and expr[i] == "~":
            is_key_ref = True
            i += 1
        key, i = _parse_key(expr, i)
        if i >= n or expr[i] != "]":
            raise LocationParseError("Expected ']'", i)
        i += 1
        if i != n:
            raise LocationParseError(f"Unexpected character {expr[i]!r} at {i}", i)
        if is_key_ref:
            return KeySeg[key]
        else:
            return ItemSeg[key]

    # Field: .foo, .?, ."foo bar", .'foo-bar'
    if expr[0] == ".":
        i = 1
        if i >= n:
            raise LocationParseError(f"Expected field name after '.' at {i}", i)
        field, i = _parse_field(expr, i)
        if i != n:
            raise LocationParseError(f"Unexpected character {expr[i]!r} at {i}", i)
        return FieldSeg[field]

    raise LocationParseError(f"Unexpected character {expr[0]!r} at 0", 0)


def location_to_str(loc: TypeForm[Any] | PathSeg | tuple[type[PathSeg], ...]) -> str:
    def strip_and_str(a: Any, i: int = 0):
        a = get_args(a)[i]
        if a is Any:
            return "?"
        if get_origin(a) is Identifier:
            return get_args(get_args(a)[0])[0]
        a = _strip(a)
        if isinstance(a, str):
            return f"'{a}'"
        else:
            return str(a)

    def field_str(seg: type[PathSeg]) -> str:
        a = get_args(seg)[0]
        if a is Any:
            return "?"
        name = get_args(get_args(a)[0])[0]
        return format_field(name)

    def seg_to_str(seg: type[PathSeg]) -> str:
        if seg == RootSeg:
            return "$"
        seg_orig = get_origin(seg)
        if seg_orig == FieldSeg:
            return f".{field_str(seg)}"
        if seg_orig == ItemSeg:
            return f"[{strip_and_str(seg)}]"
        if seg_orig == KeySeg:
            return f"[~{strip_and_str(seg)}]"
        raise ValueError(f"Unknown path segment type: {seg}")  # pragma: nocover

    if loc is Any:
        return "?"
    elif isinstance(loc, tuple):
        return "".join(seg_to_str(seg) for seg in loc)
    else:
        return seg_to_str(loc)  # type: ignore
