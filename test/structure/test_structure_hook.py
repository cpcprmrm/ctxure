from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal, NewType, TypedDict

import pytest
from typing_extensions import TypedDict as ExtTypedDict

from ctxure import (
    AmbiguousUnion,
    Ctx,
    MultipleStructureHooks,
    NoStructureHook,
    Of,
    Under,
    ValidationError,
    ctxure_config,
    get_data,
    get_extra,
    structure,
    structure_by_type,
    structure_default,
)
from ctxure.error import ExtraFields, MissingFields, ReentranceError


def test_structure_hook_local_dispatch(testregister):
    @testregister
    def structure_hook(ctx: Ctx[int], data: int) -> int:
        return data * 10

    with ctxure_config(dispatcher=testregister):
        assert structure(int, 10) == 100

    assert structure(int, 10) == 10


def test_structure_hook_primitive_type_ctx(testregister):
    @dataclass
    class Foo:
        a: int
        b: float

    @testregister
    def structure_hook(ctx: Ctx[int], data: int) -> int:
        return data * 10

    with ctxure_config(dispatcher=testregister):
        assert structure(int, 10) == 100
        assert structure(list[int], [1, 2, 3]) == [10, 20, 30]
        assert structure(tuple[int, float, int], [1, 1.1, 2]) == (10, 1.1, 20)
        assert structure(set[int], [1, 2, 3]) == {10, 20, 30}
        assert structure(frozenset[int], [1, 2, 3]) == frozenset({10, 20, 30})
        assert structure(dict[int, int], {1: 10}) == {10: 100}
        assert structure(Foo, {"a": 1, "b": 1.0}) == Foo(10, 1.0)
        assert structure(list[Foo], [{"a": 1, "b": 1.1}, {"a": 2, "b": 2.1}]) == [Foo(10, 1.1), Foo(20, 2.1)]
        assert structure(list[set[int]], [[1, 2], [3, 4]]) == [{10, 20}, {30, 40}]
        assert structure(Literal[1], 1) == 1


def test_structure_hook_primitive_type_ctx_with_path(testregister):
    @dataclass
    class Foo:
        a: int
        b: float

    @testregister
    def structure_hook(ctx: Ctx[int, "$[0]"], data: int) -> int:
        return data * 10

    with ctxure_config(dispatcher=testregister):
        assert structure(int, 1) == 1
        assert structure(list[int], [1, 2, 3]) == [10, 2, 3]
        assert structure(tuple[int, float, int], [1, 1.1, 2]) == (10, 1.1, 2)
        assert structure(set[int], [1, 2, 3]) == {1, 2, 3}
        assert structure(frozenset[int], [1, 2, 3]) == frozenset({1, 2, 3})
        assert structure(dict[int, int], {0: 10, 1: 20}) == {0: 100, 1: 20}
        assert structure(Foo, {"a": 1, "b": 1.0}) == Foo(1, 1.0)
        assert structure(list[list[int]], [[1, 2], [3, 4]]) == [[1, 2], [3, 4]]

    @testregister
    def structure_hook(ctx: Ctx[int, "$.a"], data: int) -> int:
        return data * 10

    with ctxure_config(dispatcher=testregister):
        assert structure(int, 1) == 1
        assert structure(list[int], [1, 2, 3]) == [10, 2, 3]
        assert structure(tuple[int, float, int], [1, 1.1, 2]) == (10, 1.1, 2)
        assert structure(set[int], [1, 2, 3]) == {1, 2, 3}
        assert structure(frozenset[int], [1, 2, 3]) == frozenset({1, 2, 3})
        assert structure(dict[int, int], {0: 10, 1: 20}) == {0: 100, 1: 20}
        assert structure(Foo, {"a": 1, "b": 1.0}) == Foo(10, 1.0)
        assert structure(list[list[int]], [[1, 2], [3, 4]]) == [[1, 2], [3, 4]]


def test_structure_hook_primitive_type_ctx_string_coercion(testregister):
    @dataclass
    class Foo:
        a: str

    @testregister
    def structure_hook(ctx: Ctx[str], data: int | float | bool) -> str:
        return str(data)

    with ctxure_config(dispatcher=testregister):
        assert structure(str, 1) == "1"
        assert structure(list[str], [1, 2, 3]) == ["1", "2", "3"]
        assert structure(tuple[str, str, str], [1, 1.1, True]) == ("1", "1.1", "True")
        assert structure(set[str], [1, False]) == {"1", "False"}
        assert structure(frozenset[str], [1, 1.0]) == frozenset({"1", "1.0"})
        assert structure(dict[str, str], {1: 10}) == {"1": "10"}
        assert structure(Foo, {"a": 1}) == Foo("1")
        assert structure(list[Foo], [{"a": 1}, {"a": 2}]) == [Foo("1"), Foo("2")]
        assert structure(list[set[str]], [[1, 2], [3, 4]]) == [{"1", "2"}, {"3", "4"}]


def test_structure_hook_list_type_ctx(testregister):
    @dataclass(frozen=True)
    class Foo:
        a: list[int]

    @testregister
    def structure_hook(ctx: Ctx[list[int]], data: list) -> list[int]:
        r = structure_default(ctx, data)
        r[-1] *= 10
        return r

    with ctxure_config(dispatcher=testregister):
        assert structure(list[int], [1, 2]) == [1, 20]
        assert structure(list[list[int]], [[1, 2], [3, 4]]) == [[1, 20], [3, 40]]
        assert structure(Foo, {"a": [1, 2]}) == Foo([1, 20])
        assert structure(tuple[Foo, Foo], [{"a": [1, 2]}, {"a": [3]}]) == (Foo([1, 20]), Foo([30]))


def test_structure_hook_list_type_ctx_with_path(testregister):
    @dataclass(frozen=True)
    class Foo:
        a: list[int]

    @testregister
    def structure_hook(ctx: Ctx[list[int], "$[1]"], data: list) -> list[int]:
        r = structure_default(ctx, data)
        r[-1] *= 10
        return r

    with ctxure_config(dispatcher=testregister):
        assert structure(list[int], [1, 2]) == [1, 2]
        assert structure(list[list[int]], [[1, 2], [3, 4]]) == [[1, 2], [3, 40]]
        assert structure(Foo, {"a": [1, 2]}) == Foo([1, 2])
        assert structure(tuple[Foo, Foo], [{"a": [1, 2]}, {"a": [3]}]) == (Foo([1, 2]), Foo([3]))

    @testregister
    def structure_hook(ctx: Ctx[list[int], "$"], data: list) -> list[int]:
        r = structure_default(ctx, data)
        r[-1] = 0
        return r

    with ctxure_config(dispatcher=testregister):
        assert structure(list[int], [1, 2]) == [1, 0]
        assert structure(list[list[int]], [[1, 2], [3, 4]]) == [[1, 2], [3, 40]]
        assert structure(Foo, {"a": [1, 2]}) == Foo([1, 2])
        assert structure(tuple[Foo, Foo], [{"a": [1, 2]}, {"a": [3]}]) == (Foo([1, 2]), Foo([3]))

    @testregister
    def structure_hook(ctx: Ctx[list[int], "$[0].a"], data: list) -> list[int]:
        r = structure_default(ctx, data)
        r[-1] *= 100
        return r

    with ctxure_config(dispatcher=testregister):
        assert structure(list[int], [1, 2]) == [1, 0]
        assert structure(list[list[int]], [[1, 2], [3, 4]]) == [[1, 2], [3, 40]]
        assert structure(Foo, {"a": [1, 2]}) == Foo([1, 2])
        assert structure(tuple[Foo, Foo], [{"a": [1, 2]}, {"a": [3]}]) == (Foo([1, 200]), Foo([3]))


