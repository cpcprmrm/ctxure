from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Literal, Optional

import pytest

from ctxure.multidispatch import Dispatch, MultipleMatchesFound, NoMatchFound


def test_dispatch_on_type_user_defined_generic():
    dsp = Dispatch()

    @dataclass
    class Box[T]:
        value: T

    @dsp
    def foo(x: type[Box[int]]) -> str:
        return "Box[int]"

    @dsp
    def foo(x: type[Box[str]]) -> str:
        return "Box[str]"

    assert foo(Box[int]) == "Box[int]"
    assert foo(Box[str]) == "Box[str]"


def test_invariance_unary():
    dsp = Dispatch()

    @dataclass
    class Foo[T]:
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

    @dataclass
    class Foo[T]:
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

    @dataclass
    class Foo[T]:
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

    @dataclass
    class Foo[T]:
        value: T
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

    @dataclass
    class Foo[T]:
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

    @dataclass
    class Foo[T]:
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

    @dataclass
    class Foo[T]:
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

    @dataclass
    class Base[T]:
        pass

    @dataclass
    class Derived[T](Base[T]):
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

    @dataclass
    class Base[T]:
        pass

    @dataclass
    class Derived[T](Base[T]):
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
    class Foo[U, V]:
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
    class Foo[U, V]:
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
    class Foo[T]:
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


def test_binary_dispatch_covariant_generic_disambiguate_by_second_arg():
    dsp = Dispatch()

    @dataclass
    class Box[T]:
        pass

    @dsp.covariant(0)
    def foo(x: Box[object], y: str) -> str:
        return "str"

    @dsp.covariant(0)
    def foo(x: Box[object], y: int) -> str:
        return "int"

    assert foo(Box[int](), "a") == "str"
    assert foo(Box[int](), 1) == "int"


def test_mixed_variance_hierarchy_ambiguity():
    dsp = Dispatch()

    class BaseA: ...

    class BaseB: ...

    class Derived(BaseA, BaseB): ...

    class DerivedDerived(Derived): ...

    class Box[T]: ...

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
    class Foo[T]:
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
    class Foo[T]:
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
    class Foo[T]:
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

    @dataclass
    class Foo[T]:
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

    @dataclass
    class Foo[T]:
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

    @dataclass
    class Box[T]:
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

    @dataclass
    class Box[T]:
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


type AliasInt = int


def test_dispatch_on_type_alias_sugar():
    dsp = Dispatch()

    @dsp
    def foo(x: type[int]) -> str:
        return "int"

    assert foo(AliasInt) == "int"
    assert foo(int) == "int"


type SwapDict[K, V] = dict[V, K]


def test_dispatch_on_parameterized_alias_with_reordering():
    dsp = Dispatch()

    @dsp
    def foo(x: type[dict[int, str]]) -> str:
        return "dict[int, str]"

    @dsp
    def foo(x: type[dict[str, int]]) -> str:
        return "dict[str, int]"

    assert foo(SwapDict[str, int]) == "dict[int, str]"
    assert foo(SwapDict[int, str]) == "dict[str, int]"


type Tree = list[Tree]


def test_dispatch_on_recursive_type_alias():
    dsp = Dispatch()

    @dsp
    def foo(x: type[list]) -> str:
        return "list"

    assert foo(Tree) == "list"
    assert foo(list) == "list"


type X = Y
type Y = int


def test_dispatch_on_transitive_type_alias_chain():
    dsp = Dispatch()

    @dsp
    def foo(x: type[int]) -> str:
        return "int"

    assert foo(X) == "int"


type A = B  # type: ignore
type B = A


def test_dispatch_on_mutual_cyclic_type_alias_raises():
    dsp = Dispatch()

    @dsp
    def foo(x: type[int]) -> str:
        return "int"

    with pytest.raises(TypeError, match="[Cc]yclic"):
        foo(A)
