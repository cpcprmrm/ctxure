from abc import ABC
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from itertools import permutations
from typing import Any, Generic, Literal, NewType, Optional, Sequence, TypedDict, TypeVar, cast

import pytest
from typing_extensions import TypeAliasType

from ctxure.multidispatch import Dispatch, MultipleMatchesFound, NoMatchFound, _cannot_set_orig_class


def test_nullary_dispatch_simple():
    dsp = Dispatch()

    @dsp
    def foo() -> str:
        return "foo"

    assert foo() == "foo"

    @dsp
    def bar() -> str:
        return "bar"

    assert foo() == "foo"
    assert bar() == "bar"


def test_unary_dispatch_simple():
    dsp = Dispatch()

    @dsp
    def foo(x: int) -> str:
        return "foo(int)"

    assert foo(1) == "foo(int)"

    with pytest.raises(NoMatchFound):
        foo("a")

    with pytest.raises(NoMatchFound):
        foo()

    @dsp
    def foo(x: str) -> str:
        return "foo(str)"

    @dsp
    def bar(x: str) -> str:
        return "bar(str)"

    assert foo("a") == "foo(str)"
    assert foo(1) == "foo(int)"
    assert bar("a") == "bar(str)"


def test_unary_dispatch_simple_hierarchy():
    dsp = Dispatch()

    class A:
        pass

    class B(A):
        pass

    @dsp
    def foo(x: A) -> str:
        return "A"

    assert foo(A()) == "A"
    assert foo(B()) == "A"

    @dsp
    def foo(x: B) -> str:
        return "B"

    assert foo(A()) == "A"
    assert foo(B()) == "B"

    with pytest.raises(NoMatchFound):
        foo(object())


def test_unary_dispatch_simple_hierarchy_reversed_registration():
    dsp = Dispatch()

    class A:
        pass

    class B(A):
        pass

    @dsp
    def foo(x: B) -> str:
        return "B"

    @dsp
    def foo(x: A) -> str:
        return "A"

    assert foo(A()) == "A"
    assert foo(B()) == "B"

    with pytest.raises(NoMatchFound):
        foo(object())


def test_unary_dispatch_diamond_hierarchy():
    class A:
        pass

    class B:
        pass

    class C(A, B):
        pass

    def foo(x: A) -> str:
        return "A"

    foo_a = foo

    def foo(x: B) -> str:
        return "B"

    foo_b = foo

    def foo(x: C) -> str:
        return "C"

    foo_c = foo

    for order in permutations([foo_a, foo_b, foo_c]):
        dsp = Dispatch()
        for f in order:
            dsp(f)
        mm = dsp["foo"]
        assert mm(C()) == "C", order
        assert mm(A()) == "A", order
        assert mm(B()) == "B", order


def test_unary_dispatch_object_any():
    dsp = Dispatch()

    @dsp
    def foo(x: object) -> str:
        return "object"

    assert foo(1) == "object"
    assert foo("a") == "object"
    assert foo(None) == "object"

    @dsp
    def foo(x: Any) -> str:
        return "Any"

    assert foo(1) == "object"
    assert foo("a") == "object"
    assert foo(None) == "object"


def test_unary_dispatch_ambiguous():
    dsp = Dispatch()

    class A:
        pass

    class B_0(A):
        pass

    class B_1:
        pass

    class C_0(B_0, B_1):
        pass

    @dsp
    def foo(x: A):
        pass

    @dsp
    def foo(x: B_0):
        pass

    @dsp
    def foo(x: B_1):
        pass

    with pytest.raises(MultipleMatchesFound) as e:
        foo(C_0())
    assert {m.signature for m in e.value.candidates} == {(B_0,), (B_1,)}

    class B_2(A):
        pass

    @dsp
    def foo(x: B_2):
        pass

    with pytest.raises(MultipleMatchesFound) as e:
        foo(C_0())
    assert {m.signature for m in e.value.candidates} == {(B_0,), (B_1,)}

    class C_1(B_0, B_1, B_2):
        pass

    with pytest.raises(MultipleMatchesFound) as e:
        foo(C_1())

    assert {m.signature for m in e.value.candidates} == {(B_0,), (B_1,), (B_2,)}

    with pytest.raises(MultipleMatchesFound) as e:
        foo(C_0())
    assert {m.signature for m in e.value.candidates} == {(B_0,), (B_1,)}

    with pytest.raises(MultipleMatchesFound) as e:
        foo(C_1())
    assert {m.signature for m in e.value.candidates} == {(B_0,), (B_1,), (B_2,)}


def test_unary_dispatch_union():
    dsp = Dispatch()

    @dsp
    def foo(x: int | str) -> str:
        return "int | str"

    assert foo(1) == "int | str"
    assert foo("a") == "int | str"

    with pytest.raises(NoMatchFound):
        foo(1.0)

    @dsp
    def foo(x: str) -> str:
        return "str"

    assert foo(1) == "int | str"
    assert foo("a") == "str"


def test_unary_dispatch_ambiguous_union():
    dsp = Dispatch()

    @dsp
    def foo(x: int | str) -> str:
        return "int | str"

    @dsp
    def foo(x: str | list) -> str:
        return "str | list"

    assert foo(1) == "int | str"

    with pytest.raises(MultipleMatchesFound) as e:
        foo("a")
    assert {m.signature for m in e.value.candidates} == {(int | str,), (str | list,)}


def test_unary_dispatch_literal():
    dsp = Dispatch()

    @dsp
    def foo(x: Literal[1, 2]) -> str:
        return "L12"

    assert foo(1) == "L12"
    assert foo(2) == "L12"

    with pytest.raises(NoMatchFound):
        foo(3)
    with pytest.raises(NoMatchFound):
        foo("a")

    @dsp
    def foo(x: int) -> str:
        return "int"

    assert foo(1) == "L12"
    assert foo(2) == "L12"
    assert foo(3) == "int"


def test_unary_dispatch_literal_and_others():
    """
    When a method has Literal as type hint, the `arg_type` runs different code path.
    This test covers some cases of that code path to ensure it works correctly.
    """
    dsp = Dispatch()

    class Foo(Generic[TypeVar("T")]):
        pass

    @dsp
    def foo(x: Literal[1, 2]) -> str:
        return "L12"

    @dsp
    def foo(x: Foo[int]) -> str:
        return "Foo"

    @dsp
    def foo(x: type[int]) -> str:
        return "int"

    assert foo(1) == "L12"
    assert foo(2) == "L12"
    assert foo(Foo[int]()) == "Foo"
    assert foo(int) == "int"


def test_unary_dispatch_literal_string():
    dsp = Dispatch()

    @dsp
    def foo(x: Literal["a", "b"]) -> str:
        return "ab"

    @dsp
    def foo(x: str) -> str:
        return "str"

    assert foo("a") == "ab"
    assert foo("b") == "ab"
    assert foo("c") == "str"