def test_structure_hook_dataclass_ctx(testregister):
    @dataclass
    class Foo:
        a: str
        b: int

    @dataclass
    class Bar:
        f: Foo

    @testregister
    def structure_hook(ctx: Ctx[Foo], data: dict) -> Foo:
        return Foo(data["a"], data["b"] * 10)

    with ctxure_config(dispatcher=testregister):
        assert structure(Foo, {"a": "x", "b": 1}) == Foo("x", 10)
        assert structure(list[Foo], [{"a": "x", "b": 1}, {"a": "y", "b": 2}]) == [Foo("x", 10), Foo("y", 20)]
        assert structure(Bar, {"f": {"a": "x", "b": 1}}) == Bar(Foo("x", 10))
        assert structure(tuple[Bar, Bar], [{"f": {"a": "x", "b": 1}}, {"f": {"a": "y", "b": 2}}]) == (
            Bar(Foo("x", 10)),
            Bar(Foo("y", 20)),
        )


def test_structure_hook_field(testregister):
    @dataclass
    class Foo:
        a: int
        b: int

    @dataclass
    class Bar:
        a: int

    @testregister
    def structure_hook(ctx: Ctx[".a"], data: int) -> int:
        return data * 10

    with ctxure_config(dispatcher=testregister):
        assert structure(Foo, {"a": 1, "b": 2}) == Foo(10, 2)
        assert structure(Bar, {"a": 3}) == Bar(30)
        assert structure(list[Foo], [{"a": 1, "b": 2}]) == [Foo(10, 2)]
        assert structure(list[Bar], [{"a": 3}]) == [Bar(30)]

    @testregister
    def structure_hook(ctx: Ctx[".a", Of[Foo]], data: int) -> int:
        return data * 100

    with ctxure_config(dispatcher=testregister):
        assert structure(Foo, {"a": 1, "b": 2}) == Foo(100, 2)
        assert structure(Bar, {"a": 3}) == Bar(30)
        assert structure(list[Foo], [{"a": 1, "b": 2}]) == [Foo(100, 2)]
        assert structure(list[Bar], [{"a": 3}]) == [Bar(30)]

    # Never fires, as the target type does not match
    @testregister
    def structure_hook(ctx: Ctx[".a", Of[Foo], str], data: int) -> int:
        return data * 1000

    with ctxure_config(dispatcher=testregister):
        assert structure(Foo, {"a": 1, "b": 2}) == Foo(100, 2)
        assert structure(Bar, {"a": 3}) == Bar(30)
        assert structure(list[Foo], [{"a": 1, "b": 2}]) == [Foo(100, 2)]
        assert structure(list[Bar], [{"a": 3}]) == [Bar(30)]

    @testregister
    def structure_hook(ctx: Ctx[".a", Of[Foo], int], data: int) -> int:
        return data * 1000

    with ctxure_config(dispatcher=testregister):
        assert structure(Foo, {"a": 1, "b": 2}) == Foo(1000, 2)
        assert structure(Bar, {"a": 3}) == Bar(30)
        assert structure(list[Foo], [{"a": 1, "b": 2}]) == [Foo(1000, 2)]
        assert structure(list[Bar], [{"a": 3}]) == [Bar(30)]

    @testregister
    def structure_hook(ctx: Ctx[".b", Of[Foo]], data: int) -> int:
        return -1

    @testregister
    def structure_hook(ctx: Ctx[".b", int], data: int) -> int:
        return -1

    with ctxure_config(dispatcher=testregister):
        assert structure(Bar, {"a": 3}) == Bar(30)
        assert structure(list[Bar], [{"a": 3}]) == [Bar(30)]

        with pytest.raises(MultipleStructureHooks):
            structure(Foo, {"a": 1, "b": 2})


def test_structure_hook_field_wildcard(testregister):
    @dataclass
    class Foo:
        a: int
        b: int

    @dataclass
    class Bar:
        a: int

    @testregister
    def structure_hook(ctx: Ctx[".?"], data: int) -> int:
        return data * 10

    with ctxure_config(dispatcher=testregister):
        assert structure(Foo, {"a": 1, "b": 2}) == Foo(10, 20)
        assert structure(Bar, {"a": 3}) == Bar(30)
        assert structure(list[Foo], [{"a": 1, "b": 2}]) == [Foo(10, 20)]
        assert structure(list[Bar], [{"a": 3}]) == [Bar(30)]

    @testregister
    def structure_hook(ctx: Ctx[".?", Of[Bar]], data: int) -> int:
        return data * 100

    with ctxure_config(dispatcher=testregister):
        assert structure(Foo, {"a": 1, "b": 2}) == Foo(10, 20)
        assert structure(Bar, {"a": 3}) == Bar(300)
        assert structure(list[Foo], [{"a": 1, "b": 2}]) == [Foo(10, 20)]
        assert structure(list[Bar], [{"a": 3}]) == [Bar(300)]


def test_structure_hook_item(testregister):
    @testregister
    def structure_hook(ctx: Ctx["[0]"], data: int | str) -> int | str:
        return data * 10

    with ctxure_config(dispatcher=testregister):
        assert structure(list[int], [1, 2, 3]) == [10, 2, 3]
        assert structure(list[str], ["a"]) == ["aaaaaaaaaa"]
        assert structure(tuple[int, ...], [1, 2, 3]) == (10, 2, 3)
        assert structure(tuple[str, ...], ["a"]) == ("aaaaaaaaaa",)
        assert structure(dict[int, int], {0: 10, 1: 11}) == {0: 100, 1: 11}

    @testregister
    def structure_hook(ctx: Ctx["[0]", str], data: int | str) -> int | str:
        return data * 2

    with ctxure_config(dispatcher=testregister):
        assert structure(list[int], [1, 2, 3]) == [10, 2, 3]
        assert structure(list[str], ["a"]) == ["aa"]
        assert structure(tuple[int, ...], [1, 2, 3]) == (10, 2, 3)
        assert structure(tuple[str, ...], ["a"]) == ("aa",)
        assert structure(dict[int, int], {0: 10, 1: 11}) == {0: 100, 1: 11}

    @testregister
    def structure_hook(ctx: Ctx["[0]", Of[tuple]], data: int | str) -> int | str:
        return data * 100

    with ctxure_config(dispatcher=testregister):
        assert structure(list[int], [1, 2, 3]) == [10, 2, 3]
        assert structure(list[str], ["a"]) == ["aa"]
        assert structure(tuple[int, ...], [1, 2, 3]) == (100, 2, 3)
        assert structure(dict[int, int], {0: 10, 1: 11}) == {0: 100, 1: 11}

        with pytest.raises(MultipleStructureHooks):
            structure(tuple[str, ...], ["a"])

    @testregister
    def structure_hook(ctx: Ctx["[1]", Of[tuple]], data: int | str) -> int | str:
        return data * 1000

    with ctxure_config(dispatcher=testregister):
        assert structure(list[int], [1, 2, 3]) == [10, 2, 3]
        assert structure(list[str], ["a"]) == ["aa"]
        assert structure(tuple[int, ...], [1, 2, 3]) == (100, 2000, 3)
        assert structure(dict[int, int], {0: 10, 1: 11}) == {0: 100, 1: 11}

    @testregister
    def structure_hook(ctx: Ctx["[1]", Of[tuple], int], data: int | str) -> int | str:
        return data * 10000

    with ctxure_config(dispatcher=testregister):
        assert structure(list[int], [1, 2, 3]) == [10, 2, 3]
        assert structure(list[str], ["a"]) == ["aa"]
        assert structure(tuple[int, ...], [1, 2, 3]) == (100, 20000, 3)
        assert structure(dict[int, int], {0: 10, 1: 11}) == {0: 100, 1: 11}


