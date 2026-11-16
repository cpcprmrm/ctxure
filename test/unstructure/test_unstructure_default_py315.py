from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal, TypedDict

import pytest

from ctxure import unstructure
from ctxure.error import NoUnstructureHook, ValidationError

# PEP 728 with the native `typing.TypedDict` (Python 3.15+), not `typing_extensions`.


def test_unstructure_native_typeddict_closed():
    class Foo(TypedDict, closed=True):
        a: int

    assert unstructure(Foo, {"a": 1, "extra": 99}) == {"a": 1}


def test_unstructure_native_typeddict_extra_items():
    class Foo(TypedDict, extra_items=int):
        a: str

    assert unstructure(Foo, {"a": "hi", "x": 1}) == {"a": "hi", "x": 1}

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(Foo, {"a": "hi", "bad": "not-an-int"})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$.bad"


def test_unstructure_native_typeddict_generic_extra_items():
    class Bag[T](TypedDict, extra_items=T):
        name: str

    assert unstructure(Bag[int], {"name": "ok", "extra": 1}) == {"name": "ok", "extra": 1}


def test_unstructure_frozendict():
    result = unstructure(frozendict[str, int], frozendict(a=1, b=2))
    assert type(result) is dict
    assert result == {"a": 1, "b": 2}
    assert list(result) == ["a", "b"]

    assert unstructure(frozendict[int, str], frozendict({1: "x"})) == {"1": "x"}
    assert unstructure(frozendict[str, list[int]], frozendict(a=[1, 2])) == {"a": [1, 2]}

    class Foo(Enum):
        A = "a"

    assert unstructure(frozendict[Foo, Foo], frozendict({Foo.A: Foo.A})) == {"a": "a"}


def test_unstructure_bare_frozendict():
    assert unstructure(frozendict, frozendict({"a": (1, 2)})) == {"a": [1, 2]}


def test_unstructure_frozendict_errors():
    with pytest.raises(ValidationError) as e:
        unstructure(frozendict[tuple[int], int], frozendict({(1,): 1}))
    assert e.value.ctx.structured_path == "$[~?]"

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(frozendict[str, int], frozendict(a="x"))
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$['a']"
    assert e.value.ctx.structured_key == "a"

    # The declared type is respected: a frozendict value declared as dict is not supported.
    with pytest.raises(NoUnstructureHook):
        unstructure(dict[str, int], frozendict(a=1))
    with pytest.raises(NoUnstructureHook):
        unstructure(frozendict[str, int], {"a": 1})


def test_unstructure_any_frozendict():
    result = unstructure(Any, frozendict(a=frozendict(b=(1,))))
    assert type(result) is dict
    assert result == {"a": {"b": [1]}}
    assert type(result["a"]) is dict
    assert unstructure(list, [frozendict(a=1)]) == [{"a": 1}]

    with pytest.raises(ValidationError):
        unstructure(Any, frozendict({(1,): 1}))


def test_unstructure_frozendict_nested():
    @dataclass
    class Foo:
        tags: frozendict[str, str]

    assert unstructure(Foo, Foo(frozendict(k="v"))) == {"tags": {"k": "v"}}


def test_unstructure_frozendict_union():
    fd = frozendict(a=1)
    assert unstructure(dict[str, int] | frozendict[str, int], fd) == {"a": 1}
    assert unstructure(dict[str, int] | frozendict[str, int], {"a": 1}) == {"a": 1}
    assert unstructure(frozendict[str, int] | None, None) is None


def test_unstructure_unhashable_frozendict_at_literal_union():
    # A frozendict holding a list passes isinstance(_, Hashable) but raises TypeError when hashed.
    assert unstructure(Literal["none"] | frozendict[str, list[int]], frozendict(a=[1])) == {"a": [1]}
