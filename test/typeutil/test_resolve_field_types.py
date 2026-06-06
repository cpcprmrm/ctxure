import sys
from dataclasses import dataclass
from typing import Any, Generic, TypeVar, Union

from ctxure._typeutil import resolve_field_types


def test_simple_parameterized_generic():
    T = TypeVar("T")

    @dataclass
    class Foo(Generic[T]):
        foo: T

    field_types = resolve_field_types(Foo[int])
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"foo": int}

    field_types = resolve_field_types(Foo[list[int]])
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"foo": list[int]}


def test_unparameterized_generic():
    T = TypeVar("T")

    @dataclass
    class Foo(Generic[T]):
        foo: T

    field_types = resolve_field_types(Foo)
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"foo": Any}


def test_non_generic_class():
    @dataclass
    class Bar:
        bar1: int
        bar2: str

    field_types = resolve_field_types(Bar)
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"bar1": int, "bar2": str}


def test_mix_generic_and_nongeneric():
    T = TypeVar("T")

    @dataclass
    class Base:
        base: int

    @dataclass
    class Derived(Base, Generic[T]):
        derived: T

    field_types = resolve_field_types(Derived[str])
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"base": int, "derived": str}


def test_multiple_type_parameters():
    S = TypeVar("S")
    T = TypeVar("T")

    @dataclass
    class Foo(Generic[S, T]):
        foo1: S
        foo2: T
        foo3: str

    field_types = resolve_field_types(Foo[int, list[str]])
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"foo1": int, "foo2": list[str], "foo3": str}


def test_nested_generic():
    T = TypeVar("T")

    @dataclass
    class Foo(Generic[T]):
        foo: list[T]

    field_types = resolve_field_types(Foo[int])
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"foo": list[int]}

    field_types = resolve_field_types(Foo)
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"foo": list[Any]}


def test_complex_nested_types():
    T = TypeVar("T")

    @dataclass
    class Foo(Generic[T]):
        foo: dict[str, list[T]]

    field_types = resolve_field_types(Foo[int])
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"foo": dict[str, list[int]]}

    field_types = resolve_field_types(Foo)
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"foo": dict[str, list[Any]]}


def test_simple_inheritance():
    T = TypeVar("T")

    @dataclass
    class Base(Generic[T]):
        base: T

    @dataclass
    class Derived(Base[T], Generic[T]):
        derived: T

    field_types = resolve_field_types(Derived[str])
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"base": str, "derived": str}


def test_inheritance_with_parameterized_base():
    T = TypeVar("T")

    @dataclass
    class Base(Generic[T]):
        base: T

    @dataclass
    class Derived(Base[int]):
        derived: str

    field_types = resolve_field_types(Derived)
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"base": int, "derived": str}


def test_inheritance_with_parameterized_parameterized_base():
    T = TypeVar("T")

    @dataclass
    class Base(Generic[T]):
        base: T

    @dataclass
    class Derived(Base[list[int]]):
        derived: str

    field_types = resolve_field_types(Derived)
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"base": list[int], "derived": str}


def test_inheritance_with_type_transformation_1():
    T = TypeVar("T")
    U = TypeVar("U")

    @dataclass
    class Base(Generic[T]):
        foo: T

    @dataclass
    class Derived(Base[list[U]], Generic[U]):
        bar: U

    field_types = resolve_field_types(Derived[int])
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"foo": list[int], "bar": int}


def test_inheritance_with_type_transformation_2():
    T = TypeVar("T")

    @dataclass
    class Base(Generic[T]):
        foo: T

    @dataclass
    class Derived(Base[list[T]]):
        bar: T

    field_types = resolve_field_types(Derived[int])
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"foo": list[int], "bar": int}


def test_inheritance_with_type_transformation_3():
    T = TypeVar("T")
    S = TypeVar("S")
    U = TypeVar("U")

    @dataclass
    class Base(Generic[T]):
        foo: T

    @dataclass
    class Derived(Base[dict[S, U]], Generic[S, U]):
        bar: S
        baz: U

    field_types = resolve_field_types(Derived[str, int])
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"foo": dict[str, int], "bar": str, "baz": int}


def test_inheritance_with_type_transformation_4():
    T = TypeVar("T")
    S = TypeVar("S")
    U = TypeVar("U")

    @dataclass
    class Base(Generic[S, T]):
        foo: S
        bar: T

    @dataclass
    class Derived(Base[U, U], Generic[U]):
        pass

    field_types = resolve_field_types(Derived[str])
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"foo": str, "bar": str}


def test_typevar_to_typevar():
    T = TypeVar("T")

    @dataclass
    class Bar(Generic[T]):
        c: T
        d: str

    @dataclass
    class Foo(Generic[T]):
        a: Bar[T]
        b: Bar[T]

    field_types = resolve_field_types(Bar[T])  # type: ignore
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"c": Any, "d": str}


def test_shared_typevar_multiple_bases():
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

    field_types = resolve_field_types(Baz[int])
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"foo": int, "bar": list[int], "baz": int}


def test_field_override():
    T = TypeVar("T")

    @dataclass
    class Base(Generic[T]):
        base_field: T
        shared: T

    @dataclass
    class Derived(Base[list[T]], Generic[T]):
        shared: int  # Override with concrete # type: ignore
        derived_field: T

    field_types = resolve_field_types(Derived[str])
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"base_field": list[str], "shared": int, "derived_field": str}