def test_structure_hook_item_wildcard(testregister):
    @testregister
    def structure_hook(ctx: Ctx["[?]"], data: int) -> int:
        return data * 10

    with ctxure_config(dispatcher=testregister):
        assert structure(list[int], [1, 2, 3]) == [10, 20, 30]
        assert structure(dict[int, int], {1: 10, 2: 20}) == {1: 100, 2: 200}

    @testregister
    def structure_hook(ctx: Ctx["[?]", Of[dict]], data: int) -> int:
        return data * 100

    with ctxure_config(dispatcher=testregister):
        assert structure(list[int], [1, 2, 3]) == [10, 20, 30]
        assert structure(dict[int, int], {1: 10, 2: 20}) == {1: 1000, 2: 2000}


def test_structure_hook_key(testregister):
    @testregister
    def structure_hook(ctx: Ctx["[~?]"], data: int | str) -> int | str:
        return data * 3

    with ctxure_config(dispatcher=testregister):
        assert structure(list[int], [1, 2, 3]) == [1, 2, 3]
        assert structure(dict[int, int], {1: 11, 2: 22}) == {3: 11, 6: 22}
        assert structure(dict[str, int], {"a": 11, "b": 22}) == {"aaa": 11, "bbb": 22}

    @testregister
    def structure_hook(ctx: Ctx["[~?]", str], data: str) -> str:
        return data.upper()

    with ctxure_config(dispatcher=testregister):
        assert structure(list[int], [1, 2, 3]) == [1, 2, 3]
        assert structure(dict[int, int], {1: 11, 2: 22}) == {3: 11, 6: 22}
        assert structure(dict[str, int], {"a": 11, "b": 22}) == {"A": 11, "B": 22}


def test_structure_dict_value_context_tracks_current_structured_key(testregister):
    @testregister
    def structure_hook(ctx: Ctx[str, "[~?]"], data: str) -> str:
        return get_extra(ctx)["structured_key"]

    @testregister
    def structure_hook(ctx: Ctx[int, "['a']"], data: int) -> int:  # noqa: F821
        return data + 100

    with ctxure_config(dispatcher=testregister):
        assert structure(dict[str, int], {"x": 1}, extra={"structured_key": "a"}) == {"a": 101}
        assert structure(dict[str, int], {"x": 1}, extra={"structured_key": "b"}) == {"b": 1}
        assert structure(dict[str, int], {"x": 1}, extra={"structured_key": "a"}) == {"a": 101}


def test_structure_dict_key_context_distinguishes_equal_raw_keys(testregister):
    seen = []

    @testregister
    def structure_hook(ctx: Ctx[int, "[~?]"], data: int) -> int:
        seen.append(ctx.unstructured_path)
        return int(data)

    with ctxure_config(dispatcher=testregister):
        assert structure(dict[int, str], {1: "one"}) == {1: "one"}
        assert structure(dict[int, str], {True: "true"}) == {1: "true"}

    assert seen == ["$[~1]", "$[~True]"]


def test_structure_hook_newtype(testregister):
    Int = NewType("Int", int)

    @dataclass
    class Foo:
        a: Int

    @testregister
    def structure_hook(ctx: Ctx[Int], data: int) -> Int:
        return Int(data * 10)

    with ctxure_config(dispatcher=testregister):
        assert structure(int, 1) == 1
        assert structure(Int, 1) == 10
        assert structure(list[int], [1, 2]) == [1, 2]
        assert structure(list[Int], [1, 2]) == [10, 20]
        assert structure(Foo, {"a": 1}) == Foo(Int(10))


def test_structure_hook_newtype_supertype_hook(testregister):
    Complex = NewType("Complex", complex)

    @testregister
    def structure_hook(ctx: Ctx[complex], data: complex) -> complex:
        return data * 10

    with ctxure_config(dispatcher=testregister):
        with pytest.raises(NoStructureHook):
            structure(Complex, 1j)


def test_structure_hook_newtype_supertype_hook_registered_with_ctx_subtypes(testregister):
    Complex = NewType("Complex", complex)

    @testregister.ctx_subtypes
    def structure_hook(ctx: Ctx[complex], data: complex) -> complex:
        return data * 100

    with ctxure_config(dispatcher=testregister):
        assert structure(Complex, 1j) == 100j


def test_structure_hook_literal(testregister):
    @dataclass
    class Foo:
        a: Literal[1, 2]

    @testregister
    def structure_hook(ctx: Ctx[Literal[1, 2]], data: int) -> int:
        if data in [1, 2]:
            return data % 2 + 1
        raise ValidationError(ctx, f"Invalid literal value {data}")

    with ctxure_config(dispatcher=testregister):
        assert structure(Literal[1, 2], 1) == 2
        assert structure(Literal[1, 2], 2) == 1
        assert structure(list[Literal[1, 2]], [1, 2]) == [2, 1]
        assert structure(Foo, {"a": 1}) == Foo(2)
        assert structure(Literal[1], 1) == 1
        assert structure(Literal[2], 2) == 2
        assert structure(int, 1) == 1
        assert structure(int, 2) == 2

        with pytest.raises(ValidationError):
            structure(Literal[1, 2], 3)


def test_structure_hook_literal_ctx_subtypes(testregister):
    @dataclass
    class Foo:
        a: Literal[1, 2]

    @testregister.ctx_subtypes
    def structure_hook(ctx: Ctx[Literal[1, 2]], data: int) -> int:
        if data in [1, 2]:
            return data % 2 + 1
        raise ValidationError(ctx, f"Invalid literal value {data}")

    with ctxure_config(dispatcher=testregister):
        assert structure(Literal[1, 2], 1) == 2
        assert structure(Literal[1, 2], 2) == 1
        assert structure(list[Literal[1, 2]], [1, 2]) == [2, 1]
        assert structure(Foo, {"a": 1}) == Foo(2)
        assert structure(Literal[1], 1) == 2
        assert structure(Literal[2], 2) == 1
        assert structure(int, 1) == 1
        assert structure(int, 2) == 2

        with pytest.raises(ValidationError):
            structure(Literal[1, 2], 3)


