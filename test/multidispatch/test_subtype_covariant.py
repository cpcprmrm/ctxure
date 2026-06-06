# pyright: reportArgumentType=false

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Generic, Literal, Never, NewType, TypeVar

from typing_extensions import TypeAliasType, TypedDict

from ctxure.multidispatch import DataClassBase, LiteralBase, NewTypeBase, TypedDictBase, UnionBase, is_subtype_covariant

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
Flag = NewType("Flag", bool)
Email = NewType("Email", str)
NewIntBox = NewType("NewIntBox", Box[int])


def test_non_generic_types():
    assert is_subtype_covariant(int, int)
    assert is_subtype_covariant(bool, int)
    assert is_subtype_covariant(int, object)
    assert not is_subtype_covariant(int, str)
    assert not is_subtype_covariant(str, int)
    assert is_subtype_covariant(int, Any)


def test_any():
    assert is_subtype_covariant(Any, Any)
    assert not is_subtype_covariant(Any, object)
    assert not is_subtype_covariant(Any, int)
    assert not is_subtype_covariant(Any, str)


def test_parameterized_types():
    assert is_subtype_covariant(list[int], list[int])
    assert is_subtype_covariant(list[int], list[object])
    assert not is_subtype_covariant(list[int], list[str])
    assert is_subtype_covariant(list[int], list[Any])
    assert is_subtype_covariant(list[Any], list[Any])
    assert is_subtype_covariant(list[list[int]], list[Any])
    assert not is_subtype_covariant(list[Any], list[int])
    assert not is_subtype_covariant(list[Any], list[object])
    assert is_subtype_covariant(dict[str, int], dict[str, int])
    assert is_subtype_covariant(dict[str, int], dict[str, object])
    assert is_subtype_covariant(dict[str, int], dict[object, object])
    assert not is_subtype_covariant(dict[str, int], dict[int, int])
    assert is_subtype_covariant(list[int], Sequence[int])
    assert is_subtype_covariant(list[int], Sequence[object])
    assert is_subtype_covariant(list[int], Sequence[Any])
    assert not is_subtype_covariant(list[int], Sequence[str])
    assert not is_subtype_covariant(Sequence[int], list[int])
    assert is_subtype_covariant(dict[str, int], Mapping[str, int])
    assert is_subtype_covariant(dict[str, int], Mapping[object, object])
    assert is_subtype_covariant(list[int], Any)
    assert is_subtype_covariant(dict[str, int], Any)


def test_user_defined_generics():
    assert is_subtype_covariant(Box[int], Box[int])
    assert is_subtype_covariant(Box[int], Box[object])
    assert not is_subtype_covariant(Box[int], Box[str])
    assert is_subtype_covariant(Box[Never], Box[int])
    assert is_subtype_covariant(Box[int], Box[Any])
    assert is_subtype_covariant(Never, Box[int])
    assert not is_subtype_covariant(Box[int], Box[Never])
    assert is_subtype_covariant(SpecialBox[int], Box[int])
    assert is_subtype_covariant(SpecialBox[int], Box[object])
    assert not is_subtype_covariant(SpecialBox[int], Box[str])
    assert is_subtype_covariant(IntBox, Box[int])
    assert is_subtype_covariant(IntBox, Box[object])
    assert not is_subtype_covariant(IntBox, Box[str])
    assert is_subtype_covariant(Pair[str, int], Pair[str, int])
    assert is_subtype_covariant(Pair[str, int], Pair[str, object])
    assert is_subtype_covariant(Pair[str, int], Pair[object, object])
    assert is_subtype_covariant(NestedBox[int], Box[list[int]])
    assert is_subtype_covariant(NestedBox[int], Box[list[object]])
    assert is_subtype_covariant(NestedBox[int], Box[list[Any]])
    assert not is_subtype_covariant(NestedBox[int], Box[list[str]])


def test_bare_generics():
    assert is_subtype_covariant(list, list[Any])
    assert is_subtype_covariant(list[int], list)
    assert is_subtype_covariant(list[Never], list)
    assert not is_subtype_covariant(list, list[Never])
    assert is_subtype_covariant(Never, list)
    assert is_subtype_covariant(Box, Box[Any])
    assert is_subtype_covariant(Box[int], Box)
    assert is_subtype_covariant(list, Sequence)
    assert is_subtype_covariant(tuple[int], tuple)
    assert is_subtype_covariant(tuple[int, str], tuple)
    assert is_subtype_covariant(tuple[int, ...], tuple)
    assert is_subtype_covariant(tuple[()], tuple)
    assert not is_subtype_covariant(tuple, tuple[int])
    assert not is_subtype_covariant(tuple, tuple[int, ...])


