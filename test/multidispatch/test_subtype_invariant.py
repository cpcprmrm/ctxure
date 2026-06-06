# pyright: reportArgumentType=false

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Generic, Literal, Never, NewType, TypeVar

from typing_extensions import TypeAliasType, TypedDict

from ctxure.multidispatch import DataClassBase, LiteralBase, NewTypeBase, TypedDictBase, UnionBase, is_subtype_invariant

T = TypeVar("T")
S = TypeVar("S")
K = TypeVar("K")
V = TypeVar("V")


@dataclass
class Box(Generic[T]):
    value: T


class Pair(Generic[K, V]): ...


@dataclass
class SpecialBox(Box[T], Generic[T]):
    label: str = ""


@dataclass
class IntBox(Box[int]):
    pass


@dataclass
class NestedBox(Box[list[T]], Generic[T]):
    pass


class MyTD(TypedDict):
    a: int


class SubTD(MyTD):
    b: str


class GenTD(TypedDict, Generic[T]):
    x: T


class IntTD(GenTD[int]):
    pass


UserId = NewType("UserId", int)
Email = NewType("Email", str)
NewIntBox = NewType("NewIntBox", Box[int])


def test_non_generic_types():
    assert is_subtype_invariant(int, int)
    assert is_subtype_invariant(bool, int)
    assert is_subtype_invariant(int, object)
    assert is_subtype_invariant(object, object)
    assert not is_subtype_invariant(int, str)
    assert not is_subtype_invariant(str, int)
    assert is_subtype_invariant(int, Any)


def test_any():
    assert is_subtype_invariant(Any, Any)
    assert not is_subtype_invariant(Any, int)
    assert not is_subtype_invariant(Any, object)


def test_parameterized_types():
    assert is_subtype_invariant(list[int], list[int])
    assert not is_subtype_invariant(list[int], list[str])
    assert is_subtype_invariant(list[int], list[Any])
    assert is_subtype_invariant(list[Any], list[Any])
    assert not is_subtype_invariant(list[Any], list[int])
    assert not is_subtype_invariant(list[int], list[object])
    assert is_subtype_invariant(dict[str, int], dict[str, int])
    assert not is_subtype_invariant(dict[str, int], dict[str, str])
    assert is_subtype_invariant(dict[str, int], dict[Any, Any])
    assert is_subtype_invariant(list[int], Sequence[int])
    assert not is_subtype_invariant(list[int], Sequence[str])
    assert is_subtype_invariant(list[int], Sequence[Any])
    assert not is_subtype_invariant(Sequence[int], list[int])
    assert is_subtype_invariant(dict[str, int], Mapping[str, int])
    assert is_subtype_invariant(list[int], Any)
    assert is_subtype_invariant(dict[str, int], Any)
    assert is_subtype_invariant(Box[int], Any)


def test_user_defined_generics():
    assert is_subtype_invariant(Box[int], Box[int])
    assert not is_subtype_invariant(Box[int], Box[str])
    assert is_subtype_invariant(Box[int], Box[Any])
    assert is_subtype_invariant(Never, Box[int])
    assert is_subtype_invariant(Box[Never], Box[int])
    assert not is_subtype_invariant(Box[int], Box[Never])
    assert is_subtype_invariant(SpecialBox[int], Box[int])
    assert not is_subtype_invariant(SpecialBox[int], Box[str])
    assert is_subtype_invariant(SpecialBox[int], Box[Any])
    assert is_subtype_invariant(IntBox, Box[int])
    assert not is_subtype_invariant(IntBox, Box[str])
    assert is_subtype_invariant(IntBox, Box[Any])
    assert is_subtype_invariant(Pair[str, int], Pair[str, int])
    assert not is_subtype_invariant(Pair[str, int], Pair[int, str])
    assert is_subtype_invariant(NestedBox[int], Box[list[int]])
    assert not is_subtype_invariant(NestedBox[int], Box[list[str]])


def test_bare_generics():
    assert is_subtype_invariant(list, list[Any])
    assert is_subtype_invariant(list[int], list)
    assert is_subtype_invariant(list[Never], list)
    assert not is_subtype_invariant(list, list[Never])
    assert is_subtype_invariant(Never, list)
    assert is_subtype_invariant(Box, Box[Any])
    assert is_subtype_invariant(Box[int], Box)
    assert is_subtype_invariant(list, Sequence)
    assert is_subtype_invariant(tuple[int], tuple)
    assert is_subtype_invariant(tuple[int, str], tuple)
    assert is_subtype_invariant(tuple[int, ...], tuple)
    assert is_subtype_invariant(tuple[()], tuple)
    assert not is_subtype_invariant(tuple, tuple[int])
    assert not is_subtype_invariant(tuple, tuple[int, ...])


