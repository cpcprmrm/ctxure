from typing import Any, Generic, TypeVar

from typing_extensions import TypedDict

from ctxure._typeutil import is_nominal_subclass, resolve_typeddict_field_types


def test_simple_nongeneric_typeddict():
    class Foo(TypedDict):
        a: int
        b: str

    assert resolve_typeddict_field_types(Foo) == [("a", int), ("b", str)]


def test_nongeneric_inheritance():
    class Foo(TypedDict):
        a: int

    class Bar(Foo):
        b: str

    # get_type_hints(Bar) returns inherited + own, in declaration order.
    field_dict = dict(resolve_typeddict_field_types(Bar))
    assert field_dict == {"a": int, "b": str}


def test_nongeneric_multi_level_inheritance():
    class L1(TypedDict):
        a: int

    class L2(L1):
        b: str

    class L3(L2):
        c: float

    field_dict = dict(resolve_typeddict_field_types(L3))
    assert field_dict == {"a": int, "b": str, "c": float}


def test_simple_generic_typeddict_parameterized():
    T = TypeVar("T")

    class Foo(TypedDict, Generic[T]):
        a: T

    field_dict = dict(resolve_typeddict_field_types(Foo[int]))
    assert field_dict == {"a": int}

    field_dict = dict(resolve_typeddict_field_types(Foo[list[str]]))
    assert field_dict == {"a": list[str]}


def test_generic_typeddict_unparameterized():
    T = TypeVar("T")

    class Foo(TypedDict, Generic[T]):
        a: T

    field_dict = dict(resolve_typeddict_field_types(Foo))
    assert field_dict == {"a": Any}


def test_generic_inheritance_with_bound_parent():
    T = TypeVar("T")

    class Base(TypedDict, Generic[T]):
        x: T

    class Derived(Base[int]):
        y: str

    field_dict = dict(resolve_typeddict_field_types(Derived))
    assert field_dict == {"x": int, "y": str}


def test_generic_inheritance_with_typevar_passthrough():
    T = TypeVar("T")

    class Base(TypedDict, Generic[T]):
        x: T

    class Derived(Base[T], Generic[T]):
        y: T

    field_dict = dict(resolve_typeddict_field_types(Derived[str]))
    assert field_dict == {"x": str, "y": str}


def test_generic_inheritance_with_nested_typevar():
    T = TypeVar("T")
    U = TypeVar("U")

    class Base(TypedDict, Generic[T]):
        x: T

    class Derived(Base[list[U]], Generic[U]):
        y: U

    field_dict = dict(resolve_typeddict_field_types(Derived[int]))
    assert field_dict == {"x": list[int], "y": int}


def test_multiple_type_parameters():
    K = TypeVar("K")
    V = TypeVar("V")

    class Pair(TypedDict, Generic[K, V]):
        key: K
        value: V

    field_dict = dict(resolve_typeddict_field_types(Pair[str, int]))
    assert field_dict == {"key": str, "value": int}


def test_is_nominal_subclass_dataclass_path():
    # issubclass path for non-TypedDict classes
    class A: ...

    class B(A): ...

    assert is_nominal_subclass(B, A) is True
    assert is_nominal_subclass(A, B) is False
    assert is_nominal_subclass(A, object) is True


def test_is_nominal_subclass_typeddict_nominal():
    class Foo(TypedDict):
        a: int

    class Bar(Foo):
        b: str

    assert is_nominal_subclass(Bar, Foo) is True
    assert is_nominal_subclass(Foo, Bar) is False
    # Self
    assert is_nominal_subclass(Foo, Foo) is True


def test_is_nominal_subclass_typeddict_to_object():
    class Foo(TypedDict):
        a: int

    # TypedDict <: object (universal top)
    assert is_nominal_subclass(Foo, object) is True


def test_is_nominal_subclass_typeddict_not_dict():
    class Foo(TypedDict):
        a: int

    # TypedDict is not a subclass of dict
    assert is_nominal_subclass(Foo, dict) is False


def test_is_nominal_subclass_typeddict_multi_level():
    class L1(TypedDict):
        a: int

    class L2(L1):
        b: str

    class L3(L2):
        c: float

    assert is_nominal_subclass(L3, L1) is True
    assert is_nominal_subclass(L3, L2) is True
    assert is_nominal_subclass(L2, L1) is True
    assert is_nominal_subclass(L1, L3) is False