def test_unary_dispatch_literal_overlap_more_specific_wins():
    dsp = Dispatch()

    @dsp
    def foo(x: Literal[1]) -> str:
        return "L1"

    @dsp
    def foo(x: Literal[1, 2]) -> str:
        return "L12"

    @dsp
    def foo(x: int) -> str:
        return "int"

    assert foo(1) == "L1"
    assert foo(2) == "L12"
    assert foo(3) == "int"


def test_unary_dispatch_literal_ambiguous():
    dsp = Dispatch()

    @dsp
    def foo(x: Literal[1, 2]) -> str:
        return "12"

    @dsp
    def foo(x: Literal[2, 3]) -> str:
        return "23"

    assert foo(1) == "12"
    assert foo(3) == "23"

    with pytest.raises(MultipleMatchesFound) as e:
        foo(2)
    assert {m.signature for m in e.value.candidates} == {(Literal[1, 2],), (Literal[2, 3],)}


def test_unary_dispatch_literal_bool_vs_int_distinct():
    dsp = Dispatch()

    @dsp
    def foo(x: Literal[1]) -> str:
        return "L1"

    @dsp
    def foo(x: Literal[True]) -> str:
        return "LTrue"

    @dsp
    def foo(x: int) -> str:
        return "int"

    @dsp
    def foo(x: bool) -> str:
        return "bool"

    assert foo(1) == "L1"
    assert foo(True) == "LTrue"
    assert foo(0) == "int"
    assert foo(False) == "bool"


def test_unary_dispatch_literal_in_union():
    dsp = Dispatch()

    @dsp
    def foo(x: Literal["x", "y"] | int) -> str:
        return "L-or-int"

    assert foo("x") == "L-or-int"
    assert foo("y") == "L-or-int"
    assert foo(1) == "L-or-int"

    with pytest.raises(NoMatchFound):
        foo("z")
    with pytest.raises(NoMatchFound):
        foo(1.5)


def test_unary_dispatch_literal_none():
    dsp = Dispatch()

    @dsp
    def foo(x: Literal[None]) -> str:
        return "L-None"

    @dsp
    def foo(x: int) -> str:
        return "int"

    assert foo(None) == "L-None"
    assert foo(1) == "int"

    with pytest.raises(NoMatchFound):
        foo("a")


def test_unary_dispatch_literal_none_in_union():
    dsp = Dispatch()

    @dsp
    def foo(x: Literal[None] | int) -> str:
        return "None-or-int"

    assert foo(None) == "None-or-int"
    assert foo(1) == "None-or-int"

    with pytest.raises(NoMatchFound):
        foo("a")


def test_unary_dispatch_literal_with_unhashable_arg():
    dsp = Dispatch()

    @dsp
    def foo(x: Literal[1, 2]) -> str:
        return "lit"

    @dsp
    def foo(x: list) -> str:
        return "list"

    @dsp
    def foo(x: dict) -> str:
        return "dict"

    assert foo([1, 2, 3]) == "list"
    assert foo({"a": 1}) == "dict"
    assert foo(1) == "lit"


def test_binary_dispatch_literal_registered_at_later_position_first():
    dsp = Dispatch()

    @dsp
    def foo(x: int, y: Literal["a"]) -> str:
        return "int, 'a'"

    @dsp
    def foo(x: Literal[0], y: str) -> str:
        return "0, str"

    assert foo(5, "a") == "int, 'a'"
    assert foo(0, "b") == "0, str"
    assert foo(0, "a") == "0, str"


def test_binary_dispatch_literal_only_at_first_position():
    dsp = Dispatch()

    @dsp
    def foo(x: Literal["a"], y: int) -> str:
        return "'a', int"

    @dsp
    def foo(x: str, y: int) -> str:
        return "str, int"

    assert foo("a", 1) == "'a', int"
    assert foo("b", 1) == "str, int"


def test_unary_dispatch_literal_covariant():
    dsp = Dispatch()

    @dsp.covariant(0)
    def foo(x: Literal[1, 2]) -> str:
        return "L12"

    @dsp.covariant(0)
    def foo(x: int) -> str:
        return "int"

    assert foo(1) == "L12"
    assert foo(2) == "L12"
    assert foo(3) == "int"


def test_overriding():
    dsp = Dispatch()

    @dsp
    def foo(x: int) -> str:
        return "int"

    assert foo(1) == "int"

    @dsp
    def foo(x: int) -> str:
        return "INT"

    assert foo(1) == "INT"


def test_binary_dispatch_simple():
    dsp = Dispatch()

    @dsp
    def foo(x: int, y: str) -> str:
        return "int, str"

    @dsp
    def foo(x: str, y: int) -> str:
        return "str, int"

    assert foo(1, "a") == "int, str"
    assert foo("a", 1) == "str, int"

    with pytest.raises(NoMatchFound):
        foo(1, 2)

    with pytest.raises(NoMatchFound):
        foo("a", "b")

    with pytest.raises(NoMatchFound):
        foo()

    with pytest.raises(NoMatchFound):
        foo(1)

    with pytest.raises(NoMatchFound):
        foo(1, "a", 1)


def test_binary_dispatch_hierarchy():
    dsp = Dispatch()

    class A:
        pass

    class B(A):
        pass

    @dsp
    def foo(x: B, y: A) -> str:
        return "B, A"

    @dsp
    def foo(x: A, y: B) -> str:
        return "A, B"

    assert foo(B(), A()) == "B, A"
    assert foo(A(), B()) == "A, B"
    assert foo(B(), B()) == "B, A"

    with pytest.raises(NoMatchFound):
        foo(A(), A())

    @dsp
    def foo(x: A, y: A) -> str:
        return "A, A"

    assert foo(A(), A()) == "A, A"
    assert foo(B(), A()) == "B, A"
    assert foo(A(), B()) == "A, B"
    assert foo(B(), B()) == "B, A"

    @dsp
    def foo(x: B, y: B) -> str:
        return "B, B"

    assert foo(A(), A()) == "A, A"
    assert foo(B(), A()) == "B, A"
    assert foo(A(), B()) == "A, B"
    assert foo(B(), B()) == "B, B"


def test_binary_dispatch_ambiguous():
    dsp = Dispatch()

    class A:
        pass

    class B_0(A):
        pass

    class B_1:
        pass

    class C_0(B_0, B_1):
        pass

    @dsp
    def foo(x: int, y: A):
        pass

    @dsp
    def foo(x: int, y: B_0):
        pass

    @dsp
    def foo(x: int, y: B_1):
        pass

    with pytest.raises(MultipleMatchesFound) as e:
        foo(1, C_0())
    assert {m.signature for m in e.value.candidates} == {
        (
            int,
            B_0,
        ),
        (
            int,
            B_1,
        ),
    }