def test_nested_parameterized_types():
    assert is_subtype_invariant(list[list[int]], list[list[int]])
    assert not is_subtype_invariant(list[list[int]], list[list[str]])
    assert is_subtype_invariant(list[list[int]], list[list[Any]])
    assert not is_subtype_invariant(list[list[Any]], list[list[int]])
    assert is_subtype_invariant(list[list[Never]], list[list[int]])
    assert not is_subtype_invariant(list[list[int]], list[list[Never]])
    assert is_subtype_invariant(list[list[int]], list[Any])


def test_bare_generics_in_nested_context():
    assert is_subtype_invariant(Pair[list[int], str], Pair[list, str])
    assert not is_subtype_invariant(Pair[list, str], Pair[list[int], str])
    assert is_subtype_invariant(Pair[list, str], Pair[list[Any], str])
    assert is_subtype_invariant(Pair[list[int], str], Pair[list[Any], str])
    assert not is_subtype_invariant(Pair[list[int], str], Pair[list[str], str])


def test_tuples():
    assert is_subtype_invariant(tuple[int, ...], tuple[int, ...])
    assert is_subtype_invariant(tuple[int, ...], tuple[Any, ...])
    assert is_subtype_invariant(tuple[int, int], tuple[int, ...])
    assert is_subtype_invariant(tuple[int, int], tuple[Any, ...])
    assert not is_subtype_invariant(tuple[int, ...], tuple[str, ...])
    assert not is_subtype_invariant(tuple[int, str], tuple[int, ...])
    assert is_subtype_invariant(tuple[int, str], tuple[int, str])
    assert not is_subtype_invariant(tuple[int, str], tuple[str, int])
    assert not is_subtype_invariant(tuple[int, ...], tuple[int, int])
    assert not is_subtype_invariant(tuple[int, str], tuple[int, str, float])
    assert not is_subtype_invariant(int, tuple[int, ...])
    assert not is_subtype_invariant(int, tuple[int, str])
    assert not is_subtype_invariant(tuple[int, ...], list[int])
    assert is_subtype_invariant(tuple[()], tuple[()])
    assert is_subtype_invariant(tuple[()], tuple[int, ...])
    assert is_subtype_invariant(tuple[()], tuple[Any, ...])
    assert not is_subtype_invariant(tuple[()], tuple[int, str])
    assert is_subtype_invariant(tuple[Never, ...], tuple[int, ...])
    assert is_subtype_invariant(tuple[Never, int], tuple[str, int])
    assert not is_subtype_invariant(tuple[Never, str], tuple[str, int])
    assert is_subtype_invariant(tuple, Sequence)
    assert is_subtype_invariant(tuple[()], Sequence[int])
    assert is_subtype_invariant(tuple[int, ...], Sequence[int])
    assert is_subtype_invariant(tuple[int, int], Sequence[int])
    assert not is_subtype_invariant(tuple[int, str], Sequence[object])
    assert is_subtype_invariant(tuple[str, Never], Sequence[str])


def test_tuples_with_compound_elements():
    assert is_subtype_invariant(tuple[int | str, ...], tuple[int | str, ...])
    assert is_subtype_invariant(tuple[int | str, ...], tuple[str | int, ...])
    assert is_subtype_invariant(tuple[int | str, float], tuple[int | str, float])
    assert not is_subtype_invariant(tuple[int, ...], tuple[int | str, ...])
    assert not is_subtype_invariant(tuple[int | str, ...], tuple[int, ...])
    assert is_subtype_invariant(tuple[Literal[1], str], tuple[Literal[1], str])
    assert is_subtype_invariant(tuple[Literal[1, 2], ...], tuple[Literal[2, 1], ...])
    assert not is_subtype_invariant(tuple[Literal[1], ...], tuple[Literal[1, 2], ...])
    assert not is_subtype_invariant(tuple[Literal[1], ...], tuple[int, ...])
    assert is_subtype_invariant(tuple[UserId, str], tuple[UserId, str])
    assert not is_subtype_invariant(tuple[UserId, ...], tuple[int, ...])
    assert not is_subtype_invariant(tuple[int, ...], tuple[UserId, ...])
    assert is_subtype_invariant(tuple[list[int], ...], tuple[list, ...])
    assert is_subtype_invariant(tuple[list[int], str], tuple[list, str])
    assert not is_subtype_invariant(tuple[list, ...], tuple[list[int], ...])
    assert is_subtype_invariant(tuple[list[int], ...], tuple[list[Any], ...])
    assert not is_subtype_invariant(tuple[int, str], Sequence[int | str])


