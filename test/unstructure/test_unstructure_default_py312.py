import pytest

from ctxure import unstructure
from ctxure.error import NoUnstructureHook

type _Tree = list[_Tree]

type _Int = int


def test_unstructure_recursive_alias_empty():
    assert unstructure(_Tree, []) == []


def test_unstructure_recursive_alias_nested():
    assert unstructure(_Tree, [[], [[]]]) == [[], [[]]]


def test_unstructure_recursive_alias_type_mismatch():
    with pytest.raises(NoUnstructureHook):
        unstructure(_Tree, [1])


def test_unstructure_union_of_aliases():
    assert unstructure(_Tree | _Int, 1) == 1
    assert unstructure(_Tree | _Int, [[]]) == [[]]


type CycleA = CycleB  # type: ignore
type CycleB = CycleA


def test_unstructure_mutual_cyclic_alias_raises():
    with pytest.raises(TypeError, match="[Cc]yclic"):
        unstructure(CycleA, None)