def test_binary_dispatch_deferred_tiebreak():
    dsp = Dispatch()

    class A:
        pass

    class B:
        pass

    class C(A, B):
        pass

    @dsp
    def foo(x: A, y: int) -> str:
        return "A, int"

    @dsp
    def foo(x: B, y: str) -> str:
        return "B, str"

    assert foo(C(), 1) == "A, int"
    assert foo(C(), "x") == "B, str"
    assert foo(A(), 1) == "A, int"
    assert foo(B(), "x") == "B, str"


def test_binary_dispatch_deferred_tiebreak_by_specificity():
    dsp = Dispatch()

    class A:
        pass

    class B:
        pass

    class C(A, B):
        pass

    @dsp
    def foo(x: A, y: int) -> str:
        return "A, int"

    @dsp
    def foo(x: B, y: float) -> str:
        return "B, float"

    assert foo(C(), 1) == "A, int"
    assert foo(C(), 1.0) == "B, float"
    assert foo(A(), 1) == "A, int"
    assert foo(B(), 1.0) == "B, float"


def test_binary_dispatch_deferred_tiebreak_still_ambiguous():
    dsp = Dispatch()

    class A:
        pass

    class B:
        pass

    class C(A, B):
        pass

    @dsp
    def foo(x: A, y: int) -> str:
        return "A, int"

    @dsp
    def foo(x: B, y: int) -> str:
        return "B, int"

    with pytest.raises(MultipleMatchesFound) as e:
        foo(C(), 1)
    assert {m.signature for m in e.value.candidates} == {(A, int), (B, int)}


def test_binary_dispatch_deferred_tiebreak_three_way():
    dsp = Dispatch()

    class A:
        pass

    class B:
        pass

    class C:
        pass

    class D(A, B, C):
        pass

    @dsp
    def foo(x: A, y: int) -> str:
        return "A, int"

    @dsp
    def foo(x: B, y: str) -> str:
        return "B, str"

    @dsp
    def foo(x: C, y: float) -> str:
        return "C, float"

    assert foo(D(), 1) == "A, int"
    assert foo(D(), "x") == "B, str"
    assert foo(D(), 1.0) == "C, float"


def test_ternary_dispatch_simple():
    dsp = Dispatch()

    @dsp
    def foo(x: int, y: str, z: int) -> str:
        return "int, str, int"

    @dsp
    def foo(x: str, y: int, z: set) -> str:
        return "str, int, set"

    assert foo(1, "a", 2) == "int, str, int"
    assert foo("a", 1, set()) == "str, int, set"

    with pytest.raises(NoMatchFound):
        foo(1, "a", "b")

    with pytest.raises(NoMatchFound):
        foo("a", 1, 1)


def test_ternary_dispatch_deferred_tiebreak():
    dsp = Dispatch()

    class A:
        pass

    class B:
        pass

    class C(A, B):
        pass

    @dsp.covariant(0)
    def foo(x: A, y: int, z: str) -> str:
        return "A, int, str"

    @dsp.covariant(0)
    def foo(x: B, y: int, z: int) -> str:
        return "B, int, int"

    assert foo(C(), 1, "x") == "A, int, str"
    assert foo(C(), 1, 1) == "B, int, int"


def test_mixed_arity_dispatch():
    dsp = Dispatch()

    @dsp
    def foo(x: int) -> int:
        return 1

    @dsp
    def foo(x: int, y: int, z: int) -> int:
        return 3

    @dsp
    def foo(x: int, y: int) -> int:
        return 2

    @dsp
    def foo() -> int:
        return 0

    assert foo() == 0
    assert foo(1) == 1
    assert foo(1, 1) == 2
    assert foo(1, 1, 1) == 3

    with pytest.raises(NoMatchFound):
        foo(1, 1, 1, 1)


def test_dispatch_default_value_not_allowed():
    dsp = Dispatch()

    with pytest.raises(TypeError):

        @dsp
        def foo(x: int = 0):
            pass

    with pytest.raises(TypeError):

        @dsp
        def foo(x: int, y: str = "a"):
            pass


def test_dispatch_unannotated_parameter_is_object():
    dsp = Dispatch()

    @dsp
    def foo(x) -> str:
        return "object"

    @dsp
    def foo(x: int) -> str:
        return "int"

    assert foo(1) == "int"
    assert foo("a") == "object"
    assert foo(None) == "object"


def test_dispatch_keyword_only_arguments():
    dsp = Dispatch()

    @dsp
    def foo(*, x: int) -> str:
        return "int"

    assert foo(x=1) == "int"

    @dsp
    def foo(x: str, *, y: int = 0) -> int:
        return y

    @dsp
    def foo(x: str, *, y: str = "") -> str:
        return y

    assert foo("a", y=1) == 1
    assert foo("a", y="b") == "b"


def test_dispatch_on_enum():
    dsp = Dispatch()

    class Color(Enum):
        RED = 1
        GREEN = 2
        BLUE = 3

    @dsp
    def foo(x: Color) -> str:
        return "Color"

    assert foo(Color.RED) == "Color"

    with pytest.raises(NoMatchFound):
        foo(1)


def test_dispatch_on_type_simple():
    dsp = Dispatch()

    @dsp
    def foo(x: type[int]) -> str:
        return "int"

    @dsp
    def foo(x: type[str]) -> str:
        return "str"

    assert foo(int) == "int"
    assert foo(str) == "str"

    class A:
        pass

    @dsp
    def foo(x: type[A]) -> str:
        return "A"

    assert foo(A) == "A"


def test_dispatch_on_type_metaclass():
    dsp = Dispatch()

    class Color(Enum):
        RED = 1

    class Base(ABC):
        pass

    @dsp
    def foo(x: type[Color]) -> str:
        return "Color"

    @dsp
    def foo(x: type[int]) -> str:
        return "int"

    @dsp
    def foo(x: type[Base]) -> str:
        return "Base"

    assert foo(Color) == "Color"
    assert foo(int) == "int"
    assert foo(Base) == "Base"

    @dsp.covariant(0)
    def bar(x: type[Enum]) -> str:
        return "Enum"

    assert bar(Color) == "Enum"
    assert bar(Enum) == "Enum"

    class Derived(Base):
        pass

    @dsp.covariant(0)
    def baz(x: type[Base]) -> str:
        return "Base"

    assert baz(Base) == "Base"
    assert baz(Derived) == "Base"


