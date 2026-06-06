import sys
from dataclasses import dataclass
from typing import Any, Union

from ctxure._typeutil import resolve_field_types


def test_simple_parameterized_generic():
    @dataclass
    class Foo[T]:
        foo: T

    field_types = resolve_field_types(Foo[int])
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"foo": int}

    field_types = resolve_field_types(Foo[list[int]])
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"foo": list[int]}


def test_unparameterized_generic():
    @dataclass
    class Foo[T]:
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
    @dataclass
    class Base:
        base: int

    @dataclass
    class Derived[T](Base):
        derived: T

    field_types = resolve_field_types(Derived[str])
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"base": int, "derived": str}


def test_multiple_type_parameters():
    @dataclass
    class Foo[S, T]:
        foo1: S
        foo2: T
        foo3: str

    field_types = resolve_field_types(Foo[int, list[str]])
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"foo1": int, "foo2": list[str], "foo3": str}


def test_nested_generic():
    @dataclass
    class Foo[T]:
        foo: list[T]

    field_types = resolve_field_types(Foo[int])
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"foo": list[int]}

    field_types = resolve_field_types(Foo)
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"foo": list[Any]}


def test_complex_nested_types():
    @dataclass
    class Foo[T]:
        foo: dict[str, list[T]]

    field_types = resolve_field_types(Foo[int])
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"foo": dict[str, list[int]]}

    field_types = resolve_field_types(Foo)
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"foo": dict[str, list[Any]]}


def test_simple_inheritance():
    @dataclass
    class Base[T]:
        base: T

    @dataclass
    class Derived[T](Base[T]):
        derived: T

    field_types = resolve_field_types(Derived[str])
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"base": str, "derived": str}


def test_inheritance_with_parameterized_base():
    @dataclass
    class Base[T]:
        base: T

    @dataclass
    class Derived(Base[int]):
        derived: str

    field_types = resolve_field_types(Derived)
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"base": int, "derived": str}


def test_inheritance_with_parameterized_parameterized_base():
    @dataclass
    class Base[T]:
        base: T

    @dataclass
    class Derived(Base[list[int]]):
        derived: str

    field_types = resolve_field_types(Derived)
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"base": list[int], "derived": str}


def test_inheritance_with_type_transformation_1():
    @dataclass
    class Base[T]:
        foo: T

    @dataclass
    class Derived[U](Base[list[U]]):
        bar: U

    field_types = resolve_field_types(Derived[int])
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"foo": list[int], "bar": int}


def test_inheritance_with_type_transformation_2():
    @dataclass
    class Base[T]:
        foo: T

    @dataclass
    class Derived[T](Base[list[T]]):
        bar: T

    field_types = resolve_field_types(Derived[int])
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"foo": list[int], "bar": int}


def test_inheritance_with_type_transformation_3():
    @dataclass
    class Base[T]:
        foo: T

    @dataclass
    class Derived[S, T](Base[dict[S, T]]):
        bar: S
        baz: T

    field_types = resolve_field_types(Derived[str, int])
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"foo": dict[str, int], "bar": str, "baz": int}


def test_inheritance_with_type_transformation_4():
    @dataclass
    class Base[S, T]:
        foo: S
        bar: T

    @dataclass
    class Derived[U](Base[U, U]):
        pass

    field_types = resolve_field_types(Derived[str])
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"foo": str, "bar": str}


def test_multi_level_inheritance():
    @dataclass
    class Level1[T]:
        l1: T

    @dataclass
    class Level2[T](Level1[T]):
        l2: T

    @dataclass
    class Level3[T](Level2[T]):
        l3: T

    field_types = resolve_field_types(Level3[int])
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"l1": int, "l2": int, "l3": int}


def test_nested_transformation():
    @dataclass
    class Base[T]:
        foo: T

    @dataclass
    class Middle[T](Base[list[T]]):
        bar: T

    @dataclass
    class Final[T](Middle[dict[str, T]]):
        baz: T

    field_types = resolve_field_types(Final[int])
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"foo": list[dict[str, int]], "bar": dict[str, int], "baz": int}


def test_field_override():
    @dataclass
    class Base[T]:
        base_field: T
        shared: T

    @dataclass
    class Derived[T](Base[list[T]]):
        shared: int  # Override with concrete type  # type: ignore
        derived_field: T

    field_types = resolve_field_types(Derived[str])
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"base_field": list[str], "shared": int, "derived_field": str}


def test_multiple_field_overrides():
    @dataclass
    class Level1[T]:
        field1: T
        field2: T

    @dataclass
    class Level2[S](Level1[list[S]]):
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
    @dataclass
    class Foo[T]:
        foo: Union[T, str]

    field_types = resolve_field_types(Foo[int])
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"foo": int | str}


def test_optional_typevar():
    @dataclass
    class Foo[T]:
        foo: T | None

    field_types = resolve_field_types(Foo[int])
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"foo": int | None}

    field_types = resolve_field_types(Foo)
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"foo": Any | None}


def test_union_with_nested_typevar():
    @dataclass
    class Foo[T]:
        foo: Union[list[T], dict[str, T], None]

    field_types = resolve_field_types(Foo[int])
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"foo": list[int] | dict[str, int] | None}


def test_variable_length_tuple():
    @dataclass
    class Foo[T]:
        foo: tuple[T, ...]

    field_types = resolve_field_types(Foo[int])
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"foo": tuple[int, ...]}


def test_diamond_inheritance():
    @dataclass
    class A[T]:
        a: T

    @dataclass
    class B[T](A[T]):
        b: T

    @dataclass
    class C[T](A[T]):
        c: T

    @dataclass
    class D(B[int], C[int]):
        d: int

    field_types = resolve_field_types(D)
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {"a": int, "b": int, "c": int, "d": int}


def test_ancestor_generic():
    @dataclass
    class A[T]:
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
    @dataclass
    class A[T]:
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
    @dataclass
    class A[T]:
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

    # Simulate as if B is defined at module level.
    current_module = sys.modules[__name__]
    current_module.B = B  # type: ignore

    try:
        field_types = resolve_field_types(A)
        field_dict = {f.name: t for f, t in field_types}
        assert field_dict == {
            "a": list[B],
        }
    finally:
        delattr(current_module, "B")

    @dataclass
    class C[T]:
        c: "list[T]"

    field_types = resolve_field_types(C[int])
    field_dict = {f.name: t for f, t in field_types}
    assert field_dict == {
        "c": list[int],
    }


def test_forward_reference_in_base():
    """ForwardRef in __orig_bases__: class Child(Base['SomeType'])."""

    @dataclass
    class Base[T]:
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
