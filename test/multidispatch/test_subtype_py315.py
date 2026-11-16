# pyright: reportArgumentType=false

from collections.abc import Collection, Mapping, MutableMapping
from typing import Any

from ctxure.multidispatch import Dispatch, is_subtype_covariant, is_subtype_invariant


def test_frozendict_covariant():
    assert is_subtype_covariant(frozendict[str, int], frozendict)
    assert is_subtype_covariant(frozendict[str, int], frozendict[str, float])
    assert is_subtype_covariant(frozendict[str, int], Mapping[str, int])
    assert is_subtype_covariant(frozendict[str, int], Mapping[str, float])
    assert is_subtype_covariant(frozendict[str, int], Collection[str])
    assert is_subtype_covariant(frozendict, Mapping[Any, Any])
    assert not is_subtype_covariant(frozendict[str, int], Mapping[int, int])
    assert not is_subtype_covariant(frozendict[str, int], MutableMapping[str, int])
    assert not is_subtype_covariant(frozendict[str, int], dict[str, int])
    assert not is_subtype_covariant(dict[str, int], frozendict[str, int])
    assert not is_subtype_covariant(frozendict, frozendict[str, int])


def test_frozendict_invariant():
    assert is_subtype_invariant(frozendict[str, int], frozendict)
    assert is_subtype_invariant(frozendict[str, int], frozendict[str, int])
    assert is_subtype_invariant(frozendict[str, int], Mapping[str, int])
    assert not is_subtype_invariant(frozendict[str, int], frozendict[str, float])
    assert not is_subtype_invariant(frozendict[str, int], Mapping[str, float])
    assert not is_subtype_invariant(frozendict[str, int], dict[str, int])


def test_dispatch_frozendict():
    dsp = Dispatch()

    @dsp
    def foo(x: dict) -> str:
        return "dict"

    @dsp
    def foo(x: frozendict) -> str:
        return "frozendict"

    assert foo({}) == "dict"
    assert foo(frozendict()) == "frozendict"
