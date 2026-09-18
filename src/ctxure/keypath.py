from typing import Any, NoReturn


class KeyPath:
    __slots__ = ("keys",)

    keys: tuple[str, ...]

    def __init__(self, *keys: str) -> None:
        if not keys:
            raise ValueError("KeyPath requires at least one key")
        for k in keys:
            if not isinstance(k, str):
                raise TypeError(f"KeyPath keys must be str, got {type(k).__name__}: {k!r}")
        # Store plain str so that, e.g., StrEnum members format as their value in error messages.
        object.__setattr__(self, "keys", tuple(str.__str__(k) for k in keys))

    def __setattr__(self, name: str, value: Any) -> NoReturn:
        raise AttributeError("KeyPath is immutable")

    def __delattr__(self, name: str) -> NoReturn:
        raise AttributeError("KeyPath is immutable")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, KeyPath):
            return NotImplemented
        return self.keys == other.keys

    def __hash__(self) -> int:
        return hash((KeyPath, self.keys))

    def __repr__(self) -> str:
        return f"KeyPath({', '.join(repr(k) for k in self.keys)})"

    def __reduce__(self) -> tuple[type["KeyPath"], tuple[str, ...]]:
        return (KeyPath, self.keys)