def test_dispatch_on_type_newtype():
    dsp = Dispatch()

    Int = NewType("Int", int)

    @dsp
    def foo(x: type[Int]) -> str:
        return "Int"

    @dsp
    def foo(x: type[int]) -> str:
        return "int"

    assert foo(Int) == "Int"
    assert foo(int) == "int"


def test_dispatch_on_type_user_defined_generic():
    dsp = Dispatch()

    T = TypeVar("T")

    @dataclass
    class Box(Generic[T]):
        value: T

    @dsp
    def foo(x: type[Box[int]]) -> str:
        return "Box[int]"

    @dsp
    def foo(x: type[Box[str]]) -> str:
        return "Box[str]"

    assert foo(Box[int]) == "Box[int]"
    assert foo(Box[str]) == "Box[str]"


def test_dispatch_on_type_generic_collection():
    dsp = Dispatch()

    @dsp
    def foo(x: type[list[int]]) -> str:
        return "list[int]"

    @dsp
    def foo(x: type[list[str]]) -> str:
        return "list[str]"

    @dsp
    def foo(x: type[tuple[str]]) -> str:
        return "tuple[str]"

    @dsp
    def foo(x: type[tuple[str, ...]]) -> str:
        return "tuple[str, ...]"

    @dsp
    def foo(x: type[tuple[int, float]]) -> str:
        return "tuple[int, float]"

    assert foo(list[int]) == "list[int]"
    assert foo(list[str]) == "list[str]"
    assert foo(tuple[str]) == "tuple[str]"
    assert foo(tuple[str, ...]) == "tuple[str, ...]"
    assert foo(tuple[int, float]) == "tuple[int, float]"


def test_cache():
    dsp = Dispatch()

    @dsp
    def foo(x: object):
        pass

    @dsp
    def foo(x: int):
        pass

    @dsp
    def foo(x: int):
        pass

    cache = dsp["foo"].cache
    assert not cache

    foo("a")
    assert len(cache) == 1
    assert (str,) in cache

    foo("a")
    assert len(cache) == 1
    assert (str,) in cache

    foo(1.0)
    assert len(cache) == 2
    assert (str,) in cache
    assert (float,) in cache

    foo(1.0)
    assert len(cache) == 2
    assert (str,) in cache
    assert (float,) in cache

    foo(1)
    assert len(cache) == 3
    assert (str,) in cache
    assert (float,) in cache
    assert (int,) in cache

    @dsp
    def foo(x: float):
        pass

    assert len(cache) == 0

    dsp["foo"].dispatch(float)
    assert len(cache) == 0


def test_cache_with_literal_bounded_by_registered_values():
    dsp = Dispatch()

    @dsp
    def foo(x: Literal["red", "blue"]) -> str:
        return "color"

    @dsp
    def foo(x: str) -> str:
        return "str"

    mm = dsp["foo"]
    cache = mm.cache

    for s in ["a", "b", "c", "d", "e", "f"]:
        foo(s)
    assert list(cache.keys()) == [(str,)]

    foo("red")
    foo("blue")
    assert set(cache.keys()) == {(str,), (Literal["red"],), (Literal["blue"],)}


def test_copy():
    orig = Dispatch()

    @orig
    def foo(x: int) -> str:
        return "foo(int)"

    copy = orig.copy()

    assert orig["foo"](1) == "foo(int)"
    assert copy["foo"](1) == "foo(int)"
    assert foo(1) == "foo(int)"

    @copy
    def foo(x: str) -> str:
        return "copy:foo(str)"

    assert orig["foo"](1) == "foo(int)"
    assert copy["foo"](1) == "foo(int)"
    assert copy["foo"]("a") == "copy:foo(str)"

    with pytest.raises(NoMatchFound):
        orig["foo"]("a")

    @orig
    def foo(x: str) -> str:
        return "orig:foo(str)"

    assert orig["foo"](1) == "foo(int)"
    assert orig["foo"]("a") == "orig:foo(str)"
    assert copy["foo"](1) == "foo(int)"
    assert copy["foo"]("a") == "copy:foo(str)"


def test_copy_preserves_literal_interest():
    orig = Dispatch()

    @orig
    def foo(x: Literal[1, 2]) -> str:
        return "L12"

    @orig
    def foo(x: int) -> str:
        return "int"

    copy = orig.copy()

    assert copy["foo"](1) == "L12"
    assert copy["foo"](3) == "int"
    assert copy["foo"].literal_interest is not orig["foo"].literal_interest

    @copy
    def foo(x: Literal[3]) -> str:
        return "L3"

    assert copy["foo"](3) == "L3"
    assert orig["foo"](3) == "int"


def test_nested_scope_register():
    # A function in a nested scope can be registered to the dispatcher defined in outside scope.
    # `functools.singledispatch` behaves similarly.

    dsp = Dispatch()

    @dsp
    def foo(x: int) -> str:
        return "int"

    def nested_func_1():
        @dsp
        def foo(x: str) -> str:
            return "str"

        assert foo("a") == "str"

    nested_func_1()

    assert foo(1) == "int"

    def nested_func_2():
        @dsp
        def bar(x: str) -> str:
            return "str"

        assert bar("a") == "str"

    nested_func_2()

    with pytest.raises(NameError):
        bar("a")  # type: ignore # noqa

    bar = dsp["bar"]
    assert bar("a") == "str"


def test_invariance_unary():
    dsp = Dispatch()

    T = TypeVar("T")

    @dataclass
    class Foo(Generic[T]):
        value: T

    @dsp
    def foo(x: Foo[int | None]) -> str:
        return "union"

    assert foo(Foo[int | None](None)) == "union"
    assert foo(Foo[None | int](None)) == "union"

    with pytest.raises(NoMatchFound):
        foo(Foo[int](1))

    with pytest.raises(NoMatchFound):
        foo(Foo[str]("a"))

    @dsp
    def foo(x: Foo[int]) -> str:
        return "int"

    assert foo(Foo[int | None](None)) == "union"
    assert foo(Foo[int](1)) == "int"

    with pytest.raises(NoMatchFound):
        foo(Foo[str]("a"))

    @dsp
    def foo(x: Foo[str]) -> str:
        return "str"

    assert foo(Foo[int | None](None)) == "union"
    assert foo(Foo[int](1)) == "int"
    assert foo(Foo[str]("a")) == "str"


def test_covariance_unary():
    dsp = Dispatch()

    T = TypeVar("T")

    @dataclass
    class Foo(Generic[T]):
        value: T

    @dsp.covariant(0)
    def foo(x: Foo[int | None]) -> str:
        return "union"

    assert foo(Foo[int | None](None)) == "union"
    assert foo(Foo[None | int](None)) == "union"
    assert foo(Foo[int](1)) == "union"

    with pytest.raises(NoMatchFound):
        foo(Foo[str]("a"))

    @dsp.covariant(0)
    def foo(x: Foo[int]) -> str:
        return "int"

    assert foo(Foo[int | None](None)) == "union"
    assert foo(Foo[int](1)) == "int"

    with pytest.raises(NoMatchFound):
        foo(Foo[str]("a"))

    @dsp.covariant(0)
    def foo(x: Foo[str]) -> str:
        return "str"

    assert foo(Foo[int | None](None)) == "union"
    assert foo(Foo[int](1)) == "int"
    assert foo(Foo[str]("a")) == "str"


