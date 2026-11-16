from typing import TypedDict

import pytest

from ctxure import structure
from ctxure.error import ExtraFields, NoStructureHook

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