def test_unions():
    assert is_subtype_invariant(int, int | str)
    assert is_subtype_invariant(bool, int | str)
    assert is_subtype_invariant(str, int | str)
    assert not is_subtype_invariant(float, int | str)
    assert is_subtype_invariant(list[int], list[int] | str)
    assert is_subtype_invariant(list[int], list[Any] | str)
    assert not is_subtype_invariant(list[int], list[str] | str)
    assert is_subtype_invariant(int | str, object)
    assert is_subtype_invariant(bool | int, int)
    assert not is_subtype_invariant(int | str, int)
    assert not is_subtype_invariant(int | float, str)
    assert is_subtype_invariant(list[int] | list[str], list[Any])
    assert not is_subtype_invariant(list[int] | list[str], list[int])
    assert is_subtype_invariant(int | str, int | str)
    assert is_subtype_invariant(int | str, str | int)
    assert is_subtype_invariant(int | str, int | str | float)
    assert not is_subtype_invariant(int | str | float, int | str)
    assert is_subtype_invariant(bool | str, int | str)
    assert not is_subtype_invariant(int | str, bool | str)
    assert is_subtype_invariant(Never, int | str)
    assert not is_subtype_invariant(int | str, Never)


def test_dataclass():
    assert is_subtype_invariant(Box, DataClassBase)
    assert is_subtype_invariant(IntBox, DataClassBase)
    assert not is_subtype_invariant(int, DataClassBase)
    assert not is_subtype_invariant(DataClassBase, DataClassBase)
    assert not is_subtype_invariant(Box | int, DataClassBase)
    assert not is_subtype_invariant(Box | IntBox, DataClassBase)


def test_typeddict():
    assert is_subtype_invariant(MyTD, MyTD)
    assert is_subtype_invariant(SubTD, MyTD)
    assert not is_subtype_invariant(MyTD, SubTD)
    assert is_subtype_invariant(MyTD, TypedDictBase)
    assert is_subtype_invariant(SubTD, TypedDictBase)
    assert not is_subtype_invariant(dict, TypedDictBase)
    assert not is_subtype_invariant(TypedDictBase, TypedDictBase)
    assert not is_subtype_invariant(MyTD, dict)
    assert not is_subtype_invariant(GenTD[int], dict)


def test_typeddict_generic():
    assert is_subtype_invariant(GenTD[int], GenTD[int])
    assert is_subtype_invariant(GenTD[int], GenTD[Any])
    assert not is_subtype_invariant(GenTD[int], GenTD[str])
    assert not is_subtype_invariant(GenTD[int], GenTD[object])
    assert is_subtype_invariant(IntTD, GenTD[int])
    assert not is_subtype_invariant(IntTD, GenTD[str])
    assert is_subtype_invariant(IntTD, GenTD[Any])
    assert is_subtype_invariant(IntTD, TypedDictBase)
    assert is_subtype_invariant(GenTD, GenTD[Any])
    assert is_subtype_invariant(GenTD[int], GenTD)


def test_unions_in_nested_context():
    assert is_subtype_invariant(list[int | str], list[int | str])
    assert is_subtype_invariant(list[int | str], list[str | int])
    assert not is_subtype_invariant(list[int], list[str | int])
    assert not is_subtype_invariant(list[int | str], list[int | str | None])
    assert not is_subtype_invariant(list[int | str], list[UnionBase])


def test_unions_vs_virtual_bases():
    assert is_subtype_invariant(Box[int] | Box[str], UnionBase)
    assert not is_subtype_invariant(Literal[1] | Literal[2], LiteralBase)
    assert not is_subtype_invariant(UserId | Email, NewTypeBase)
    assert not is_subtype_invariant(Box[int] | Box[str], DataClassBase)


def test_literals_in_nested_context():
    assert is_subtype_invariant(list[Literal[1, 2]], list[Literal[1, 2]])
    assert is_subtype_invariant(list[Literal[1, 2]], list[Literal[2, 1]])
    assert not is_subtype_invariant(list[Literal[1, 2]], list[Literal[1, 2, 3]])
    assert not is_subtype_invariant(list[Literal[1, 2, 3]], list[Literal[1, 2]])