def test_invariance_nested_unary():
    dsp = Dispatch()

    T = TypeVar("T")

    @dataclass
    class Foo(Generic[T]):
        value: T

    @dsp
    def foo(x: Foo[list[int]]) -> str:
        return "list[int]"

    assert foo(Foo[list[int]]([])) == "list[int]"
    assert foo(Foo[list[int]]([1, 2, 3])) == "list[int]"

    with pytest.raises(NoMatchFound):
        foo(Foo[list]([1]))

    with pytest.raises(NoMatchFound):
        foo(Foo[list[Any]]([1]))

    with pytest.raises(NoMatchFound):
        foo(Foo[list[object]]([1]))

    with pytest.raises(NoMatchFound):
        foo(Foo[list[bool]]([True]))

    with pytest.raises(NoMatchFound):
        foo(Foo[list[str]](["a"]))

    @dsp
    def foo(x: Foo[list[bool]]) -> str:
        return "list[bool]"

    assert foo(Foo[list[int]]([])) == "list[int]"
    assert foo(Foo[list[int]]([1, 2, 3])) == "list[int]"
    assert foo(Foo[list[bool]]([True])) == "list[bool]"

    with pytest.raises(NoMatchFound):
        foo(Foo[list]([1]))

    with pytest.raises(NoMatchFound):
        foo(Foo[list[Any]]([1]))

    with pytest.raises(NoMatchFound):
        foo(Foo[list[object]]([1]))

    with pytest.raises(NoMatchFound):
        foo(Foo[list[str]](["a"]))

    @dsp
    def foo(x: Foo[list[str]]) -> str:
        return "list[str]"

    assert foo(Foo[list[int]]([])) == "list[int]"
    assert foo(Foo[list[int]]([1, 2, 3])) == "list[int]"
    assert foo(Foo[list[bool]]([True])) == "list[bool]"
    assert foo(Foo[list[str]](["a"])) == "list[str]"


def test_covariance_nested_unary():
    dsp = Dispatch()

    T = TypeVar("T")

    @dataclass
    class Foo(Generic[T]):
        value: T

    @dsp.covariant(0)
    def foo(x: Foo[list[int]]) -> str:
        return "list[int]"

    assert foo(Foo[list[int]]([])) == "list[int]"
    assert foo(Foo[list[int]]([1, 2, 3])) == "list[int]"
    assert foo(Foo[list[bool]]([True])) == "list[int]"

    with pytest.raises(NoMatchFound):
        foo(Foo[list]([1]))

    with pytest.raises(NoMatchFound):
        foo(Foo[list[Any]]([1]))

    with pytest.raises(NoMatchFound):
        foo(Foo[list[object]]([1]))

    with pytest.raises(NoMatchFound):
        foo(Foo[list[str]](["a"]))

    @dsp.covariant(0)
    def foo(x: Foo[list[bool]]) -> str:
        return "list[bool]"

    assert foo(Foo[list[int]]([])) == "list[int]"
    assert foo(Foo[list[int]]([1, 2, 3])) == "list[int]"
    assert foo(Foo[list[bool]]([True])) == "list[bool]"

    with pytest.raises(NoMatchFound):
        foo(Foo[list]([1]))

    with pytest.raises(NoMatchFound):
        foo(Foo[list[Any]]([1]))

    with pytest.raises(NoMatchFound):
        foo(Foo[list[object]]([1]))

    with pytest.raises(NoMatchFound):
        foo(Foo[list[str]](["a"]))

    @dsp.covariant(0)
    def foo(x: Foo[list[str]]) -> str:
        return "list[str]"

    assert foo(Foo[list[int]]([])) == "list[int]"
    assert foo(Foo[list[int]]([1, 2, 3])) == "list[int]"
    assert foo(Foo[list[bool]]([True])) == "list[bool]"
    assert foo(Foo[list[str]](["a"])) == "list[str]"


def test_mixed_variance_binary():
    dsp = Dispatch()

    T = TypeVar("T")

    @dataclass
    class Foo(Generic[T]):
        pass

    @dsp.covariant(0)
    def foo(x: Foo[int], y: Foo[int]) -> str:
        return "foo(c, i)"

    assert foo(Foo[int](), Foo[int]()) == "foo(c, i)"
    assert foo(Foo[bool](), Foo[int]()) == "foo(c, i)"

    with pytest.raises(NoMatchFound):
        assert foo(Foo[int](), Foo[bool]()) == "foo"


def test_invariance_binary():
    dsp = Dispatch()

    T = TypeVar("T")

    @dataclass
    class Foo(Generic[T]):
        pass

    @dsp
    def foo(x: Foo[int], y: Foo[int]) -> str:
        return "foo"

    assert foo(Foo[int](), Foo[int]()) == "foo"

    with pytest.raises(NoMatchFound):
        assert foo(Foo[bool](), Foo[int]()) == "foo"

    with pytest.raises(NoMatchFound):
        assert foo(Foo[int](), Foo[bool]()) == "foo"


def test_covariance_binary():
    dsp = Dispatch()

    T = TypeVar("T")

    @dataclass
    class Foo(Generic[T]):
        pass

    @dsp.covariant(0, 1)
    def foo(x: Foo[int], y: Foo[int]) -> str:
        return "foo"

    assert foo(Foo[int](), Foo[int]()) == "foo"
    assert foo(Foo[int](), Foo[bool]()) == "foo"
    assert foo(Foo[bool](), Foo[int]()) == "foo"
    assert foo(Foo[bool](), Foo[bool]()) == "foo"


def test_invariance_nonparam_hierarchy():
    dsp = Dispatch()

    @dsp
    def foo(x: int | date) -> str:
        return "foo"

    assert foo(1) == "foo"
    assert foo(date.today()) == "foo"
    assert foo(True) == "foo"
    assert foo(datetime.now()) == "foo"

    T = TypeVar("T")

    @dataclass
    class Base(Generic[T]):
        pass

    @dataclass
    class Derived(Base[T]):
        pass

    @dsp
    def bar(x: Base[int]) -> str:
        return "base"

    assert bar(Base[int]()) == "base"
    assert bar(Derived[int]()) == "base"

    with pytest.raises(NoMatchFound):
        bar(Derived[bool]())

    @dsp
    def bar(x: Derived[str]) -> str:
        return "derived"

    assert bar(Base[int]()) == "base"
    assert bar(Derived[int]()) == "base"
    assert bar(Derived[str]()) == "derived"