def test_bare_generics_in_nested_context():
    assert is_subtype_covariant(Pair[list[int], str], Pair[list, str])
    assert not is_subtype_covariant(Pair[list, str], Pair[list[int], str])
    assert is_subtype_covariant(Pair[list, str], Pair[list[Any], str])
    assert is_subtype_covariant(Pair[list[int], str], Pair[list[Any], str])
    assert not is_subtype_covariant(Pair[list[int], str], Pair[list[str], str])


def test_tuples():
    assert is_subtype_covariant(tuple[int, ...], tuple[int, ...])
    assert is_subtype_covariant(tuple[int, ...], tuple[object, ...])
    assert not is_subtype_covariant(tuple[int, ...], tuple[str, ...])
    assert is_subtype_covariant(tuple[int, str], tuple[object, ...])
    assert is_subtype_covariant(tuple[int, bool], tuple[int, ...])
    assert not is_subtype_covariant(tuple[int, str], tuple[int, ...])
    assert not is_subtype_covariant(tuple[int, ...], tuple[int, int])
    assert is_subtype_covariant(tuple[int, str], tuple[int, str])
    assert is_subtype_covariant(tuple[int, str], tuple[object, object])
    assert not is_subtype_covariant(tuple[int, str], tuple[int, str, float])
    assert is_subtype_covariant(tuple[int, str], tuple[Any, ...])
    assert not is_subtype_covariant(int, tuple[int, ...])
    assert not is_subtype_covariant(tuple[int, ...], list[int])
    assert is_subtype_covariant(tuple[()], tuple[()])
    assert is_subtype_covariant(tuple[()], tuple[int, ...])
    assert is_subtype_covariant(tuple[()], tuple[Any, ...])
    assert not is_subtype_covariant(tuple[()], tuple[int, str])
    assert is_subtype_covariant(tuple[Never, ...], tuple[int, ...])
    assert is_subtype_covariant(tuple[Never, int], tuple[str, int])
    assert not is_subtype_covariant(tuple[Never, str], tuple[str, int])
    assert is_subtype_covariant(tuple, Sequence)
    assert is_subtype_covariant(tuple[()], Sequence[int])
    assert is_subtype_covariant(tuple[int, ...], Sequence[object])
    assert is_subtype_covariant(tuple[int, str], Sequence[object])
    assert is_subtype_covariant(tuple[str, Never], Sequence[str])


def test_tuples_with_compound_elements():
    assert is_subtype_covariant(tuple[int, str], tuple[int | str, int | str])
    assert is_subtype_covariant(tuple[int, ...], tuple[int | str, ...])
    assert is_subtype_covariant(tuple[int | str, ...], tuple[int | str | None, ...])
    assert not is_subtype_covariant(tuple[int | str, ...], tuple[int, ...])
    assert is_subtype_covariant(tuple[Literal[1], str], tuple[int, str])
    assert is_subtype_covariant(tuple[Literal[1], Literal["a"]], tuple[int, str])
    assert is_subtype_covariant(tuple[Literal[1, 2], ...], tuple[int, ...])
    assert is_subtype_covariant(tuple[Literal[1], ...], tuple[int | str, ...])
    assert not is_subtype_covariant(tuple[Literal[1, 2], ...], tuple[str, ...])
    assert is_subtype_covariant(tuple[Literal[1], Literal[2]], tuple[Literal[1, 2], ...])
    assert is_subtype_covariant(tuple[UserId, str], tuple[int, str])
    assert not is_subtype_covariant(tuple[int, str], tuple[UserId, str])
    assert is_subtype_covariant(tuple[UserId, ...], tuple[int, ...])
    assert is_subtype_covariant(tuple[list[int], ...], tuple[list, ...])
    assert is_subtype_covariant(tuple[list[int], str], tuple[list, str])
    assert not is_subtype_covariant(tuple[list, ...], tuple[list[int], ...])
    assert is_subtype_covariant(tuple[list[int], ...], tuple[list[Any], ...])
    assert is_subtype_covariant(tuple[int, str], Sequence[int | str])


