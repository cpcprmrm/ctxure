from typing import TypedDict

import pytest

from ctxure import unstructure
from ctxure.error import NoUnstructureHook

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
