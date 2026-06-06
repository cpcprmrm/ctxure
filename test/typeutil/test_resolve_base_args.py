from collections.abc import Collection, Iterable, Mapping, MutableMapping, MutableSequence, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Generic, TypeVar

from ctxure._typeutil import _resolve_base_typevar_substitution, resolve_base_args

T = TypeVar("T")
K = TypeVar("K")
V = TypeVar("V")


# Representative examples


def test_doc_resolve_str_int_none():
    assert resolve_base_args(str, int, ()) is None


def test_doc_resolve_list_sequence():
    assert resolve_base_args(list, Sequence, (int,)) == (int,)


def test_doc_resolve_list_list():
    assert resolve_base_args(list, list, (int,)) == (int,)


def test_doc_resolve_mydict():
    T = TypeVar("T")

    class MyDict(dict[int, list[T]], Generic[T]): ...

    assert resolve_base_args(MyDict, dict, (str,)) == (int, list[str])


# User-defined generics


def test_resolve_box_to_itself():
    T = TypeVar("T")

    @dataclass
    class Box(Generic[T]):
        value: T

    assert resolve_base_args(Box, Box, (int,)) == (int,)


def test_resolve_bare_box():
    T = TypeVar("T")

    @dataclass
    class Box(Generic[T]):
        value: T

    assert resolve_base_args(Box, Box, ()) == (Any,)


def test_resolve_bare_specialbox_to_box():
    T = TypeVar("T")

    @dataclass
    class Box(Generic[T]):
        value: T

    @dataclass
    class SpecialBox(Box[T], Generic[T]): ...

    assert resolve_base_args(SpecialBox, SpecialBox, ()) == (Any,)
    assert resolve_base_args(SpecialBox, Box, ()) == (Any,)


def test_resolve_specialbox_to_box():
    T = TypeVar("T")

    @dataclass
    class Box(Generic[T]):
        value: T

    @dataclass
    class SpecialBox(Box[T], Generic[T]): ...

    assert resolve_base_args(SpecialBox, Box, (int,)) == (int,)


def test_resolve_intbox_to_box():
    T = TypeVar("T")

    @dataclass
    class Box(Generic[T]):
        value: T

    @dataclass
    class IntBox(Box[int]): ...

    assert resolve_base_args(IntBox, Box, ()) == (int,)


def test_resolve_nestedbox_to_box():
    T = TypeVar("T")

    @dataclass
    class Box(Generic[T]):
        value: T

    @dataclass
    class NestedBox(Box[list[T]], Generic[T]): ...

    assert resolve_base_args(NestedBox, Box, (int,)) == (list[int],)


def test_resolve_nestedbox_to_box_str():
    T = TypeVar("T")

    @dataclass
    class Box(Generic[T]):
        value: T

    @dataclass
    class NestedBox(Box[list[T]], Generic[T]): ...

    assert resolve_base_args(NestedBox, Box, (str,)) == (list[str],)


def test_resolve_pair_to_itself():
    K = TypeVar("K")
    V = TypeVar("V")

    class Pair(Generic[K, V]): ...

    assert resolve_base_args(Pair, Pair, (str, int)) == (str, int)


# Builtin generics


def test_resolve_list_to_mutablesequence():
    assert resolve_base_args(list, MutableSequence, (int,)) == (int,)


def test_resolve_list_to_collection():
    assert resolve_base_args(list, Collection, (int,)) == (int,)


def test_resolve_list_to_iterable():
    assert resolve_base_args(list, Iterable, (int,)) == (int,)


def test_resolve_dict_to_mapping():
    assert resolve_base_args(dict, Mapping, (str, int)) == (str, int)


def test_resolve_dict_to_mutablemapping():
    assert resolve_base_args(dict, MutableMapping, (str, int)) == (str, int)


def test_resolve_dict_to_collection():
    assert resolve_base_args(dict, Collection, (str, int)) == (str,)


def test_resolve_dict_to_iterable():
    assert resolve_base_args(dict, Iterable, (str, int)) == (str,)


# Unparameterized generics


def test_resolve_bare_list():
    assert resolve_base_args(list, list, ()) == (Any,)


def test_resolve_bare_list_to_sequence():
    assert resolve_base_args(list, Sequence, ()) == (Any,)


def test_resolve_bare_dict():
    assert resolve_base_args(dict, dict, ()) == (Any, Any)


def test_resolve_bare_dict_to_mapping():
    assert resolve_base_args(dict, Mapping, ()) == (Any, Any)


