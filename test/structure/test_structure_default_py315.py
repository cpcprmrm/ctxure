from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal, TypedDict

import pytest

from ctxure import structure
from ctxure.error import AmbiguousUnion, ExtraFields, NoStructureHook, ValidationError

# PEP 728 with the native `typing.TypedDict` (Python 3.15+), not `typing_extensions`.


def test_structure_native_typeddict_closed():
    class Foo(TypedDict, closed=True):
        a: int

    assert structure(Foo, {"a": 1}) == {"a": 1}

    with pytest.raises(ExtraFields) as e:
        structure(Foo, {"a": 1, "extra": 99})
    assert set(e.value.extra) == {"extra"}


def test_structure_native_typeddict_extra_items():
    class Foo(TypedDict, extra_items=int):
        a: str

    assert structure(Foo, {"a": "hi", "x": 1}) == {"a": "hi", "x": 1}

    with pytest.raises(NoStructureHook) as e:
        structure(Foo, {"a": "hi", "bad": "not-an-int"})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$.bad"


def test_structure_native_typeddict_default_drops_extras():
    class Foo(TypedDict):
        a: int

    assert structure(Foo, {"a": 1, "extra": 99}) == {"a": 1}


def test_structure_native_typeddict_inherited_closed():
    class Base(TypedDict, closed=True):
        a: int

    class Sub(Base):
        pass

    with pytest.raises(ExtraFields) as e:
        structure(Sub, {"a": 1, "extra": 99})
    assert set(e.value.extra) == {"extra"}


def test_structure_native_typeddict_generic_extra_items():
    class Bag[T](TypedDict, extra_items=T):
        name: str

    assert structure(Bag[int], {"name": "ok", "extra": 1}) == {"name": "ok", "extra": 1}

    with pytest.raises(NoStructureHook) as e:
        structure(Bag[int], {"name": "bad", "extra": "not-an-int"})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$.extra"


def test_structure_frozendict():
    result = structure(frozendict[str, int], {"a": 1, "b": 2})
    assert type(result) is frozendict
    assert result == frozendict(a=1, b=2)
    assert list(result) == ["a", "b"]

    assert structure(frozendict[str, int], {}) == frozendict()
    assert structure(frozendict[int, int], {"1": 10, 2: 20}) == frozendict({1: 10, 2: 20})
    assert structure(frozendict[str, list[int]], {"a": (1, 2)}) == frozendict(a=[1, 2])

    class Foo(Enum):
        A = "a"

    assert structure(frozendict[Foo, int], {"a": 1}) == frozendict({Foo.A: 1})
    assert structure(frozendict[Literal[1], int], {"1": 10}) == frozendict({1: 10})


def test_structure_frozendict_from_frozendict():
    result = structure(frozendict[str, int], frozendict(a=1))
    assert type(result) is frozendict
    assert result == frozendict(a=1)


def test_structure_bare_frozendict():
    data = {"a": [1, "x"], 1: None}
    result = structure(frozendict, data)
    assert type(result) is frozendict
    assert result == frozendict(data)
    assert structure(frozendict[Any, Any], data) == frozendict(data)


def test_structure_frozendict_errors():
    with pytest.raises(NoStructureHook) as e:
        structure(frozendict[str, int], {"a": "1"})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$['a']"
    assert e.value.ctx.unstructured_path == "$['a']"
    assert e.value.ctx.structured_key == "a"
    assert e.value.ctx.parent is not None
    assert e.value.ctx.parent.structured_type == frozendict[str, int]
    assert e.value.data == "1"

    with pytest.raises(ValidationError) as e:
        structure(frozendict[int, int], {"x": 1})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$[~?]"

    with pytest.raises(NoStructureHook) as e:
        structure(frozendict[str, int], [("a", 1)])
    assert e.value.ctx.structured_type == frozendict[str, int]
    assert e.value.ctx.structured_path == "$"


def test_structure_dict_from_frozendict():
    result = structure(dict[str, int], frozendict(a=1))
    assert type(result) is dict
    assert result == {"a": 1}
    assert structure(dict, frozendict(a=1)) == {"a": 1}


def test_structure_frozendict_nested():
    @dataclass
    class Foo:
        tags: frozendict[str, str]

    assert structure(Foo, {"tags": {"k": "v"}}) == Foo(frozendict(k="v"))
    assert structure(set[frozendict[str, int]], [{"a": 1}, {"a": 1}]) == {frozendict(a=1)}
    assert structure(list[frozendict[str, int]], [frozendict(a=1)]) == [frozendict(a=1)]


def test_structure_frozendict_is_not_dataclass_or_typeddict_source():
    @dataclass
    class Foo:
        a: int

    class Bar(TypedDict):
        a: int

    with pytest.raises(NoStructureHook):
        structure(Foo, frozendict(a=1))
    with pytest.raises(NoStructureHook):
        structure(Bar, frozendict(a=1))


def test_structure_frozendict_union():
    assert structure(frozendict[str, int] | None, {"a": 1}) == frozendict(a=1)
    assert structure(frozendict[str, int] | None, None) is None
    assert structure(frozendict[str, int] | list[int], frozendict(a=1)) == frozendict(a=1)

    with pytest.raises(AmbiguousUnion):
        structure(dict[str, int] | frozendict[str, int], {"a": 1})
    with pytest.raises(AmbiguousUnion):
        structure(dict[str, int] | frozendict[str, int], frozendict(a=1))


def test_structure_unhashable_frozendict_at_literal_union():
    # A frozendict holding a list passes isinstance(_, Hashable) but raises TypeError when hashed.
    data = frozendict(a=[1])
    assert structure(Literal["none"] | dict[str, list[int]], data) == {"a": [1]}
    assert structure(Literal["none"] | frozendict[str, list[int]], data) == data
    with pytest.raises(ValidationError) as e:
        structure(Literal["a", "b"], data)
    assert e.value.data is data