def test_covariance_nonparam_hierarchy():
    dsp = Dispatch()

    @dsp.covariant(0)
    def foo(x: int | date) -> str:
        return "foo"

    assert foo(1) == "foo"
    assert foo(date.today()) == "foo"
    assert foo(True) == "foo"
    assert foo(datetime.now()) == "foo"

    T = TypeVar("T")

    @dataclass
    class Base(Generic[T]):
        pass

    @dataclass
    class Derived(Base[T]):
        pass

    @dsp.covariant(0)
    def bar(x: Base[int]) -> str:
        return "base"

    assert bar(Base[int]()) == "base"
    assert bar(Derived[int]()) == "base"
    assert bar(Derived[bool]()) == "base"

    @dsp.covariant(0)
    def bar(x: Derived[bool]) -> str:
        return "derived"

    assert bar(Base[int]()) == "base"
    assert bar(Derived[int]()) == "base"
    assert bar(Derived[bool]()) == "derived"


def test_invariance_multiple_type_params():
    dsp = Dispatch()

    @dataclass
    class Foo(Generic[TypeVar("U"), TypeVar("V")]):
        pass

    @dsp
    def foo(x: Foo[int, date]) -> str:
        return "foo"

    assert foo(Foo[int, date]()) == "foo"

    with pytest.raises(NoMatchFound):
        foo(Foo[bool, date]())

    with pytest.raises(NoMatchFound):
        foo(Foo[int, datetime]())


def test_covariance_multiple_type_params():
    dsp = Dispatch()

    @dataclass
    class Foo(Generic[TypeVar("U"), TypeVar("V")]):
        pass

    @dsp.covariant(0, 1)
    def foo(x: Foo[int, date]) -> str:
        return "foo"

    assert foo(Foo[int, date]()) == "foo"
    assert foo(Foo[bool, date]()) == "foo"
    assert foo(Foo[int, datetime]()) == "foo"


def test_mixed_variance_hierarchy():
    dsp = Dispatch()

    @dataclass
    class Foo(Generic[TypeVar("T")]):
        pass

    @dsp
    def foo(x: Foo[int | str]) -> str:
        return "union"

    assert foo(Foo[int | str]()) == "union"

    with pytest.raises(NoMatchFound):
        foo(Foo[bool]())

    with pytest.raises(NoMatchFound):
        foo(Foo[int]())

    with pytest.raises(NoMatchFound):
        foo(Foo[str]())

    @dsp.covariant(0)
    def foo(x: Foo[object]) -> str:
        return "object"

    assert foo(Foo[int | str]()) == "union"
    assert foo(Foo[bool]()) == "object"
    assert foo(Foo[int]()) == "object"
    assert foo(Foo[str]()) == "object"

    @dsp.covariant(0)
    def foo(x: Foo[bool]) -> str:
        return "bool"

    assert foo(Foo[int | str]()) == "union"
    assert foo(Foo[bool]()) == "bool"
    assert foo(Foo[int]()) == "object"
    assert foo(Foo[str]()) == "object"

    @dsp.covariant(0)
    def foo(x: Foo[str]) -> str:
        return "str"

    assert foo(Foo[int | str]()) == "union"
    assert foo(Foo[bool]()) == "bool"
    assert foo(Foo[int]()) == "object"
    assert foo(Foo[str]()) == "str"


def test_mixed_variance_hierarchy_ambiguity():
    dsp = Dispatch()

    class BaseA:
        pass

    class BaseB:
        pass

    class Derived(BaseA, BaseB):
        pass

    class DerivedDerived(Derived):
        pass

    class Box(Generic[TypeVar("T")]):
        pass

    @dsp.covariant(0)
    def foo(x: Box[BaseA]):
        return "BaseA"

    @dsp.covariant(0)
    def foo(x: Box[BaseB]):
        return "BaseB"

    @dsp
    def foo(x: Box[Derived]):
        return "Derived"

    with pytest.raises(MultipleMatchesFound):
        foo(Box[DerivedDerived]())


def test_invariance_overlapped_unions():
    dsp = Dispatch()

    @dataclass
    class Foo(Generic[TypeVar("T")]):
        pass

    @dsp
    def foo(x: Foo[int | str]) -> str:
        return "int | str"

    @dsp
    def foo(x: Foo[str | float]) -> str:
        return "str | float"

    assert foo(Foo[int | str]()) == "int | str"
    assert foo(Foo[str | float]()) == "str | float"

    with pytest.raises(NoMatchFound):
        foo(Foo[int]())

    with pytest.raises(NoMatchFound):
        foo(Foo[str]())


def test_covariance_overlapped_unions():
    dsp = Dispatch()

    @dataclass
    class Foo(Generic[TypeVar("T")]):
        pass

    @dsp.covariant(0)
    def foo(x: Foo[int | str]) -> str:
        return "int | str"

    @dsp.covariant(0)
    def foo(x: Foo[str | set]) -> str:
        return "str | set"

    assert foo(Foo[int | str]()) == "int | str"
    assert foo(Foo[str | set]()) == "str | set"
    assert foo(Foo[int]()) == "int | str"
    assert foo(Foo[set]()) == "str | set"

    with pytest.raises(MultipleMatchesFound):
        foo(Foo[str]())


def test_mixed_variance_hierarchy_overlapped_unions():
    dsp = Dispatch()

    @dataclass
    class Foo(Generic[TypeVar("T")]):
        pass

    @dsp.covariant(0)
    def foo(x: Foo[int | str]) -> str:
        return "int | str"

    @dsp
    def foo(x: Foo[str | float]) -> str:
        return "str | float"

    assert foo(Foo[int | str]()) == "int | str"
    assert foo(Foo[str | float]()) == "str | float"
    assert foo(Foo[int]()) == "int | str"
    assert foo(Foo[str]()) == "int | str"


def test_invariance_generics_equivalence():
    dsp = Dispatch()

    T = TypeVar("T")

    @dataclass
    class Foo(Generic[T]):
        pass

    @dsp
    def foo(x: Foo[str | int]) -> str:
        return "union"

    assert foo(Foo[str | int]()) == "union"
    assert foo(Foo[int | str]()) == "union"

    @dsp
    def foo(x: Foo[str | None]) -> str:
        return "optional"

    assert foo(Foo[str | None]()) == "optional"
    assert foo(Foo[None | str]()) == "optional"
    assert foo(Foo[Optional[str]]()) == "optional"

    @dsp
    def foo(x: Foo[Literal[2, 1]]) -> str:
        return "literal"

    assert foo(Foo[Literal[2, 1]]()) == "literal"
    assert foo(Foo[Literal[1, 2]]()) == "literal"

    @dsp
    def bar(x: Foo[str] | Foo[int]) -> str:
        return "v1"

    @dsp
    def bar(x: Foo[int] | Foo[str]) -> str:
        return "v2"

    assert bar(Foo[str]()) == "v2"
    assert bar(Foo[int]()) == "v2"

    @dsp
    def baz(x: Foo[dict[str | int, list[Literal[2, 1]]]]) -> str:
        return "nested"

    assert baz(Foo[dict[str | int, list[Literal[2, 1]]]]()) == "nested"
    assert baz(Foo[dict[int | str, list[Literal[1, 2]]]]()) == "nested"