def test_literals():
    assert is_subtype_covariant(Literal[1], Literal[1])
    assert is_subtype_covariant(Literal[1], Literal[1, 2])
    assert is_subtype_covariant(Literal[1, 2], Literal[1, 2, 3])
    assert not is_subtype_covariant(Literal[1, 2, 3], Literal[1, 2])
    assert is_subtype_covariant(Literal[1, 2], Literal[2, 1])
    assert is_subtype_covariant(Literal[1], int)
    assert is_subtype_covariant(Literal["a"], str)
    assert not is_subtype_covariant(Literal[1], str)
    assert is_subtype_covariant(Literal[True], bool)
    assert is_subtype_covariant(Literal[True], int)
    assert not is_subtype_covariant(int, Literal[1])
    assert not is_subtype_covariant(Literal[1], Literal[True])
    assert not is_subtype_covariant(Literal[True], Literal[1])
    assert not is_subtype_covariant(Literal[True], Literal[1, 2])
    assert is_subtype_covariant(Literal[1, True], Literal[True, 1])
    assert is_subtype_covariant(Literal[None], Literal[None])
    assert is_subtype_covariant(Literal[None], Literal[None, 1])
    assert is_subtype_covariant(Literal[None], type(None))
    assert is_subtype_covariant(Literal[None], object)
    assert not is_subtype_covariant(Literal[None], int)
    assert not is_subtype_covariant(type(None), Literal[None])

    assert not is_subtype_covariant(Literal[1], Box[int])
    assert not is_subtype_covariant(Box[int], Literal[1])
    assert not is_subtype_covariant(Literal[1], Box[Any])
    assert not is_subtype_covariant(Box[Any], Literal[1])
    assert not is_subtype_covariant(Literal["a"], UserId)
    assert not is_subtype_covariant(UserId, Literal["a"])
    assert not is_subtype_covariant(Literal["a"], MyTD)
    assert not is_subtype_covariant(MyTD, Literal["a"])
    assert is_subtype_covariant(Literal["a"], str | int)
    assert not is_subtype_covariant(str | int, Literal["a"])
    assert not is_subtype_covariant(Box[Literal[1]], Box[Literal[True]])
    assert not is_subtype_covariant(Box[Literal[True]], Box[Literal[1]])


def test_newtypes():
    assert is_subtype_covariant(UserId, UserId)
    assert is_subtype_covariant(UserId, int)
    assert is_subtype_covariant(UserId, object)
    assert not is_subtype_covariant(int, UserId)
    assert not is_subtype_covariant(UserId, str)
    assert is_subtype_covariant(Email, str)
    assert not is_subtype_covariant(Email, UserId)
    assert not is_subtype_covariant(Flag, UserId)
    assert is_subtype_covariant(NewIntBox, Box[int])
    assert not is_subtype_covariant(Box[int], NewIntBox)
    assert not is_subtype_covariant(NewIntBox, Box[str])
    assert is_subtype_covariant(NewIntBox, Box[Any])
    assert is_subtype_covariant(NewIntBox, Box)
    assert not is_subtype_covariant(UserId, Box[int])
    assert not is_subtype_covariant(Box[int], UserId)
    assert not is_subtype_covariant(UserId, Box[Any])
    assert not is_subtype_covariant(Box[Any], UserId)
    assert not is_subtype_covariant(Literal[1, 2], UserId)
    assert not is_subtype_covariant(UserId, Literal[1, 2])
    assert not is_subtype_covariant(UserId, MyTD)
    assert not is_subtype_covariant(MyTD, UserId)
    assert is_subtype_covariant(UserId, UserId | Box)
    assert not is_subtype_covariant(UserId | Box, UserId)
    assert is_subtype_covariant(UserId, str | int)
    assert not is_subtype_covariant(str | int, UserId)


