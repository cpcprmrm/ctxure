from typing import Any

from ctxure._location import parse_path


def loc(s: str) -> Any:
    pathsegs = parse_path(s)
    if pathsegs is Any:
        return Any
    if isinstance(pathsegs, tuple):
        return tuple[tuple[*pathsegs[:-1]], pathsegs[-1]]
    return tuple[Any, pathsegs]