def test_structure_hook_primitive_union(testregister):
    @dataclass
    class Foo:
        a: int | None

    @testregister
    def structure_hook(ctx: Ctx[int | None], data: int | None) -> int | None:
        if data is None:
            return None
        return structure_default(ctx, data * 10)

    with ctxure_config(dispatcher=testregister):
        assert structure(int | None, 1) == 10
        assert structure(int | None, None) is None
        assert structure(list[int | None], [1, None]) == [10, None]
        assert structure(Foo, {"a": 1}) == Foo(10)
        assert structure(Foo, {"a": None}) == Foo(None)
        assert structure(float | None, 1.1) == 1.1
        assert structure(str | None, "a") == "a"
        assert structure(int, 1) == 1
        assert structure(str, "a") == "a"
        assert structure(bool, 1) == True

    @testregister
    def structure_hook(ctx: Ctx[int | str], data: int | str) -> int | str:
        return data * 3

    with ctxure_config(dispatcher=testregister):
        assert structure(int | None, 1) == 10
        assert structure(int | None, None) is None
        assert structure(list[int | None], [1, None]) == [10, None]
        assert structure(Foo, {"a": 1}) == Foo(10)
        assert structure(Foo, {"a": None}) == Foo(None)
        assert structure(float | None, 1.1) == 1.1
        assert structure(str | None, "a") == "a"
        assert structure(int, 1) == 1
        assert structure(str, "a") == "a"
        assert structure(bool, 1) == True
        assert structure(int | str, 1) == 3
        assert structure(int | str, "a") == "aaa"

    @testregister
    def structure_hook(ctx: Ctx[int], data: int) -> int:
        return data * 5

    with ctxure_config(dispatcher=testregister):
        assert structure(int | None, 1) == 50
        assert structure(int | None, None) is None
        assert structure(list[int | None], [1, None]) == [50, None]
        assert structure(Foo, {"a": 1}) == Foo(50)
        assert structure(Foo, {"a": None}) == Foo(None)
        assert structure(float | None, 1.1) == 1.1
        assert structure(str | None, "a") == "a"
        assert structure(int, 1) == 5
        assert structure(str, "a") == "a"
        assert structure(bool, 1) == True
        assert structure(int | str, 1) == 3
        assert structure(int | str, "a") == "aaa"


def test_structure_hook_dataclass_union(testregister):
    @dataclass
    class Foo:
        a: int

    @dataclass
    class Bar:
        a: int

    @dataclass
    class Baz:
        b: int

    @dataclass
    class Qux:
        a: int

    @testregister
    def structure_hook(ctx: Ctx[Foo | Bar], data: dict) -> Foo | Bar:
        return Foo(data["a"] * 10)

    @testregister
    def structure_hook(ctx: Ctx[Foo], data: dict) -> Foo:
        return Foo(data["a"] * 100)

    with ctxure_config(dispatcher=testregister):
        assert structure(Foo, {"a": 1}) == Foo(100)
        assert structure(Bar, {"a": 1}) == Bar(1)
        assert structure(Foo | Bar, {"a": 1}) == Foo(10)
        assert structure(list[Foo | Bar], [{"a": 1}, {"a": 2}]) == [Foo(10), Foo(20)]
        assert structure(Foo | Baz, {"a": 1}) == Foo(100)
        assert structure(Foo | Baz, {"b": 2}) == Baz(2)
        assert structure(Bar | Baz, {"a": 2}) == Bar(2)

        with pytest.raises(AmbiguousUnion):
            structure(Foo | Qux, {"a": 1})


def test_structure_hook_union_over_identity(testregister):
    @dataclass
    class Foo:
        x: int

    @testregister
    def structure_hook(ctx: Ctx[Foo], data: int) -> Foo:
        return Foo(data)

    with ctxure_config(dispatcher=testregister):
        assert structure(Foo | int, 5) == Foo(5)
        assert structure(int | Foo, 5) == Foo(5)
        assert structure(Foo | str, "hi") == "hi"


def test_structure_hook_ambiguous_at_union_member(testregister):
    @testregister.ctx_subtypes
    def structure_hook(ctx: Ctx[int | float], data: int) -> int:
        return data * 2

    @testregister.ctx_subtypes
    def structure_hook(ctx: Ctx[int | bytes], data: int) -> int:
        return data * 3

    with ctxure_config(dispatcher=testregister):
        with pytest.raises(AmbiguousUnion):
            structure(int | str, 1)


def test_structure_hook_union_preserve_context(testregister):
    @dataclass
    class Foo:
        a: list[int | str]

    @testregister
    def structure_hook(ctx: Ctx[int, Under[Foo], "$.a[1]"], data: int) -> int:
        return data * 10

    with ctxure_config(dispatcher=testregister):
        assert structure(Foo, {"a": [1, 2, 3]}) == Foo([1, 20, 3])
        assert structure(Foo, {"a": [1, "a", 3]}) == Foo([1, "a", 3])


def test_structure_hook_invariance(testregister):
    @dataclass
    class Foo:
        pass

    @dataclass
    class Bar(Foo):
        pass

    @dataclass
    class Baz(Bar):
        pass

    @testregister
    def structure_hook(ctx: Ctx[Foo], data: int) -> str:
        return "Foo"

    with ctxure_config(dispatcher=testregister):
        assert structure(Foo, 1) == "Foo"

        with pytest.raises(NoStructureHook):
            assert structure(Bar, 1) == "Foo"

        with pytest.raises(NoStructureHook):
            assert structure(Baz, 1) == "Foo"

    @testregister
    def structure_hook(ctx: Ctx[Bar], data: int) -> str:
        return "Bar"

    with ctxure_config(dispatcher=testregister):
        assert structure(Foo, 1) == "Foo"
        assert structure(Bar, 1) == "Bar"

        with pytest.raises(NoStructureHook):
            assert structure(Baz, 1) == "Bar"


def test_structure_hook_disambiguate_by_data_type(testregister):
    @testregister
    def structure_hook(ctx: Ctx[Sequence[int]], data: list) -> list[int]:
        return [x * 10 for x in data]

    @testregister
    def structure_hook(ctx: Ctx[Sequence[int]], data: tuple) -> list[int]:
        return [x * 100 for x in data]

    with ctxure_config(dispatcher=testregister):
        assert structure(Sequence[int], [1, 2]) == [10, 20]
        assert structure(Sequence[int], (1, 2)) == [100, 200]


def test_structure_with_stripped_ctx_routes_to_type_only_hook(testregister):
    @dataclass
    class Inner:
        val: str

    @dataclass
    class Wrapper:
        inner: Inner

    calls: list[str] = []

    @testregister
    def structure_hook(ctx: Ctx[Inner], data: dict) -> Inner:
        calls.append("type-only")
        return Inner(data["val"].upper())

    @testregister
    def structure_hook(ctx: Ctx[Inner, Of[Wrapper]], data: dict) -> Inner:
        calls.append("of-wrapper")
        result = structure_by_type(ctx, data)
        return Inner(result.val + "_wrapped")

    with ctxure_config(dispatcher=testregister):
        assert structure(Wrapper, {"inner": {"val": "hello"}}) == Wrapper(Inner("HELLO_wrapped"))
        assert calls == ["of-wrapper", "type-only"]