# Unrelated types


def test_resolve_unrelated_int_str():
    assert resolve_base_args(int, str, ()) is None


def test_resolve_list_not_subtype_of_dict():
    assert resolve_base_args(list, dict, (int,)) is None


def test_resolve_sequence_not_subtype_of_list():
    assert resolve_base_args(Sequence, list, (int,)) is None


# Non-generic inheritance


def test_resolve_same_nongeneric():
    assert resolve_base_args(int, int, ()) == ()


def test_resolve_bool_to_int():
    assert resolve_base_args(bool, int, ()) == ()


def test_resolve_datetime_to_date():
    assert resolve_base_args(datetime, date, ()) == ()


# Bare user generic → builtin generic base


def test_resolve_bare_user_generic_to_builtin_generic():
    T = TypeVar("T")

    class MyList(list[T], Generic[T]): ...

    assert resolve_base_args(MyList, Sequence, ()) == (Any,)


# Bare user generic → plain base


def test_resolve_bare_user_generic_to_plain_base():
    T = TypeVar("T")

    class Mixin: ...

    class MyGeneric(Mixin, Generic[T]): ...

    assert resolve_base_args(MyGeneric, Mixin, ()) == ()


# Parameterized user generic → plain base


def test_resolve_param_user_generic_to_plain_base():
    T = TypeVar("T")

    class Mixin: ...

    class MyGeneric(Mixin, Generic[T]): ...

    assert resolve_base_args(MyGeneric, Mixin, (int,)) == ()


# Plain class → builtin generic base


def test_resolve_plain_subclass_to_builtin_generic():
    class MyList(list): ...

    assert resolve_base_args(MyList, Sequence, ()) == (Any,)


def test_resolve_plain_subclass_to_builtin_generic_multi_param():
    class MyDict(dict): ...

    assert resolve_base_args(MyDict, Mapping, ()) == (Any, Any)


# Multi-level user-defined inheritance


def test_resolve_multi_level():
    T = TypeVar("T")

    @dataclass
    class Base(Generic[T]):
        base: T

    @dataclass
    class Middle(Base[list[T]], Generic[T]):
        mid: T

    @dataclass
    class Final(Middle[dict[str, T]], Generic[T]):
        final: T

    assert resolve_base_args(Final, Middle, (int,)) == (dict[str, int],)
    assert resolve_base_args(Final, Base, (int,)) == (list[dict[str, int]],)


def test_resolve_inheritance_type_collapse():
    S = TypeVar("S")
    T = TypeVar("T")

    @dataclass
    class Base(Generic[S, T]):
        foo: S
        bar: T

    U = TypeVar("U")

    @dataclass
    class Derived(Base[U, U], Generic[U]): ...

    assert resolve_base_args(Derived, Base, (str,)) == (str, str)


# Multiple bases


def test_resolve_multiple_bases():
    T = TypeVar("T")

    @dataclass
    class Foo(Generic[T]):
        foo: T

    @dataclass
    class Bar(Generic[T]):
        bar: T

    @dataclass
    class Baz(Foo[T], Bar[list[T]], Generic[T]):
        baz: T

    assert resolve_base_args(Baz, Foo, (int,)) == (int,)
    assert resolve_base_args(Baz, Bar, (int,)) == (list[int],)


# Fixed param inheritance


def test_resolve_fixed_param_base():
    T = TypeVar("T")

    @dataclass
    class Base(Generic[T]):
        base: T

    @dataclass
    class Derived(Base[int]):
        derived: str

    assert resolve_base_args(Derived, Base, ()) == (int,)


def test_resolve_fixed_parameterized_param_base():
    T = TypeVar("T")

    @dataclass
    class Base(Generic[T]):
        base: T

    @dataclass
    class Derived(Base[list[int]]):
        derived: str

    assert resolve_base_args(Derived, Base, ()) == (list[int],)


# Dict returns all bases in hierarchy


def test_all_bases_present():
    T = TypeVar("T")

    @dataclass
    class Box(Generic[T]):
        value: T

    @dataclass
    class SpecialBox(Box[T], Generic[T]): ...

    result = _resolve_base_typevar_substitution(SpecialBox, (int,))
    assert SpecialBox in result
    assert Box in result


def test_all_builtin_bases_present():
    result = _resolve_base_typevar_substitution(list, (int,))
    assert list in result
    assert MutableSequence in result
    assert Sequence in result
    assert Collection in result
    assert Iterable in result
