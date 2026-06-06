from dataclasses import dataclass
from typing import Literal, TypedDict

import pytest

from ctxure import structure
from ctxure.error import NoStructureHook

type _Tree = list[_Tree]

type _Int = int

type CycleA = CycleB  # type: ignore

type CycleB = CycleA

type _MaybeInt = _Int | None


@dataclass
class Foo:
    kind: Literal["foo"]
    a: str


class Bar(TypedDict):
    kind: Literal["bar"]
    b: int


def test_structure_recursive_alias_empty():
    assert structure(_Tree, []) == []


def test_structure_recursive_alias_nested():
    assert structure(_Tree, [[], [[]]]) == [[], [[]]]


def test_structure_recursive_alias_type_mismatch():
    with pytest.raises(NoStructureHook):
        structure(_Tree, [1])


def test_structure_union_of_aliases():
    assert structure(_Tree | _Int, 1) == 1
    assert structure(_Tree | _Int, [[]]) == [[]]


def test_structure_mutual_cyclic_alias_raises():
    with pytest.raises(TypeError, match="Cyclic"):
        structure(CycleA, None)


def test_structure_nested_unions_with_type_aliases():
    Tagged = Foo | Bar
    Mixed = Tagged | _MaybeInt

    assert structure(Mixed, {"kind": "foo", "a": "hello"}) == Foo("foo", "hello")