def test_structure_with_stripped_ctx_should_not_restore_child_context(testregister):
    @dataclass
    class Inner:
        val: str

    @dataclass
    class Wrapper:
        inner: Inner

    @testregister
    def structure_hook(ctx: Ctx[str, Under[Wrapper]], data: str) -> str:
        return data.upper()

    @testregister
    def structure_hook(ctx: Ctx[str, "$.inner.val"], data: str) -> str:
        return data.upper()

    @testregister
    def structure_hook(ctx: Ctx[Inner], data: dict) -> Inner:
        return structure_default(ctx, data)

    @testregister
    def structure_hook(ctx: Ctx[Inner, Of[Wrapper]], data: dict) -> Inner:
        result = structure_by_type(ctx, data)
        return Inner(result.val + "_wrapped")

    with ctxure_config(dispatcher=testregister):
        assert structure(Wrapper, {"inner": {"val": "hello"}}) == Wrapper(Inner("hello_wrapped"))


def test_structure_with_stripped_ctx_child_get_owner(testregister):
    @dataclass
    class Inner:
        val: str

    @dataclass
    class Wrapper:
        inner: Inner

    @testregister
    def structure_hook(ctx: Ctx[str, Of[Inner]], data: str) -> str:
        return data.upper()

    @testregister
    def structure_hook(ctx: Ctx[Inner], data: dict) -> Inner:
        return structure_default(ctx, data)

    @testregister
    def structure_hook(ctx: Ctx[Inner, Of[Wrapper]], data: dict) -> Inner:
        result = structure_by_type(ctx, data)
        return Inner(result.val + "_wrapped")

    with ctxure_config(dispatcher=testregister):
        assert structure(Wrapper, {"inner": {"val": "hello"}}) == Wrapper(Inner("HELLO_wrapped"))


def test_structure_by_type_redispatches_per_data_type(testregister):
    @dataclass
    class Target:
        x: int

    @testregister
    def structure_hook(ctx: Ctx[Target], data: str) -> Target:
        return Target(int(data))

    @dataclass
    class Owner:
        inner: Target

    @testregister
    def structure_hook(ctx: Ctx[Target, Of[Owner]], data: dict) -> Target:
        if data.get("form") == "str":
            return structure_by_type(ctx, data["val"])  # str -> type-only str hook
        return structure_by_type(ctx, {"x": data["val"]})  # dict -> default dataclass

    with ctxure_config(dispatcher=testregister):
        assert structure(Owner, {"inner": {"form": "dict", "val": 10}}) == Owner(Target(10))
        assert structure(Owner, {"inner": {"form": "str", "val": "20"}}) == Owner(Target(20))
        assert structure(Owner, {"inner": {"form": "dict", "val": 30}}) == Owner(Target(30))


def test_register_general_multimethod(testregister):
    with pytest.raises(TypeError):

        @testregister.ctx_subtypes
        def foo(data: int) -> int:
            return data * 10

    @testregister
    def foo(data: int) -> int:
        return data * 10

    assert foo(1) == 10


def test_structure_hook_priority_paths(testregister):
    @dataclass
    class Foo:
        foo: int

    @testregister
    def structure_hook(ctx: Ctx[".foo"], data: int) -> int:
        return data * 10

    with ctxure_config(dispatcher=testregister):
        assert structure(Foo, {"foo": 1}) == Foo(10)

    @testregister
    def structure_hook(ctx: Ctx["$.foo"], data: int) -> int:
        return data * 1000

    with ctxure_config(dispatcher=testregister):
        assert structure(Foo, {"foo": 1}) == Foo(1000)


def test_structure_hook_priority_additional_constraints(testregister):
    @dataclass
    class Foo:
        foo: int

    @testregister
    def structure_hook(ctx: Ctx[int], data: int) -> int:
        return data * 10

    with ctxure_config(dispatcher=testregister):
        assert structure(Foo, {"foo": 1}) == Foo(10)

    @testregister
    def structure_hook(ctx: Ctx[int, Of[Foo]], data: int) -> int:
        return data * 100

    with ctxure_config(dispatcher=testregister):
        assert structure(Foo, {"foo": 1}) == Foo(100)

    @testregister
    def structure_hook(ctx: Ctx[int, Of[Foo], ".foo"], data: int) -> int:
        return data * 1000

    with ctxure_config(dispatcher=testregister):
        assert structure(Foo, {"foo": 1}) == Foo(1000)


def test_structure_hook_priority_different_constraints(testregister):
    @dataclass
    class Foo:
        foo: int

    @testregister
    def structure_hook(ctx: Ctx[int], data: int) -> int:
        return data * 10

    @testregister
    def structure_hook(ctx: Ctx[".foo"], data: int) -> int:
        return data * 100

    with ctxure_config(dispatcher=testregister):
        with pytest.raises(MultipleStructureHooks) as e:
            structure(Foo, {"foo": 1})
        assert len(e.value.candidates) == 2
        assert e.value.data == 1

    @testregister
    def structure_hook(ctx: Ctx[Of[Foo]], data: int) -> int:
        return data * 1000

    with ctxure_config(dispatcher=testregister):
        with pytest.raises(MultipleStructureHooks) as e:
            structure(Foo, {"foo": 1})
        assert len(e.value.candidates) == 3

    @testregister
    def structure_hook(ctx: Ctx["$.foo"], data: int) -> int:
        return data * 10000

    with ctxure_config(dispatcher=testregister):
        with pytest.raises(MultipleStructureHooks) as e:
            structure(Foo, {"foo": 1})
        assert len(e.value.candidates) == 3


def test_structure_hook_under_root(testregister):
    @testregister
    def structure_hook(ctx: Ctx[int, Under[int]], data: int) -> int:
        return data * 10

    with ctxure_config(dispatcher=testregister):
        assert structure(int, 5) == 50


def test_structure_hook_under_does_not_match_other_root(testregister):
    @testregister
    def structure_hook(ctx: Ctx[int, Under[int]], data: int) -> int:
        return data * 10

    with ctxure_config(dispatcher=testregister):
        assert structure(list[int], [1, 2]) == [1, 2]


def test_structure_hook_under_matches_nested_position_with_inherited_root(testregister):
    @testregister
    def structure_hook(ctx: Ctx[int, Under[list[int]]], data: int) -> int:
        return data * 10

    with ctxure_config(dispatcher=testregister):
        assert structure(list[int], [1, 2]) == [10, 20]
        assert structure(int, 5) == 5


def test_structure_hook_under_preserved_through_union_narrowing_at_root(testregister):
    @testregister
    def structure_hook(ctx: Ctx[int, Under[int | str]], data: int) -> int:
        return data * 10

    with ctxure_config(dispatcher=testregister):
        assert structure(int | str, 5) == 50