def test_covariance_generics_equivalence():
    dsp = Dispatch()

    T = TypeVar("T")

    @dataclass
    class Foo(Generic[T]):
        pass

    @dsp.covariant(0)
    def foo(x: Foo[str | int]) -> str:
        return "union"

    assert foo(Foo[str | int]()) == "union"
    assert foo(Foo[int | str]()) == "union"
    assert foo(Foo[bool | str]()) == "union"
    assert foo(Foo[str | bool]()) == "union"

    @dsp.covariant(0)
    def foo(x: Foo[str | None]) -> str:
        return "optional"

    assert foo(Foo[str | None]()) == "optional"
    assert foo(Foo[None | str]()) == "optional"
    assert foo(Foo[Optional[str]]()) == "optional"

    @dsp.covariant(0)
    def foo(x: Foo[Literal[2, 1]]) -> str:
        return "literal"

    assert foo(Foo[Literal[2, 1]]()) == "literal"
    assert foo(Foo[Literal[1, 2]]()) == "literal"

    @dsp.covariant(0)
    def bar(x: Foo[str] | Foo[int]) -> str:
        return "v1"

    @dsp.covariant(0)
    def bar(x: Foo[int] | Foo[str]) -> str:
        return "v2"

    assert bar(Foo[str]()) == "v2"
    assert bar(Foo[int]()) == "v2"

    @dsp.covariant(0)
    def baz(x: Foo[dict[str | int, list[Literal[2, 1]]]]) -> str:
        return "nested"

    assert baz(Foo[dict[str | int, list[Literal[2, 1]]]]()) == "nested"
    assert baz(Foo[dict[int | str, list[Literal[1, 2]]]]()) == "nested"


def test_invariance_any_bare_equivalence():
    dsp = Dispatch()

    T = TypeVar("T")

    @dataclass
    class Box(Generic[T]):
        value: T

    @dsp
    def foo(x: Box[int]) -> str:
        return "int"

    @dsp
    def foo(x: Box[str]) -> str:
        return "str"

    @dsp
    def foo(x: Box) -> str:
        return "bare"

    assert foo(Box(1.0)) == "bare"
    assert foo(Box[Any](1.0)) == "bare"
    assert foo(Box[object](1.0)) == "bare"
    assert foo(Box[float](1.0)) == "bare"
    assert foo(Box[int](1)) == "int"
    assert foo(Box[str]("a")) == "str"

    @dsp
    def foo(x: Box[Any]) -> str:
        return "any"

    assert foo(Box(1.0)) == "any"
    assert foo(Box[Any](1.0)) == "any"
    assert foo(Box[object](1.0)) == "any"
    assert foo(Box[float](1.0)) == "any"
    assert foo(Box[int](1)) == "int"
    assert foo(Box[str]("a")) == "str"

    @dsp
    def foo(x: Box[object]) -> str:
        return "object"

    assert foo(Box(1.0)) == "any"
    assert foo(Box[Any](1.0)) == "any"
    assert foo(Box[object](1.0)) == "object"
    assert foo(Box[float](1.0)) == "any"
    assert foo(Box[int](1)) == "int"
    assert foo(Box[str]("a")) == "str"


def test_covariance_any_bare_equivalence():
    dsp = Dispatch()

    T = TypeVar("T")

    @dataclass
    class Box(Generic[T]):
        value: T

    @dsp.covariant(0)
    def foo(x: Box[int]) -> str:
        return "int"

    @dsp.covariant(0)
    def foo(x: Box[str]) -> str:
        return "str"

    @dsp.covariant(0)
    def foo(x: Box) -> str:
        return "bare"

    assert foo(Box(1.0)) == "bare"
    assert foo(Box[Any](1.0)) == "bare"
    assert foo(Box[object](1.0)) == "bare"
    assert foo(Box[float](1.0)) == "bare"
    assert foo(Box[int](1)) == "int"
    assert foo(Box[str]("a")) == "str"

    @dsp.covariant(0)
    def foo(x: Box[Any]) -> str:
        return "any"

    assert foo(Box(1.0)) == "any"
    assert foo(Box[Any](1.0)) == "any"
    assert foo(Box[object](1.0)) == "any"
    assert foo(Box[float](1.0)) == "any"
    assert foo(Box[int](1)) == "int"
    assert foo(Box[str]("a")) == "str"

    @dsp.covariant(0)
    def foo(x: Box[object]) -> str:
        return "object"

    assert foo(Box(1.0)) == "any"
    assert foo(Box[Any](1.0)) == "any"
    assert foo(Box[object](1.0)) == "object"
    assert foo(Box[float](1.0)) == "object"
    assert foo(Box[int](1)) == "int"
    assert foo(Box[str]("a")) == "str"


def test_dispatch_without_call():
    dsp = Dispatch()

    @dsp
    def foo(x: int) -> int:
        return x * 10

    @dsp
    def foo(x: str) -> str:
        return x.upper()

    methods = dsp["foo"].dispatch(int)
    assert methods
    assert methods[0](1) == 10

    methods = dsp["foo"].dispatch(str)
    assert methods
    assert methods[0]("a") == "A"
    assert methods[0]("a") == "A"

    methods = dsp["foo"].dispatch(complex)
    assert not methods


def test_newtype_toplevel_hint_rejection():
    dsp = Dispatch()

    Int = NewType("Int", int)

    with pytest.raises(TypeError):

        @dsp
        def foo(x: Int) -> None:
            pass