def test_multiple_field_overrides():
    T = TypeVar("T")
    S = TypeVar("S")

    @dataclass
    class Level1(Generic[T]):
        field1: T
        field2: T

    @dataclass
    class Level2(Level1[list[S]], Generic[S]):
        field2: dict[S, S]  # Override  # type: ignore
        field3: S

    @dataclass
    class Level3(Level2[int]):
        field1: str  # Override with concrete type  # type: ignore
        field4: bool

    field_types = resolve_field_types(Level3)
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"field1": str, "field2": dict[int, int], "field3": int, "field4": bool}


def test_union_with_typevar():
    T = TypeVar("T")

    @dataclass
    class Foo(Generic[T]):
        foo: Union[T, str]

    field_types = resolve_field_types(Foo[int])
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"foo": int | str}


def test_optional_typevar():
    T = TypeVar("T")

    @dataclass
    class Foo(Generic[T]):
        foo: T | None

    field_types = resolve_field_types(Foo[int])
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"foo": int | None}

    field_types = resolve_field_types(Foo)
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"foo": Any | None}


def test_union_with_nested_typevar():
    T = TypeVar("T")

    @dataclass
    class Foo(Generic[T]):
        foo: Union[list[T], dict[str, T], None]

    field_types = resolve_field_types(Foo[int])
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"foo": list[int] | dict[str, int] | None}


def test_variable_length_tuple():
    T = TypeVar("T")

    @dataclass
    class Foo(Generic[T]):
        foo: tuple[T, ...]

    field_types = resolve_field_types(Foo[int])
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"foo": tuple[int, ...]}


def test_diamond_inheritance():
    T = TypeVar("T")

    @dataclass
    class A(Generic[T]):
        a: T

    @dataclass
    class B(A[T]):
        b: T

    @dataclass
    class C(A[T]):
        c: T

    @dataclass
    class D(B[int], C[int]):
        d: int

    field_types = resolve_field_types(D)
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"a": int, "b": int, "c": int, "d": int}


def test_diamond_inheritance_conflicting_type_params():
    """
    MRO priority: B binds A[int], C binds A[str]. B comes first, so A.a resolves to int.
    """

    T = TypeVar("T")

    @dataclass
    class A(Generic[T]):
        a: T

    @dataclass
    class B(A[int]):
        b: int

    @dataclass
    class C(A[str]):
        c: str

    @dataclass
    class D(B, C):  # type: ignore[reportGeneralTypeIssues]
        d: bool

    # MRO: D → B → C → A → object
    field_types = resolve_field_types(D)
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {
        "a": int,  # from B's path (MRO priority), not str from C's path
        "b": int,
        "c": str,
        "d": bool,
    }


def test_ancestor_generic():
    T = TypeVar("T")

    @dataclass
    class A(Generic[T]):
        a: T

    @dataclass
    class B(A[int]):
        pass

    @dataclass
    class C(B):
        c: str

    @dataclass
    class D(C):
        pass

    field_types = resolve_field_types(B)
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"a": int}

    field_types = resolve_field_types(C)
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"a": int, "c": str}

    field_types = resolve_field_types(D)
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"a": int, "c": str}


def test_bare_generic_type():
    T = TypeVar("T")

    @dataclass
    class A(Generic[T]):
        a: T

    @dataclass
    class B(A):
        b: int

    @dataclass
    class C(B):
        pass

    field_types = resolve_field_types(A)
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"a": Any}

    field_types = resolve_field_types(B)
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"a": Any, "b": int}

    field_types = resolve_field_types(C)
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"a": Any, "b": int}


def test_forward_reference_parameter():
    T = TypeVar("T")

    @dataclass
    class A(Generic[T]):
        a: T

    A_B = A["B"]

    class B:
        pass

    # Simulate as if B is defined at module level.
    current_module = sys.modules[__name__]
    current_module.B = B  # type: ignore

    try:
        field_types = resolve_field_types(A_B)
        field_dict = {f.name: t for f, t in field_types}
        assert field_dict == {
            "a": B,
        }
    finally:
        delattr(current_module, "B")


def test_forward_reference_field():
    @dataclass
    class A:
        a: "list[B]"

    class B:
        pass

    T = TypeVar("T")

    @dataclass
    class C(Generic[T]):
        c: "list[T]"

    # Simulate as if B is defined at module level.
    current_module = sys.modules[__name__]
    current_module.B = B  # type: ignore
    current_module.T = T  # type: ignore

    try:
        field_types = resolve_field_types(A)
        field_dict = {f.name: t for f, t in field_types}
        assert field_dict == {
            "a": list[B],
        }

        field_types = resolve_field_types(C[int])
        field_dict = {f.name: t for f, t in field_types}
        assert field_dict == {
            "c": list[int],
        }
    finally:
        delattr(current_module, "B")
        delattr(current_module, "T")


def test_forward_reference_in_base():
    T = TypeVar("T")

    @dataclass
    class Base(Generic[T]):
        a: T

    class Ref:
        pass

    @dataclass
    class Child(Base["Ref"]):
        b: str

    # Simulate as if Ref is defined at module level.
    current_module = sys.modules[__name__]
    current_module.Ref = Ref  # type: ignore

    try:
        field_types = resolve_field_types(Child)
        field_dict = {f.name: t for f, t in field_types}
        assert field_dict == {
            "a": Ref,
            "b": str,
        }
    finally:
        delattr(current_module, "Ref")