def test_structure_hook_under_preserved_through_dataclass_union_dispatch_at_root(testregister):
    @dataclass
    class A:
        a: int

    @dataclass
    class B:
        b: int

    @testregister
    def structure_hook(ctx: Ctx[int, Under[A | B]], data: int) -> int:
        return data * 10

    with ctxure_config(dispatcher=testregister):
        assert structure(A | B, {"a": 5}) == A(50)
        assert structure(A | B, {"b": 7}) == B(70)


def test_structure_default_preserves_root(testregister):
    saw_roots = []

    @testregister
    def structure_hook(ctx: Ctx[int], data: int) -> int:
        # Walk to the root ctx and capture its structured_type
        c = ctx
        while c.parent is not None:
            c = c.parent
        saw_roots.append(c.structured_type)
        return structure_default(ctx, data)

    with ctxure_config(dispatcher=testregister):
        structure(list[int], [1, 2])

    # Both inner int positions see the same top-of-chain root
    assert saw_roots == [list[int], list[int]]


def test_structure_extra_visible_through_root_level_dataclass_union(testregister):
    @dataclass
    class A:
        a: int

    @dataclass
    class B:
        b: int

    seen = []

    @testregister
    def structure_hook(ctx: Ctx[int], data: int) -> int:
        seen.append(get_extra(ctx))
        return structure_default(ctx, data)

    with ctxure_config(dispatcher=testregister):
        structure(A | B, {"a": 5}, extra={"tag": "root-union"})

    assert seen == [{"tag": "root-union"}]


def test_structure_hook_for_union_fired_by_default_union_handler(testregister):
    @testregister.ctx_subtypes
    def structure_hook(ctx: Ctx[int | str], data: int | str) -> str:
        return "int | str"

    with ctxure_config(dispatcher=testregister):
        with pytest.raises(AmbiguousUnion):
            structure(int | str | float, 1)


def test_structure_hook_for_literal_fired_by_default_union_handler(testregister):
    @testregister
    def structure_hook(ctx: Ctx[Literal[1]], data: int) -> int:
        # Not 1, anyway for test.
        return 10

    with ctxure_config(dispatcher=testregister):
        assert structure(Literal[1] | int, 1) == 10
        assert structure(Literal[1] | int, 2) == 2
        assert structure(Literal[1, 2], 1) == 10
        assert structure(Literal[1, 2] | int, 1) == 10
        assert structure(Literal[1, 2] | int, 2) == 2
        assert structure(Literal[1, 2] | int, 3) == 3
        assert structure(Literal[1, 2] | str, 1) == 10
        assert structure(Literal[1, 2] | str, 2) == 2
        assert structure(Literal[1, 2] | str, "a") == "a"
        assert structure(Literal[1] | Literal[2], 1) == 10
        assert structure(Literal[1] | Literal[2] | int, 1) == 10
        assert structure(Literal[1] | Literal[2] | int, 3) == 3
        assert structure(Literal[1] | Literal[2] | int | str, 1) == 10
        assert structure(Literal[1] | Literal[2] | int | str, 2) == 2
        assert structure(Literal[1] | Literal[2] | int | str, 3) == 3
        assert structure(Literal[1] | Literal[2] | int | str, "a") == "a"

        with pytest.raises(ValidationError):
            structure(Literal[1, 2], 3)

        with pytest.raises(NoStructureHook):
            structure(Literal[1] | Literal[2], 3)

        with pytest.raises(NoStructureHook):
            structure(Literal[1, 2] | str, 3)

    @testregister
    def structure_hook(ctx: Ctx[int], data: int) -> int:
        return data * 100

    with ctxure_config(dispatcher=testregister):
        assert structure(Literal[1] | int, 1) == 10
        assert structure(Literal[1] | int, 2) == 200
        assert structure(Literal[1, 2], 1) == 10
        assert structure(Literal[1, 2] | int, 1) == 10
        assert structure(Literal[1, 2] | int, 2) == 2
        assert structure(Literal[1, 2] | int, 3) == 300
        assert structure(Literal[1, 2] | str, 1) == 10
        assert structure(Literal[1, 2] | str, 2) == 2
        assert structure(Literal[1, 2] | str, "a") == "a"
        assert structure(Literal[1] | Literal[2], 1) == 10
        assert structure(Literal[1] | Literal[2] | int, 1) == 10
        assert structure(Literal[1] | Literal[2] | int, 3) == 300
        assert structure(Literal[1] | Literal[2] | int | str, 1) == 10
        assert structure(Literal[1] | Literal[2] | int | str, 2) == 2
        assert structure(Literal[1] | Literal[2] | int | str, 3) == 300
        assert structure(Literal[1] | Literal[2] | int | str, "a") == "a"

        with pytest.raises(ValidationError):
            structure(Literal[1, 2], 3)

        with pytest.raises(NoStructureHook):
            structure(Literal[1] | Literal[2], 3)

        with pytest.raises(NoStructureHook):
            structure(Literal[1, 2] | str, 3)


def test_structure_hook_for_typeddict_fired_by_default_union_handler(testregister):
    class Foo(TypedDict):
        tag: Literal["foo"]
        a: int

    class Bar(TypedDict):
        tag: Literal["bar"]
        b: int

    @testregister
    def structure_hook(ctx: Ctx[Foo], data: dict) -> dict:
        return {"a": data["a"] * 10}

    with ctxure_config(dispatcher=testregister):
        assert structure(Foo | Bar, {"a": 1, "tag": "foo"}) == {"a": 10}
        assert structure(Foo | Bar, {"b": 2, "tag": "bar"}) == {"b": 2, "tag": "bar"}


def test_structure_hook_for_base_of_literal_with_ctx_subtypes(testregister):
    @testregister.ctx_subtypes
    def structure_hook(ctx: Ctx[int], data: int) -> int:
        return data * 10

    with ctxure_config(dispatcher=testregister):
        assert structure(Literal[1], 1) == 10
        assert structure(Literal[1, 2], 1) == 10
        assert structure(Literal[1, 2], 2) == 20
        assert structure(Literal[1, 2], 3) == 30


def test_structure_hook_rejects_specific_key_constraint(testregister):
    with pytest.raises(TypeError, match="dict-key constraint.*meaningless"):

        @testregister
        def structure_hook(ctx: Ctx[int, "[~'foo']"], data: int) -> int:  # noqa: F821
            return data

    with pytest.raises(TypeError, match="dict-key constraint.*meaningless"):

        @testregister
        def structure_hook(ctx: Ctx[int, "$[~0]"], data: int) -> int:
            return data


def test_structure_hook_rejects_empty_constraint(testregister):
    with pytest.raises(TypeError, match="The signature of a hook should be"):

        @testregister
        def structure_hook(data: int) -> int:
            return data


def test_structure_hook_accepts_wildcard_key_constraint(testregister):
    @testregister
    def structure_hook(ctx: Ctx[int, "[~?]"], data: int) -> int:
        return data * 10

    with ctxure_config(dispatcher=testregister):
        assert structure(dict[int, str], {1: "a"}) == {10: "a"}


def test_structure_hook_accepts_item_path_with_specific_key(testregister):
    @testregister
    def structure_hook(ctx: Ctx[int, "['foo']"], data: int) -> int:  # noqa: F821
        return data * 10

    with ctxure_config(dispatcher=testregister):
        assert structure(dict[str, int], {"foo": 1, "bar": 2}) == {"foo": 10, "bar": 2}