def test_unions():
    assert is_subtype_covariant(int, int | str)
    assert is_subtype_covariant(str, int | str)
    assert not is_subtype_covariant(float, int | str)
    assert is_subtype_covariant(int | str, int | str)
    assert is_subtype_covariant(int | str, str | int)
    assert is_subtype_covariant(int | str, int | str | float)
    assert not is_subtype_covariant(int | str | float, int | str)
    assert is_subtype_covariant(int | str, object)
    assert is_subtype_covariant(bool | int, int)
    assert is_subtype_covariant(list[int], list[int] | str)
    assert is_subtype_covariant(list[int] | str, Sequence[int] | str)
    assert is_subtype_covariant(list[int] | str, list[object] | object)
    assert is_subtype_covariant(Literal[1], int | str)
    assert is_subtype_covariant(Literal[1] | Literal["a"], int | str)
    assert is_subtype_covariant(Literal[1] | Literal[2], Literal[1, 2, 3])
    assert not is_subtype_covariant(Literal[1] | Literal[2], Literal[1, 3])
    assert is_subtype_covariant(Never, int | str)
    assert not is_subtype_covariant(int | str, Never)


def test_union_of_literals():
    assert is_subtype_covariant(Literal[1, 2], Literal[1] | Literal[2])
    assert is_subtype_covariant(Literal[1] | Literal[2], Literal[1, 2])
    assert is_subtype_covariant(Literal[1], Literal[1] | Literal[2])
    assert not is_subtype_covariant(Literal[1] | Literal[2], Literal[1])
    assert is_subtype_covariant(Literal[1], Literal[1, 2])
    assert not is_subtype_covariant(Literal[1, 2], Literal[1])
    assert is_subtype_covariant(Literal[1] | Literal[2], Literal[1, 2, 3])
    assert is_subtype_covariant(Literal[1, 2], Literal[1] | Literal[2] | Literal[3])
    assert not is_subtype_covariant(Literal[1] | Literal[2], Literal[2] | Literal[3])
    assert is_subtype_covariant(Literal[1, 2] | int, Literal[2] | int | Literal[1])
    assert is_subtype_covariant(Literal[2] | int | Literal[1], Literal[1, 2] | int)


def test_dataclass():
    assert is_subtype_covariant(Box, DataClassBase)
    assert is_subtype_covariant(IntBox, DataClassBase)
    assert not is_subtype_covariant(int, DataClassBase)
    assert not is_subtype_covariant(DataClassBase, DataClassBase)
    assert not is_subtype_covariant(Box | int, DataClassBase)
    assert not is_subtype_covariant(Box | IntBox, DataClassBase)


def test_typeddict():
    assert is_subtype_covariant(MyTD, TypedDictBase)
    assert is_subtype_covariant(SubTD, TypedDictBase)
    assert is_subtype_covariant(SubTD, MyTD)
    assert not is_subtype_covariant(MyTD, SubTD)
    assert not is_subtype_covariant(dict, TypedDictBase)
    assert not is_subtype_covariant(TypedDictBase, TypedDictBase)
    assert not is_subtype_covariant(MyTD, dict)
    assert not is_subtype_covariant(GenTD[int], dict[str, int])
    assert is_subtype_covariant(MyTD, object)


def test_typeddict_generic():
    assert is_subtype_covariant(GenTD, GenTD[Any])
    assert is_subtype_covariant(GenTD[int], GenTD)
    assert is_subtype_covariant(IntTD, GenTD[Any])
    assert is_subtype_covariant(GenTD[int], GenTD[int])
    assert is_subtype_covariant(GenTD[int], GenTD[object])
    assert is_subtype_covariant(GenTD[int], GenTD[Any])
    assert not is_subtype_covariant(GenTD[int], GenTD[str])
    assert is_subtype_covariant(IntTD, GenTD[int])
    assert is_subtype_covariant(IntTD, GenTD[object])
    assert not is_subtype_covariant(IntTD, GenTD[str])
    assert is_subtype_covariant(IntTD, TypedDictBase)


def test_unionbase():
    assert is_subtype_covariant(int | str, UnionBase)
    assert is_subtype_covariant(int | str | float, UnionBase)
    assert not is_subtype_covariant(int, UnionBase)
    assert not is_subtype_covariant(UnionBase, int)


def test_literalbase():
    assert is_subtype_covariant(Literal[1, 2], LiteralBase)
    assert is_subtype_covariant(Literal["a", "b", "c"], LiteralBase)
    assert not is_subtype_covariant(int, LiteralBase)
    assert not is_subtype_covariant(LiteralBase, Literal[1, 2])