def test_literals():
    assert is_subtype_invariant(Literal[1], Literal[1])
    assert is_subtype_invariant(Literal[1], Literal[1, 2])
    assert is_subtype_invariant(Literal[1, 2], Literal[2, 1])
    assert not is_subtype_invariant(Literal[1, 2, 3], Literal[1, 2])
    assert is_subtype_invariant(Literal[1], int)
    assert is_subtype_invariant(Literal[1, 2], int)
    assert is_subtype_invariant(Literal["a"], str)
    assert not is_subtype_invariant(Literal[1], str)
    assert is_subtype_invariant(Literal[True], bool)
    assert is_subtype_invariant(Literal[True], int)
    assert not is_subtype_invariant(int, Literal[1])
    assert is_subtype_invariant(Literal[1], int | str)
    assert is_subtype_invariant(Literal[1], Any)
    assert is_subtype_invariant(Literal[1], object)
    assert not is_subtype_invariant(Literal[1], Literal[True])
    assert not is_subtype_invariant(Literal[True], Literal[1])
    assert not is_subtype_invariant(Literal[True], Literal[1, 2])
    assert is_subtype_invariant(Literal[None], Literal[None])
    assert is_subtype_invariant(Literal[None], Literal[None, 1])
    assert is_subtype_invariant(Literal[None], type(None))
    assert is_subtype_invariant(Literal[None], object)
    assert not is_subtype_invariant(Literal[None], int)
    assert not is_subtype_invariant(Literal[1], Box[int])
    assert not is_subtype_invariant(Box[int], Literal[1])
    assert not is_subtype_invariant(Literal["a"], MyTD)
    assert not is_subtype_invariant(MyTD, Literal["a"])
    assert is_subtype_invariant(Literal["a"], str | int)
    assert not is_subtype_invariant(str | int, Literal["a"])
    assert not is_subtype_invariant(Box[Literal[1]], Box[Literal[True]])
    assert not is_subtype_invariant(Box[Literal[True]], Box[Literal[1]])


def test_union_of_literals():
    assert is_subtype_invariant(Literal[1, 2], Literal[1] | Literal[2])
    assert is_subtype_invariant(Literal[1] | Literal[2], Literal[1, 2])
    assert is_subtype_invariant(Literal[1], Literal[1] | Literal[2])
    assert not is_subtype_invariant(Literal[1] | Literal[2], Literal[1])
    assert is_subtype_invariant(Literal[1], Literal[1, 2])
    assert not is_subtype_invariant(Literal[1, 2], Literal[1])
    assert is_subtype_invariant(Literal[1] | Literal[2], Literal[1, 2, 3])
    assert is_subtype_invariant(Literal[1, 2], Literal[1] | Literal[2] | Literal[3])
    assert not is_subtype_invariant(Literal[1] | Literal[2], Literal[2] | Literal[3])
    assert is_subtype_invariant(Literal[1, 2] | int, Literal[2] | int | Literal[1])
    assert is_subtype_invariant(Literal[2] | int | Literal[1], Literal[1, 2] | int)


def test_literalbase():
    assert is_subtype_invariant(Literal[1, 2], LiteralBase)
    assert is_subtype_invariant(Literal["a"], LiteralBase)
    assert not is_subtype_invariant(int, LiteralBase)
    assert not is_subtype_invariant(LiteralBase, Literal[1, 2])


def test_nested_and_cross_cutting():
    assert not is_subtype_invariant(list[UserId], list[int])
    assert not is_subtype_invariant(list[list[UserId]], list[list[int]])
    assert not is_subtype_invariant(list[NewIntBox], list[Box[int]])
    assert not is_subtype_invariant(list[list[NewIntBox]], list[list[Box[int]]])
    assert not is_subtype_invariant(list[NewIntBox], list[Box])
    assert not is_subtype_invariant(list[list[NewIntBox]], list[list[Box]])


def test_numeric_tower():
    assert is_subtype_invariant(bool, float)
    assert is_subtype_invariant(bool, complex)
    assert is_subtype_invariant(int, float)
    assert is_subtype_invariant(int, complex)
    assert is_subtype_invariant(float, complex)
    assert not is_subtype_invariant(float, bool)
    assert not is_subtype_invariant(float, int)
    assert not is_subtype_invariant(complex, bool)
    assert not is_subtype_invariant(complex, int)
    assert not is_subtype_invariant(complex, float)


def test_never():
    assert is_subtype_invariant(Never, Never)
    assert is_subtype_invariant(Never, int)
    assert is_subtype_invariant(Never, Any)
    assert not is_subtype_invariant(int, Never)
    assert not is_subtype_invariant(Any, Never)
    assert not is_subtype_invariant(list, Never)


AliasInt = TypeAliasType("AliasInt", int)


def test_type_alias_transparent():
    assert is_subtype_invariant(AliasInt, int)
    assert is_subtype_invariant(int, AliasInt)
    assert is_subtype_invariant(AliasInt, AliasInt)
    assert not is_subtype_invariant(AliasInt, str)


T = TypeVar("T")
AliasList = TypeAliasType("AliasList", list[T], type_params=(T,))


def test_type_alias_parameterized_invariant():
    assert is_subtype_invariant(AliasList[int], list[int])
    assert is_subtype_invariant(list[int], AliasList[int])
    assert not is_subtype_invariant(AliasList[int], list[str])
    assert is_subtype_invariant(list[AliasList[int]], list[list[int]])


AliasA = TypeAliasType("AliasA", int)
AliasB = TypeAliasType("AliasB", AliasA)


def test_type_alias_transitive_chain_invariant():
    assert is_subtype_invariant(AliasB, int)
    assert is_subtype_invariant(int, AliasB)