def test_builtin_container_toplevel_hint_rejection():
    dsp = Dispatch()

    with pytest.raises(TypeError):

        @dsp
        def foo(x: list[int]) -> None:
            pass

    with pytest.raises(TypeError):

        @dsp
        def foo(x: list[list[int]]) -> None:
            pass

    with pytest.raises(TypeError):

        @dsp
        def foo(x: Sequence[int]) -> None:
            pass

    class Foo(TypedDict):
        pass

    with pytest.raises(TypeError):

        @dsp
        def foo(x: Foo):
            pass

    with pytest.raises(TypeError):

        @dsp
        def foo(x: tuple[int]) -> None:
            pass

    with pytest.raises(TypeError):

        @dsp
        def foo(x: tuple[int, ...]) -> None:
            pass

    @dsp
    def foo(x: tuple[Any, ...]) -> None:
        pass

    @dsp
    def foo(x: tuple) -> None:
        pass

    @dsp
    def foo(x: list[Any]) -> None:
        pass

    @dsp
    def foo(x: list) -> None:
        pass

    @dsp
    def foo(x: Sequence[Any]) -> None:
        pass

    @dsp
    def foo(x: Sequence) -> None:
        pass

    class Foo(Generic[TypeVar("T")]):
        pass

    @dsp
    def foo(x: Foo[list[int]]) -> None:
        pass


def test_frozen_slotted_generic_toplevel_hint_rejection():
    dsp = Dispatch()

    T = TypeVar("T")

    @dataclass(frozen=True)
    class FrozenBox(Generic[T]):
        value: T

    @dataclass(slots=True)
    class SlottedBox(Generic[T]):
        value: T

    @dataclass
    class RegularBox(Generic[T]):
        value: T

    class ManualSlots(Generic[T]):
        __slots__ = ("value",)

        def __init__(self, value: T) -> None:
            self.value = value

    class SlotsWithOrig(Generic[T]):
        __slots__ = ("value", "__orig_class__")

        def __init__(self, value: T) -> None:
            self.value = value

    class SlotsWithDict(Generic[T]):
        __slots__ = ("value", "__dict__")

        def __init__(self, value: T) -> None:
            self.value = value

    @dataclass(frozen=True)
    class Point:
        x: float
        y: float

    sentinel = object()

    # Python 3.11~3.14 don't set `__orig_class__` for these types.
    # If a later version sets it, this test will fail.
    for cls in (FrozenBox, SlottedBox, ManualSlots, SlotsWithOrig, SlotsWithDict, RegularBox):
        alias = cast(Any, cls)[int]
        instance = alias(sentinel)
        actually_cannot = getattr(instance, "__orig_class__", None) is None
        assert _cannot_set_orig_class(cls) == actually_cannot, cls

    # frozen dataclass generic — parameterized with non-Any → rejected
    with pytest.raises(TypeError):

        @dsp
        def foo(x: FrozenBox[int]) -> None:
            pass

    # slotted dataclass generic — parameterized with non-Any → rejected
    with pytest.raises(TypeError):

        @dsp
        def foo(x: SlottedBox[int]) -> None:
            pass

    # manual __slots__ without __orig_class__ — rejected
    with pytest.raises(TypeError):

        @dsp
        def foo(x: ManualSlots[int]) -> None:
            pass

    # union member: FrozenBox[int] inside union → rejected (recursive validation)
    with pytest.raises(TypeError):

        @dsp
        def foo(x: FrozenBox[int] | int) -> None:
            pass

    # FrozenBox[Any] → allowed (all-Any args)
    @dsp
    def foo(x: FrozenBox[Any]) -> None:
        pass

    # bare FrozenBox → allowed (get_origin is None)
    @dsp
    def foo(x: FrozenBox) -> None:
        pass

    # non-generic frozen dataclass (Point) → allowed (get_origin is None)
    @dsp
    def foo(x: Point) -> None:
        pass

    # regular generic dataclass → allowed
    @dsp
    def foo(x: RegularBox[int]) -> None:
        pass

    # slots with __orig_class__ declared → allowed
    @dsp
    def foo(x: SlotsWithOrig[int]) -> None:
        pass

    # slots with __dict__ declared → allowed
    @dsp
    def foo(x: SlotsWithDict[int]) -> None:
        pass


def test_partially_applied():
    dsp = Dispatch()

    @dsp
    def foo(x: int, y: str, z: str) -> str:
        return "int, str, str"

    @dsp
    def foo(x: int, y: str, z: float) -> str:
        return "int, str, float"

    @dsp
    def foo(x: int, y: str, z: int) -> str:
        return "int, str, int"

    @dsp
    def foo(x: int, y: str, z: int | date) -> str:
        return "int, str, int|date"

    @dsp
    def foo(x: int, y: str, z: set | date) -> str:
        return "int, str, set|date"

    @dsp
    def foo(x: int, y: list, z: str) -> str:
        return "int, list, str"

    partials = {m.signature for m in foo.partial_dispatch(int, str)}
    assert partials == {
        (int, str, str),
        (int, str, float),
        (int, str, int),
        (int, str, int | date),
        (int, str, set | date),
    }

    partials = {m.signature for m in foo.partial_dispatch(int, list)}
    assert partials == {(int, list, str)}

    partials = {m.signature for m in foo.partial_dispatch(int, str, str)}
    assert partials == {(int, str, str)}

    partials = {m.signature for m in foo.partial_dispatch(int, float)}
    assert partials == set()

    partials = {m.signature for m in foo.partial_dispatch(int, str, complex)}
    assert partials == set()


AliasInt = TypeAliasType("AliasInt", int)


def test_dispatch_on_type_alias_collapses_with_underlying():
    dsp = Dispatch()

    @dsp
    def foo(x: type[int]) -> str:
        return "int"

    assert foo(AliasInt) == "int"
    assert foo(int) == "int"


def test_dispatch_on_type_alias_toplevel_hint():
    dsp = Dispatch()

    @dsp
    def foo(x: AliasInt) -> str:
        return "matched"

    assert foo(5) == "matched"


T = TypeVar("T")
AliasList = TypeAliasType("AliasList", list[T], type_params=(T,))


def test_dispatch_on_parameterized_type_alias():
    dsp = Dispatch()

    @dsp
    def foo(x: type[list[int]]) -> str:
        return "list[int]"

    @dsp
    def foo(x: type[list[str]]) -> str:
        return "list[str]"

    assert foo(AliasList[int]) == "list[int]"
    assert foo(AliasList[str]) == "list[str]"
    assert foo(list[int]) == "list[int]"


AliasA = TypeAliasType("AliasA", int)
AliasB = TypeAliasType("AliasB", AliasA)


def test_dispatch_on_type_alias_transitive_chain():
    dsp = Dispatch()

    @dsp
    def foo(x: type[int]) -> str:
        return "int"

    assert foo(AliasB) == "int"


def test_variance_mode_conflict():
    dsp = Dispatch()

    @dsp
    def foo(x: int, y: str) -> None:
        pass

    @dsp
    def foo(x: str, y: int) -> None:
        pass

    with pytest.raises(TypeError):

        @dsp.covariant(0)
        def foo(x: int) -> None:
            pass

    with pytest.raises(TypeError):

        @dsp.covariant(1)
        def foo(x: int, y: str) -> None:
            pass