def test_newtypebase():
    assert is_subtype_covariant(UserId, NewTypeBase)
    assert is_subtype_covariant(Flag, NewTypeBase)
    assert not is_subtype_covariant(NewTypeBase, UserId)
    assert not is_subtype_covariant(int, NewTypeBase)


def test_unions_in_nested_context():
    assert is_subtype_covariant(list[int | str], list[int | str])
    assert is_subtype_covariant(list[int | str], list[str | int])
    assert is_subtype_covariant(list[int], list[str | int])
    assert is_subtype_covariant(list[int | str], list[int | str | None])
    assert is_subtype_covariant(Box[int | str], Box[object])
    assert not is_subtype_covariant(list[int | str | None], list[int | str])


def test_literals_in_nested_context():
    assert is_subtype_covariant(list[Literal[1, 2]], list[Literal[1, 2]])
    assert is_subtype_covariant(list[Literal[1, 2]], list[Literal[2, 1]])
    assert is_subtype_covariant(list[Literal[1, 2]], list[Literal[1, 2, 3]])
    assert not is_subtype_covariant(list[Literal[1, 2, 3]], list[Literal[1, 2]])


def test_unions_vs_virtual_bases():
    assert is_subtype_covariant(Box[int] | Box[str], UnionBase)
    assert not is_subtype_covariant(Literal[1] | Literal[2], LiteralBase)
    assert not is_subtype_covariant(UserId | Email, NewTypeBase)
    assert not is_subtype_covariant(Box[int] | Box[str], DataClassBase)


def test_unionbase_in_nested_context():
    assert is_subtype_covariant(list[int | str], list[UnionBase])
    assert is_subtype_covariant(Box[int | str], Box[UnionBase])
    assert not is_subtype_covariant(list[int], list[UnionBase])


def test_nested_and_cross_cutting():
    assert is_subtype_covariant(list[UserId], list[int])
    assert not is_subtype_covariant(list[int], list[UserId])
    assert is_subtype_covariant(list[list[UserId]], list[list[int]])
    assert is_subtype_covariant(NestedBox[UserId], Box[list[int]])


def test_numeric_tower():
    assert is_subtype_covariant(bool, float)
    assert is_subtype_covariant(bool, complex)
    assert is_subtype_covariant(int, float)
    assert is_subtype_covariant(int, complex)
    assert is_subtype_covariant(float, complex)
    assert not is_subtype_covariant(float, bool)
    assert not is_subtype_covariant(float, int)
    assert not is_subtype_covariant(complex, bool)
    assert not is_subtype_covariant(complex, int)
    assert not is_subtype_covariant(complex, float)


def test_never():
    assert is_subtype_covariant(Never, Never)
    assert is_subtype_covariant(Never, int)
    assert is_subtype_covariant(Never, Any)
    assert not is_subtype_covariant(int, Never)
    assert not is_subtype_covariant(Any, Never)
    assert not is_subtype_covariant(list, Never)


AliasInt = TypeAliasType("AliasInt", int)


def test_type_alias_transparent():
    assert is_subtype_covariant(AliasInt, int)
    assert is_subtype_covariant(int, AliasInt)
    assert is_subtype_covariant(AliasInt, AliasInt)
    assert is_subtype_covariant(AliasInt, object)
    assert not is_subtype_covariant(AliasInt, str)
    assert is_subtype_covariant(bool, AliasInt)
    assert is_subtype_covariant(AliasInt, complex)


T = TypeVar("T")
AliasList = TypeAliasType("AliasList", list[T], type_params=(T,))


def test_type_alias_parameterized():
    assert is_subtype_covariant(AliasList[int], list[int])
    assert is_subtype_covariant(list[int], AliasList[int])
    assert is_subtype_covariant(AliasList[int], AliasList[int])
    assert is_subtype_covariant(AliasList[int], list[object])
    assert not is_subtype_covariant(AliasList[int], list[str])
    assert is_subtype_covariant(AliasList[int], Sequence[int])


AliasA = TypeAliasType("AliasA", int)
AliasB = TypeAliasType("AliasB", AliasA)


def test_type_alias_transitive_chain():
    assert is_subtype_covariant(AliasB, int)
    assert is_subtype_covariant(int, AliasB)
    assert is_subtype_covariant(AliasB, AliasA)