def test_structure_hook_literal_data(testregister):
    @testregister
    def structure_hook(ctx: Ctx[int], data: Literal[1, 2]) -> int:
        return data * 10

    with ctxure_config(dispatcher=testregister):
        assert structure(int, 1) == 10
        assert structure(int, 2) == 20
        assert structure(int, 3) == 3
        assert structure(int | str, 1) == 10
        assert structure(int | str, 3) == 3

    @testregister
    def structure_hook(ctx: Ctx[int], data: int) -> int:
        return data * 100

    with ctxure_config(dispatcher=testregister):
        assert structure(int, 1) == 10
        assert structure(int, 2) == 20
        assert structure(int, 3) == 300

    with ctxure_config(dispatcher=testregister.copy()):
        assert structure(int, 1) == 10
        assert structure(int, 2) == 20
        assert structure(int, 3) == 300


def test_structure_hook_literal_data_selects_union_member(testregister):
    class Token:
        pass

    token = Token()

    # Only this hook can produce a Token, and only for the literal "token".
    @testregister
    def structure_hook(ctx: Ctx[Token], data: Literal["token"]) -> Token:
        return token

    with ctxure_config(dispatcher=testregister):
        assert structure(Token | int, "token") is token
        assert structure(Token | int, 1) == 1

        with pytest.raises(NoStructureHook):
            structure(Token | int, "other")


def test_structure_hook_multitype_literal_data(testregister):
    class Foo(Enum):
        A = "A"

    @testregister
    def structure_hook(ctx: Ctx[int], data: Literal[1, "a", Foo.A]) -> int:
        return -1

    with ctxure_config(dispatcher=testregister):
        assert structure(int, 1) == -1
        assert structure(int, "a") == -1
        assert structure(int, Foo.A) == -1
        assert structure(int, 2) == 2

    with pytest.raises(NoStructureHook):
        structure(int, "b")

    with pytest.raises(NoStructureHook):
        structure(int, "A")


def test_structure_hook_field_get_data(testregister):
    @dataclass
    class Foo:
        a: int
        b: int  # hook-free sibling

    seen = []

    @testregister
    def structure_hook(ctx: Ctx[".a", Of[Foo], int], data: int) -> int:
        seen.append(get_data(ctx))
        return data * 2

    with ctxure_config(dispatcher=testregister):
        assert structure(Foo, {"a": 3, "b": 1}) == Foo(6, 1)
        assert structure(Foo, {"a": 5, "b": 2}) == Foo(10, 2)

    assert seen == [3, 5]


def test_structure_hook_get_parent_data(testregister):
    @dataclass
    class Inner:
        a: int
        b: int

    @dataclass
    class Outer:
        inner: Inner  # no hook on Inner itself → is_hook_free=True → bypassed

    seen = []

    @testregister
    def structure_hook(ctx: Ctx[".a", Of[Inner], int], data: int) -> int:
        assert ctx.parent is not None
        seen.append(get_data(ctx.parent))  # should be the current dict for Inner
        return data * 2

    with ctxure_config(dispatcher=testregister):
        assert structure(Outer, {"inner": {"a": 3, "b": 1}}) == Outer(Inner(6, 1))
        assert structure(Outer, {"inner": {"a": 5, "b": 2}}) == Outer(Inner(10, 2))

    assert seen == [{"a": 3, "b": 1}, {"a": 5, "b": 2}]


def test_structure_hook_get_parent_data_nested_container(testregister):
    # The hook on the elements must stop the inner lists from being bypassed on later calls,
    # otherwise the inner list's recorded data goes stale.
    seen = []

    @testregister
    def structure_hook(ctx: Ctx[int], data: int) -> int:
        assert ctx.parent is not None
        seen.append(get_data(ctx.parent))
        return data

    with ctxure_config(dispatcher=testregister):
        assert structure(list[list[int]], [[1]]) == [[1]]
        assert structure(list[list[int]], [[2]]) == [[2]]

    assert seen == [[1], [2]]


def test_structure_hook_get_parent_data_list(testregister):
    @dataclass
    class Outer:
        items: list[int]  # no hook on list → bypassed by Outer until propagation

    seen = []

    @testregister
    def structure_hook(ctx: Ctx["[0]", int], data: int) -> int:
        assert ctx.parent is not None
        seen.append(get_data(ctx.parent))  # should be the current list being structured
        return data * 2

    with ctxure_config(dispatcher=testregister):
        assert structure(Outer, {"items": [3, 4]}) == Outer([6, 4])
        assert structure(Outer, {"items": [5, 6]}) == Outer([10, 6])

    assert seen == [[3, 4], [5, 6]]


def test_structure_hook_enum_type_ctx(testregister):
    class Foo(Enum):
        A = 1
        B = 2

    @testregister
    def structure_hook(ctx: Ctx[Foo], data: float) -> Foo:
        return Foo.A if data > 0 else Foo.B

    with ctxure_config(testregister):
        assert structure(Foo, 0.1) == Foo.A
        assert structure(Foo, -0.1) == Foo.B


def test_structure_hook_typeddict_ctx(testregister):
    class Foo(TypedDict):
        a: str
        b: str

    @testregister
    def structure_hook(ctx: Ctx[Foo], data: str) -> Foo:
        a, b = data.split(":")
        return {"a": a, "b": b}

    with ctxure_config(testregister):
        assert structure(Foo, "x:y") == {"a": "x", "b": "y"}

    with pytest.raises(NoStructureHook):
        structure(dict, "x:y")


def test_structure_hook_user_defined_class_ctx(testregister):
    class Foo:
        a: str
        b: str

        def __init__(self, a: str, b: str):
            self.a = a
            self.b = b

    @testregister
    def structure_hook(ctx: Ctx[Foo], data: str) -> Foo:
        a, b = data.split(":")
        return Foo(a, b)

    with ctxure_config(testregister):
        foo = structure(Foo, "x:y")
        assert foo.a == "x"
        assert foo.b == "y"


def test_structure_default_dataclass_with_keymap(testregister):
    @dataclass
    class Foo:
        a: int
        b: int
        c: int

    keymap = {"b": "B", "c": "C"}

    @testregister
    def structure_hook(ctx: Ctx[Foo], data: dict) -> Foo:
        return structure_default(ctx, data, keymap)

    with ctxure_config(testregister):
        assert structure(Foo, {"a": 1, "B": 2, "C": 3}) == Foo(1, 2, 3)

        with pytest.raises(MissingFields) as e:
            structure(Foo, {"a": 1, "b": 2, "c": 3})
        assert e.value.missing == ["B", "C"]

        with pytest.raises(ExtraFields) as e:
            structure(Foo, {"a": 1, "B": 2, "C": 3, "d": 4})
        assert e.value.extra == ["d"]


def test_structure_newtype_dict_key_uses_supertype_for_value_path(testregister):
    UserId = NewType("UserId", int)

    @testregister
    def structure_hook(ctx: Ctx[str, "$[1]"], data: str) -> str:
        return data.upper()

    with ctxure_config(testregister):
        assert structure(dict[UserId, str], {"1": "a"}) == {1: "A"}


def test_structure_default_union_with_keymap_is_not_supported(testregister):
    @dataclass
    class Foo:
        a: int

    @dataclass
    class Bar:
        b: int

    keymap = {"a": "A", "b": "B"}

    @testregister
    def structure_hook(ctx: Ctx[Foo | Bar], data: dict) -> Foo | Bar:
        return structure_default(ctx, data, keymap)

    with ctxure_config(testregister):
        with pytest.raises(ValidationError, match="keymap is not supported") as e:
            structure(Foo | Bar, {"A": 1})
        assert e.value.ctx.structured_type == Foo | Bar


def test_structure_default_typeddict_with_keymap(testregister):
    class Foo(TypedDict):
        a: int
        b: int
        c: int

    keymap = {"b": "B", "c": "C"}

    @testregister
    def structure_hook(ctx: Ctx[Foo], data: dict) -> Foo:
        return structure_default(ctx, data, keymap)

    with ctxure_config(testregister):
        assert structure(Foo, {"a": 1, "B": 2, "C": 3}) == {"a": 1, "b": 2, "c": 3}
        assert structure(Foo, {"a": 1, "B": 2, "C": 3, "d": 4}) == {"a": 1, "b": 2, "c": 3}

        with pytest.raises(MissingFields) as e:
            structure(Foo, {"a": 1, "b": 2, "c": 3})
        assert e.value.missing == ["B", "C"]


def test_structure_default_closed_typeddict_with_keymap(testregister):
    class Foo(ExtTypedDict, closed=True):
        a: int
        b: int

    keymap = {"b": "B"}

    @testregister
    def structure_hook(ctx: Ctx[Foo], data: dict) -> Foo:
        return structure_default(ctx, data, keymap)

    with ctxure_config(testregister):
        assert structure(Foo, {"a": 1, "B": 2}) == {"a": 1, "b": 2}

        with pytest.raises(ExtraFields) as e:
            structure(Foo, {"a": 1, "B": 2, "x": 3})
        assert e.value.extra == ["x"]


def test_structure_default_typeddict_extra_items_with_keymap(testregister):
    class Foo(ExtTypedDict, extra_items=int):
        a: str
        b: str

    keymap = {"b": "B"}

    @testregister
    def structure_hook(ctx: Ctx[Foo], data: dict) -> Foo:
        return structure_default(ctx, data, keymap)

    with ctxure_config(testregister):
        assert structure(Foo, {"a": "x", "B": "y"}) == {"a": "x", "b": "y"}
        assert structure(Foo, {"a": "x", "B": "y", "extra": 99}) == {"a": "x", "b": "y", "extra": 99}

        with pytest.raises(ValidationError) as e:
            structure(Foo, {"a": "x", "B": "y", "b": 99})
        assert "conflicts with declared field" in str(e.value)


def test_structure_default_with_keymap_dynamic_keymap(testregister):
    @dataclass
    class Foo:
        a: int
        b: int
        c: int

    @testregister
    def structure_hook(ctx: Ctx[Foo], data: dict) -> Foo:
        keymap = {"b": "B", "c": "C"}
        return structure_default(ctx, data, keymap)

    with ctxure_config(testregister):
        for _ in range(100):
            assert structure(Foo, {"a": 1, "B": 2, "C": 3}) == Foo(1, 2, 3)

    keymap1 = {"b": "B", "c": "C"}
    keymap2 = {"b": "_b", "c": "_c"}

    @testregister
    def structure_hook(ctx: Ctx[Foo], data: dict) -> Foo:
        if data["a"] > 0:
            return structure_default(ctx, data, keymap1)
        else:
            return structure_default(ctx, data, keymap2)

    with ctxure_config(testregister):
        assert structure(Foo, {"a": 1, "B": 2, "C": 3}) == Foo(1, 2, 3)
        assert structure(Foo, {"a": -1, "_b": 2, "_c": 3}) == Foo(-1, 2, 3)
        assert structure(Foo, {"a": 1, "B": 2, "C": 3}) == Foo(1, 2, 3)
        assert structure(Foo, {"a": -1, "_b": 2, "_c": 3}) == Foo(-1, 2, 3)


def test_structure_hook_newtype_union_with_supertype(testregister):
    Int = NewType("Int", int)

    @testregister.ctx_subtypes
    def structure_hook(ctx: Ctx[Int | int], data: int) -> Int:
        return Int(data * 100)

    with ctxure_config(dispatcher=testregister):
        assert structure(Int, 1) == 100
        assert structure(int, 1) == 100


def test_structure_hook_various_target_from_int(testregister):
    @dataclass
    class Foo:
        a: int

    class Bar(TypedDict):
        a: int

    NewFoo = NewType("NewFoo", Foo)

    @testregister
    def structure_hook(ctx: Ctx[Foo], data: int) -> Foo:
        return Foo(data)

    @testregister
    def structure_hook(ctx: Ctx[Bar], data: int) -> Bar:
        return {"a": data}

    @testregister
    def structure_hook(ctx: Ctx[Literal[1, 2]], data: int) -> Literal[1]:
        return 1

    @testregister
    def structure_hook(ctx: Ctx[NewFoo], data: int) -> NewFoo:
        return NewFoo(Foo(data * 10000))

    with ctxure_config(dispatcher=testregister):
        assert structure(Foo, 1) == Foo(1)
        assert structure(Bar, 1) == {"a": 1}
        assert structure(Literal[1, 2], 1) == 1
        assert structure(Literal[1, 2], 2) == 1
        assert structure(Literal[1, 2], 3) == 1
        assert structure(int, 3) == 3
        assert structure(NewFoo, 1) == NewFoo(Foo(10000))
        assert structure(NewFoo, 1) == NewFoo(Foo(10000))


def test_structure_hook_calling_structure_default_in_union_ctx(testregister):

    @dataclass
    class Foo:
        a: int | str

    @testregister
    def structure_hook(ctx: Ctx["$.a"], data: Any) -> str:
        return structure_default(ctx, data).upper()

    with ctxure_config(dispatcher=testregister):
        assert structure(Foo, {"a": "x"}) == Foo("X")


def test_structure_hook_literal_union_equivalence_1(testregister):
    @testregister
    def structure_hook(ctx: Ctx[Literal[1, 2]], data: int) -> str:
        return "a"

    with ctxure_config(dispatcher=testregister):
        assert structure(Literal[1] | Literal[2], 1) == "a"
        assert structure(Literal[1] | Literal[2], 2) == "a"


def test_structure_hook_literal_union_equivalence_2(testregister):
    @testregister
    def structure_hook(ctx: Ctx[Literal[1] | Literal[2]], data: int) -> str:
        return "a"

    with ctxure_config(dispatcher=testregister):
        assert structure(Literal[1, 2], 1) == "a"
        assert structure(Literal[1, 2], 2) == "a"


def test_structure_hook_reentrance_error(testregister):
    @testregister
    def structure_hook(ctx: Ctx[int], data: int) -> int:
        return structure(int, data)

    with ctxure_config(dispatcher=testregister):
        with pytest.raises(ReentranceError):
            structure(int, 1)
