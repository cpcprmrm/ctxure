from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Generic, Literal, NewType, TypeVar, TypedDict

import pytest
from typing_extensions import TypedDict as ExtTypedDict

from ctxure import (
    AmbiguousUnion,
    Ctx,
    KeyPath,
    MultipleUnstructureHooks,
    NoUnstructureHook,
    Of,
    Under,
    ValidationError,
    ctxure_config,
    get_data,
    get_extra,
    unstructure,
    unstructure_by_type,
    unstructure_default,
)
from ctxure.error import ReentranceError


def test_unstructure_hook_local_dispatch(testregister):
    @testregister
    def unstructure_hook(ctx: Ctx[int], data: int) -> int:
        return data * 10

    with ctxure_config(dispatcher=testregister):
        assert unstructure(int, 10) == 100

    assert unstructure(int, 10) == 10


def test_unstructure_hook_primitive_type_ctx(testregister):
    @dataclass
    class Foo:
        a: int
        b: float

    @testregister
    def unstructure_hook(ctx: Ctx[int], data: int) -> int:
        return data * 10

    with ctxure_config(dispatcher=testregister):
        assert unstructure(int, 10) == 100
        assert unstructure(list[int], [1, 2, 3]) == [10, 20, 30]
        assert unstructure(tuple[int, float, int], (1, 1.1, 2)) == [10, 1.1, 20]
        assert sorted(unstructure(set[int], {1, 2, 3})) == [10, 20, 30]
        assert sorted(unstructure(frozenset[int], frozenset({1, 2, 3}))) == [10, 20, 30]
        assert unstructure(dict[str, int], {"a": 1}) == {"a": 10}
        assert unstructure(Foo, Foo(1, 1.0)) == {"a": 10, "b": 1.0}
        assert unstructure(list[Foo], [Foo(1, 1.1), Foo(2, 2.1)]) == [{"a": 10, "b": 1.1}, {"a": 20, "b": 2.1}]
        assert sorted(unstructure(list[set[int]], [{1, 2}, {3, 4}]), key=sorted) == [[10, 20], [30, 40]]


def test_unstructure_hook_primitive_type_ctx_with_path(testregister):
    @dataclass
    class Foo:
        a: int
        b: float

    @testregister
    def unstructure_hook(ctx: Ctx[int, "$[0]"], data: int) -> int:
        return data * 10

    with ctxure_config(dispatcher=testregister):
        assert unstructure(int, 1) == 1
        assert unstructure(list[int], [1, 2, 3]) == [10, 2, 3]
        assert unstructure(tuple[int, float, int], (1, 1.1, 2)) == [10, 1.1, 2]
        assert sorted(unstructure(set[int], {1, 2, 3})) == [1, 2, 3]
        assert sorted(unstructure(frozenset[int], frozenset({1, 2, 3}))) == [1, 2, 3]
        assert unstructure(dict[str, int], {"a": 1, "b": 2}) == {"a": 1, "b": 2}
        assert unstructure(Foo, Foo(1, 1.0)) == {"a": 1, "b": 1.0}
        assert unstructure(list[list[int]], [[1, 2], [3, 4]]) == [[1, 2], [3, 4]]

    @testregister
    def unstructure_hook(ctx: Ctx[int, "$.a"], data: int) -> int:
        return data * 10

    with ctxure_config(dispatcher=testregister):
        assert unstructure(int, 1) == 1
        assert unstructure(list[int], [1, 2, 3]) == [10, 2, 3]
        assert unstructure(tuple[int, float, int], (1, 1.1, 2)) == [10, 1.1, 2]
        assert sorted(unstructure(set[int], {1, 2, 3})) == [1, 2, 3]
        assert sorted(unstructure(frozenset[int], frozenset({1, 2, 3}))) == [1, 2, 3]
        assert unstructure(dict[str, int], {"a": 1, "b": 2}) == {"a": 1, "b": 2}
        assert unstructure(Foo, Foo(1, 1.0)) == {"a": 10, "b": 1.0}
        assert unstructure(list[list[int]], [[1, 2], [3, 4]]) == [[1, 2], [3, 4]]


def test_unstructure_hook_list_type_ctx(testregister):
    @dataclass(frozen=True)
    class Foo:
        a: list[int]

    @testregister
    def unstructure_hook(ctx: Ctx[list[int]], data: list) -> list:
        r = unstructure_default(ctx, data)
        r[-1] *= 10
        return r

    with ctxure_config(dispatcher=testregister):
        assert unstructure(list[int], [1, 2]) == [1, 20]
        assert unstructure(list[list[int]], [[1, 2], [3, 4]]) == [[1, 20], [3, 40]]
        assert unstructure(Foo, Foo(a=[1, 2])) == {"a": [1, 20]}
        assert unstructure(tuple[Foo, Foo], (Foo(a=[1, 2]), Foo(a=[3]))) == [{"a": [1, 20]}, {"a": [30]}]


def test_unstructure_hook_list_type_ctx_with_path(testregister):
    @dataclass(frozen=True)
    class Foo:
        a: list[int]

    @testregister
    def unstructure_hook(ctx: Ctx[list[int], "$[1]"], data: list) -> list:
        r = unstructure_default(ctx, data)
        r[-1] *= 10
        return r

    with ctxure_config(dispatcher=testregister):
        assert unstructure(list[int], [1, 2]) == [1, 2]
        assert unstructure(list[list[int]], [[1, 2], [3, 4]]) == [[1, 2], [3, 40]]
        assert unstructure(Foo, Foo(a=[1, 2])) == {"a": [1, 2]}
        assert unstructure(tuple[Foo, Foo], (Foo(a=[1, 2]), Foo(a=[3]))) == [{"a": [1, 2]}, {"a": [3]}]

    @testregister
    def unstructure_hook(ctx: Ctx[list[int], "$"], data: list) -> list:
        r = unstructure_default(ctx, data)
        r[-1] = 0
        return r

    with ctxure_config(dispatcher=testregister):
        assert unstructure(list[int], [1, 2]) == [1, 0]
        assert unstructure(list[list[int]], [[1, 2], [3, 4]]) == [[1, 2], [3, 40]]
        assert unstructure(Foo, Foo(a=[1, 2])) == {"a": [1, 2]}
        assert unstructure(tuple[Foo, Foo], (Foo(a=[1, 2]), Foo(a=[3]))) == [{"a": [1, 2]}, {"a": [3]}]

    @testregister
    def unstructure_hook(ctx: Ctx[list[int], "$[0].a"], data: list) -> list:
        r = unstructure_default(ctx, data)
        r[-1] *= 100
        return r

    with ctxure_config(dispatcher=testregister):
        assert unstructure(list[int], [1, 2]) == [1, 0]
        assert unstructure(list[list[int]], [[1, 2], [3, 4]]) == [[1, 2], [3, 40]]
        assert unstructure(Foo, Foo(a=[1, 2])) == {"a": [1, 2]}
        assert unstructure(tuple[Foo, Foo], (Foo(a=[1, 2]), Foo(a=[3]))) == [{"a": [1, 200]}, {"a": [3]}]


def test_unstructure_hook_dataclass_ctx(testregister):
    @dataclass
    class Foo:
        a: str
        b: int

    @dataclass
    class Bar:
        f: Foo

    @testregister
    def unstructure_hook(ctx: Ctx[Foo], data: Foo) -> dict:
        return {"a": data.a, "b": data.b * 10}

    with ctxure_config(dispatcher=testregister):
        assert unstructure(Foo, Foo("x", 1)) == {"a": "x", "b": 10}
        assert unstructure(list[Foo], [Foo("x", 1), Foo("y", 2)]) == [{"a": "x", "b": 10}, {"a": "y", "b": 20}]
        assert unstructure(Bar, Bar(Foo("x", 1))) == {"f": {"a": "x", "b": 10}}
        assert unstructure(tuple[Bar, Bar], (Bar(Foo("x", 1)), Bar(Foo("y", 2)))) == [
            {"f": {"a": "x", "b": 10}},
            {"f": {"a": "y", "b": 20}},
        ]


def test_unstructure_hook_field(testregister):
    @dataclass
    class Foo:
        a: int
        b: int

    @dataclass
    class Bar:
        a: int

    @testregister
    def unstructure_hook(ctx: Ctx[".a"], data: int) -> int:
        return data * 10

    with ctxure_config(dispatcher=testregister):
        assert unstructure(Foo, Foo(1, 2)) == {"a": 10, "b": 2}
        assert unstructure(Bar, Bar(3)) == {"a": 30}
        assert unstructure(list[Foo], [Foo(1, 2)]) == [{"a": 10, "b": 2}]
        assert unstructure(list[Bar], [Bar(3)]) == [{"a": 30}]

    @testregister
    def unstructure_hook(ctx: Ctx[".a", Of[Foo]], data: int) -> int:
        return data * 100

    with ctxure_config(dispatcher=testregister):
        assert unstructure(Foo, Foo(1, 2)) == {"a": 100, "b": 2}
        assert unstructure(Bar, Bar(3)) == {"a": 30}
        assert unstructure(list[Foo], [Foo(1, 2)]) == [{"a": 100, "b": 2}]
        assert unstructure(list[Bar], [Bar(3)]) == [{"a": 30}]

    # Never fires, as the target type does not match
    @testregister
    def unstructure_hook(ctx: Ctx[".a", Of[Foo], str], data: int) -> int:
        return data * 1000

    with ctxure_config(dispatcher=testregister):
        assert unstructure(Foo, Foo(1, 2)) == {"a": 100, "b": 2}
        assert unstructure(Bar, Bar(3)) == {"a": 30}
        assert unstructure(list[Foo], [Foo(1, 2)]) == [{"a": 100, "b": 2}]
        assert unstructure(list[Bar], [Bar(3)]) == [{"a": 30}]

    @testregister
    def unstructure_hook(ctx: Ctx[".a", Of[Foo], int], data: int) -> int:
        return data * 1000

    with ctxure_config(dispatcher=testregister):
        assert unstructure(Foo, Foo(1, 2)) == {"a": 1000, "b": 2}
        assert unstructure(Bar, Bar(3)) == {"a": 30}
        assert unstructure(list[Foo], [Foo(1, 2)]) == [{"a": 1000, "b": 2}]
        assert unstructure(list[Bar], [Bar(3)]) == [{"a": 30}]

    @testregister
    def unstructure_hook(ctx: Ctx[".b", Of[Foo]], data: int) -> int:
        return -1

    @testregister
    def unstructure_hook(ctx: Ctx[".b", int], data: int) -> int:
        return -1

    with ctxure_config(dispatcher=testregister):
        assert unstructure(Bar, Bar(3)) == {"a": 30}
        assert unstructure(list[Bar], [Bar(3)]) == [{"a": 30}]

        foo = Foo(1, 2)
        with pytest.raises(MultipleUnstructureHooks) as e:
            unstructure(Foo, foo)
        assert e.value.data == 2
        assert len(e.value.candidates) == 2


def test_unstructure_hook_field_wildcard(testregister):
    @dataclass
    class Foo:
        a: int
        b: int

    @dataclass
    class Bar:
        a: int

    @testregister
    def unstructure_hook(ctx: Ctx[".?"], data: int) -> int:
        return data * 10

    with ctxure_config(dispatcher=testregister):
        assert unstructure(Foo, Foo(1, 2)) == {"a": 10, "b": 20}
        assert unstructure(Bar, Bar(3)) == {"a": 30}
        assert unstructure(list[Foo], [Foo(1, 2)]) == [{"a": 10, "b": 20}]
        assert unstructure(list[Bar], [Bar(3)]) == [{"a": 30}]

    @testregister
    def unstructure_hook(ctx: Ctx[".?", Of[Bar]], data: int) -> int:
        return data * 100

    with ctxure_config(dispatcher=testregister):
        assert unstructure(Foo, Foo(1, 2)) == {"a": 10, "b": 20}
        assert unstructure(Bar, Bar(3)) == {"a": 300}
        assert unstructure(list[Foo], [Foo(1, 2)]) == [{"a": 10, "b": 20}]
        assert unstructure(list[Bar], [Bar(3)]) == [{"a": 300}]


def test_unstructure_hook_item(testregister):
    @testregister
    def unstructure_hook(ctx: Ctx["[0]"], data: int | str) -> int | str:
        return data * 10

    with ctxure_config(dispatcher=testregister):
        assert unstructure(list[int], [1, 2, 3]) == [10, 2, 3]
        assert unstructure(list[str], ["a"]) == ["aaaaaaaaaa"]
        assert unstructure(tuple[int, ...], (1, 2, 3)) == [10, 2, 3]
        assert unstructure(tuple[str, ...], ("a",)) == ["aaaaaaaaaa"]
        assert unstructure(dict[str, int], {"a": 1, "b": 2}) == {"a": 1, "b": 2}

    @testregister
    def unstructure_hook(ctx: Ctx["[0]", str], data: str) -> str:
        return data * 2

    with ctxure_config(dispatcher=testregister):
        assert unstructure(list[int], [1, 2, 3]) == [10, 2, 3]
        assert unstructure(list[str], ["a"]) == ["aa"]
        assert unstructure(tuple[int, ...], (1, 2, 3)) == [10, 2, 3]
        assert unstructure(tuple[str, ...], ("a",)) == ["aa"]
        assert unstructure(dict[str, int], {"a": 1, "b": 2}) == {"a": 1, "b": 2}

    @testregister
    def unstructure_hook(ctx: Ctx["[0]", Of[tuple]], data: int | str) -> int | str:
        return data * 100

    with ctxure_config(dispatcher=testregister):
        assert unstructure(list[int], [1, 2, 3]) == [10, 2, 3]
        assert unstructure(list[str], ["a"]) == ["aa"]
        assert unstructure(tuple[int, ...], (1, 2, 3)) == [100, 2, 3]
        assert unstructure(dict[str, int], {"a": 1, "b": 2}) == {"a": 1, "b": 2}
        assert unstructure(tuple[str, ...], ("a",)) == ["aa"]

    @testregister
    def unstructure_hook(ctx: Ctx["[1]", Of[tuple]], data: int | str) -> int | str:
        return data * 1000

    with ctxure_config(dispatcher=testregister):
        assert unstructure(list[int], [1, 2, 3]) == [10, 2, 3]
        assert unstructure(list[str], ["a"]) == ["aa"]
        assert unstructure(tuple[int, ...], (1, 2, 3)) == [100, 2000, 3]
        assert unstructure(dict[str, int], {"a": 1, "b": 2}) == {"a": 1, "b": 2}

    @testregister
    def unstructure_hook(ctx: Ctx["[1]", Of[tuple], int], data: int | str) -> int | str:
        return data * 10000

    with ctxure_config(dispatcher=testregister):
        assert unstructure(list[int], [1, 2, 3]) == [10, 2, 3]
        assert unstructure(list[str], ["a"]) == ["aa"]
        assert unstructure(tuple[int, ...], (1, 2, 3)) == [100, 20000, 3]
        assert unstructure(dict[str, int], {"a": 1, "b": 2}) == {"a": 1, "b": 2}


def test_unstructure_hook_item_wildcard(testregister):
    @testregister
    def unstructure_hook(ctx: Ctx["[?]"], data: int) -> int:
        return data * 10

    with ctxure_config(dispatcher=testregister):
        assert unstructure(list[int], [1, 2, 3]) == [10, 20, 30]
        assert unstructure(dict[str, int], {"a": 1, "b": 2}) == {"a": 10, "b": 20}

    @testregister
    def unstructure_hook(ctx: Ctx["[?]", Of[dict]], data: int) -> int:
        return data * 100

    with ctxure_config(dispatcher=testregister):
        assert unstructure(list[int], [1, 2, 3]) == [10, 20, 30]
        assert unstructure(dict[str, int], {"a": 1, "b": 2}) == {"a": 100, "b": 200}


def test_unstructure_hook_key(testregister):
    @testregister
    def unstructure_hook(ctx: Ctx["[~'a']"], data: str) -> str:  # noqa: F821
        return data.upper()

    with ctxure_config(dispatcher=testregister):
        assert unstructure(dict[str, int], {"a": 11, "b": 22}) == {"A": 11, "b": 22}
        assert unstructure(dict[int, int], {1: 11, 2: 22}) == {"1": 11, "2": 22}

    @testregister
    def unstructure_hook(ctx: Ctx["[~1]"], data: int) -> str:
        return "ONE"

    with ctxure_config(dispatcher=testregister):
        assert unstructure(dict[int, int], {1: 11, 2: 22}) == {"ONE": 11, "2": 22}
        assert unstructure(dict[str, int], {"a": 11, "b": 22}) == {"A": 11, "b": 22}

    @testregister
    def unstructure_hook(ctx: Ctx["[~1]", Of[dict]], data: int) -> str:
        return "ONE_OF_DICT"

    with ctxure_config(dispatcher=testregister):
        assert unstructure(dict[int, int], {1: 11, 2: 22}) == {"ONE_OF_DICT": 11, "2": 22}


def test_unstructure_hook_key_wildcard(testregister):
    @testregister
    def unstructure_hook(ctx: Ctx["[~?]"], data: int | str) -> str:
        return str(data) * 3

    with ctxure_config(dispatcher=testregister):
        assert unstructure(list[int], [1, 2, 3]) == [1, 2, 3]
        assert unstructure(dict[int, int], {1: 11, 2: 22}) == {"111": 11, "222": 22}
        assert unstructure(dict[str, int], {"a": 11, "b": 22}) == {"aaa": 11, "bbb": 22}

    @testregister
    def unstructure_hook(ctx: Ctx["[~?]", str], data: str) -> str:
        return data.upper()

    with ctxure_config(dispatcher=testregister):
        assert unstructure(list[int], [1, 2, 3]) == [1, 2, 3]
        assert unstructure(dict[int, int], {1: 11, 2: 22}) == {"111": 11, "222": 22}
        assert unstructure(dict[str, int], {"a": 11, "b": 22}) == {"A": 11, "B": 22}


def test_unstructure_dict_value_context_tracks_current_unstructured_key(testregister):
    @testregister
    def unstructure_hook(ctx: Ctx[str, "[~'a']"], data: str) -> str:  # noqa: F821
        return get_extra(ctx)["unstructured_key"]

    @testregister
    def unstructure_hook(ctx: Ctx[int, "['a']"], data: int) -> str:  # noqa: F821
        return ctx.unstructured_path

    with ctxure_config(dispatcher=testregister):
        assert unstructure(dict[str, int], {"a": 1}, extra={"unstructured_key": "x"}) == {"x": "$['x']"}
        assert unstructure(dict[str, int], {"a": 1}, extra={"unstructured_key": "y"}) == {"y": "$['y']"}
        assert unstructure(dict[str, int], {"a": 1}, extra={"unstructured_key": "x"}) == {"x": "$['x']"}


def test_unstructure_dict_key_context_distinguishes_equal_structured_keys(testregister):
    seen = []

    @testregister
    def unstructure_hook(ctx: Ctx[int, "[~?]"], data: int) -> str:
        seen.append(ctx.structured_path)
        return str(data)

    with ctxure_config(dispatcher=testregister):
        assert unstructure(dict[int, str], {1: "one"}) == {"1": "one"}
        assert unstructure(dict[int, str], {True: "true"}) == {"True": "true"}

    assert seen == ["$[~1]", "$[~?]"]


def test_unstructure_hook_newtype(testregister):
    Int = NewType("Int", int)

    @dataclass
    class Foo:
        a: Int

    @testregister
    def unstructure_hook(ctx: Ctx[Int], data: int) -> int:
        return data * 10

    with ctxure_config(dispatcher=testregister):
        assert unstructure(int, 1) == 1
        assert unstructure(Int, Int(1)) == 10
        assert unstructure(list[int], [1, 2]) == [1, 2]
        assert unstructure(list[Int], [Int(1), Int(2)]) == [10, 20]
        assert unstructure(Foo, Foo(Int(1))) == {"a": 10}


def test_unstructure_hook_newtype_supertype_hook(testregister):
    Complex = NewType("Complex", complex)

    @testregister
    def unstructure_hook(ctx: Ctx[complex], data: complex) -> complex:
        return data * 10

    with ctxure_config(dispatcher=testregister):
        with pytest.raises(NoUnstructureHook):
            unstructure(Complex, 1j)


def test_unstructure_hook_newtype_supertype_hook_registered_with_ctx_subtypes(testregister):
    Complex = NewType("Complex", complex)

    @testregister.ctx_subtypes
    def unstructure_hook(ctx: Ctx[complex], data: complex) -> complex:
        return data * 100

    with ctxure_config(dispatcher=testregister):
        assert unstructure(Complex, 1j) == 100j


def test_unstructure_hook_literal(testregister):
    @dataclass
    class Foo:
        a: Literal[1, 2]

    @testregister
    def unstructure_hook(ctx: Ctx[Literal[1, 2]], data: int) -> int:
        if data in [1, 2]:
            return data % 2 + 1
        raise ValidationError(ctx, f"Invalid literal value {data}")

    with ctxure_config(dispatcher=testregister):
        assert unstructure(Literal[1, 2], 1) == 2
        assert unstructure(Literal[1, 2], 2) == 1
        assert unstructure(list[Literal[1, 2]], [1, 2]) == [2, 1]
        assert unstructure(Foo, Foo(1)) == {"a": 2}
        assert unstructure(int, 1) == 1
        assert unstructure(int, 2) == 2

        with pytest.raises(ValidationError):
            unstructure(Literal[1, 2], 3)


def test_unstructure_hook_union(testregister):
    @dataclass
    class Foo:
        a: int | None

    @testregister
    def unstructure_hook(ctx: Ctx[int | None], data: int | None) -> int | None:
        if data is None:
            return None
        return unstructure_default(ctx, data * 10)

    with ctxure_config(dispatcher=testregister):
        assert unstructure(int | None, 1) == 10
        assert unstructure(int | None, None) is None
        assert unstructure(list[int | None], [1, None]) == [10, None]
        assert unstructure(Foo, Foo(1)) == {"a": 10}
        assert unstructure(Foo, Foo(None)) == {"a": None}
        assert unstructure(float | None, 1.1) == 1.1
        assert unstructure(str | None, "a") == "a"
        assert unstructure(int, 1) == 1
        assert unstructure(str, "a") == "a"
        assert unstructure(bool, True) == True

    @testregister
    def unstructure_hook(ctx: Ctx[int | str], data: int | str) -> int | str:
        return data * 3

    with ctxure_config(dispatcher=testregister):
        assert unstructure(int | None, 1) == 10
        assert unstructure(int | None, None) is None
        assert unstructure(list[int | None], [1, None]) == [10, None]
        assert unstructure(Foo, Foo(1)) == {"a": 10}
        assert unstructure(Foo, Foo(None)) == {"a": None}
        assert unstructure(float | None, 1.1) == 1.1
        assert unstructure(str | None, "a") == "a"
        assert unstructure(int, 1) == 1
        assert unstructure(str, "a") == "a"
        assert unstructure(int | str, 1) == 3
        assert unstructure(int | str, "a") == "aaa"

    @testregister
    def unstructure_hook(ctx: Ctx[int], data: int) -> int:
        return data * 5

    with ctxure_config(dispatcher=testregister):
        assert unstructure(int | None, 1) == 50
        assert unstructure(int | None, None) is None
        assert unstructure(list[int | None], [1, None]) == [50, None]
        assert unstructure(Foo, Foo(1)) == {"a": 50}
        assert unstructure(Foo, Foo(None)) == {"a": None}
        assert unstructure(float | None, 1.1) == 1.1
        assert unstructure(str | None, "a") == "a"
        assert unstructure(int, 1) == 5
        assert unstructure(str, "a") == "a"
        assert unstructure(int | str, 1) == 3
        assert unstructure(int | str, "a") == "aaa"


def test_unstructure_hook_union_over_identity(testregister):
    @dataclass
    class Foo:
        x: int

    @testregister
    def unstructure_hook(ctx: Ctx[Foo], data: Foo) -> int:
        return data.x

    with ctxure_config(dispatcher=testregister):
        assert unstructure(Foo | int, Foo(5)) == 5
        assert unstructure(int | Foo, Foo(5)) == 5
        assert unstructure(Foo | str, "hi") == "hi"


def test_unstructure_hook_dataclass_union(testregister):
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
    def unstructure_hook(ctx: Ctx[Foo | Bar], data: Foo) -> dict:
        return {"a": data.a * 10}

    @testregister
    def unstructure_hook(ctx: Ctx[Foo], data: Foo) -> dict:
        return {"a": data.a * 100}

    with ctxure_config(dispatcher=testregister):
        assert unstructure(Foo, Foo(1)) == {"a": 100}
        assert unstructure(Bar, Bar(1)) == {"a": 1}
        assert unstructure(Foo | Bar, Foo(1)) == {"a": 10}
        assert unstructure(list[Foo | Bar], [Foo(1), Foo(2)]) == [{"a": 10}, {"a": 20}]
        assert unstructure(Foo | Baz, Foo(1)) == {"a": 100}
        assert unstructure(Foo | Baz, Baz(2)) == {"b": 2}
        assert unstructure(Bar | Baz, Bar(2)) == {"a": 2}


def test_unstructure_hook_for_union_fired_by_default_union_handler(testregister):
    @testregister.ctx_subtypes
    def unstructure_hook(ctx: Ctx[int | str], data: int | str) -> str:
        return "int | str"

    with ctxure_config(dispatcher=testregister):
        with pytest.raises(AmbiguousUnion):
            unstructure(int | str | float, 1)


def test_unstructure_hook_for_typeddict_fired_by_default_union_handler(testregister):
    class Foo(TypedDict):
        tag: Literal["foo"]
        a: int

    class Bar(TypedDict):
        tag: Literal["bar"]
        b: int

    @testregister
    def unstructure_hook(ctx: Ctx[Foo], data: dict) -> dict:
        return {"a": data["a"] * 10}

    with ctxure_config(dispatcher=testregister):
        assert unstructure(Foo | Bar, {"a": 1, "tag": "foo"}) == {"a": 10}
        assert unstructure(Foo | Bar, {"b": 2, "tag": "bar"}) == {"b": 2, "tag": "bar"}


def test_unstructure_hook_type_ctx_invariance(testregister):
    @dataclass
    class Base:
        a: int

    @dataclass
    class Child(Base):
        b: str

    @testregister
    def unstructure_hook(ctx: Ctx[Base], data: Base) -> dict:
        return {"a": data.a * 10}

    with ctxure_config(dispatcher=testregister):
        assert unstructure(Base, Base(1)) == {"a": 10}
        assert unstructure(Child, Child(1, "x")) == {"a": 1, "b": "x"}

    @testregister
    def unstructure_hook(ctx: Ctx[Child], data: Child) -> dict:
        return {"a": data.a * 100, "b": data.b.upper()}

    with ctxure_config(dispatcher=testregister):
        assert unstructure(Base, Base(1)) == {"a": 10}
        assert unstructure(Child, Child(1, "x")) == {"a": 100, "b": "X"}


def test_unstructure_hook_disambiguate_by_data_type(testregister):
    @testregister
    def unstructure_hook(ctx: Ctx[Sequence[int]], data: list) -> list[int]:
        return [x * 10 for x in data]

    @testregister
    def unstructure_hook(ctx: Ctx[Sequence[int]], data: tuple) -> list[int]:
        return [x * 100 for x in data]

    with ctxure_config(dispatcher=testregister):
        assert unstructure(Sequence[int], [1, 2]) == [10, 20]
        assert unstructure(Sequence[int], (1, 2)) == [100, 200]


def test_unstructure_hook_failure(testregister):
    class Custom:
        pass

    with ctxure_config(dispatcher=testregister):
        with pytest.raises(NoUnstructureHook):
            unstructure(Custom, Custom())


def test_unstructure_with_stripped_ctx_routes_to_type_only_hook(testregister):
    @dataclass
    class Inner:
        val: str

    @dataclass
    class Wrapper:
        inner: Inner

    calls: list[str] = []

    @testregister
    def unstructure_hook(ctx: Ctx[Inner], data: Inner) -> dict:
        calls.append("type-only")
        return {"val": data.val.upper()}

    @testregister
    def unstructure_hook(ctx: Ctx[Inner, Of[Wrapper]], data: Inner) -> dict:
        calls.append("of-wrapper")
        result = unstructure_by_type(ctx, data)
        return {**result, "val": result["val"] + "_wrapped"}

    with ctxure_config(dispatcher=testregister):
        assert unstructure(Wrapper, Wrapper(Inner("hello"))) == {"inner": {"val": "HELLO_wrapped"}}
        assert calls == ["of-wrapper", "type-only"]


def test_unstructure_with_stripped_ctx_should_not_restore_child_context(testregister):
    @dataclass
    class Inner:
        val: str

    @dataclass
    class Wrapper:
        inner: Inner

    @testregister
    def unstructure_hook(ctx: Ctx[str, Under[Wrapper]], data: str) -> str:
        return data.upper()

    @testregister
    def unstructure_hook(ctx: Ctx[str, "$.inner.val"], data: str) -> str:
        return data.upper()

    @testregister
    def unstructure_hook(ctx: Ctx[Inner], data: Inner) -> dict:
        return unstructure_default(ctx, data)

    @testregister
    def unstructure_hook(ctx: Ctx[Inner, Of[Wrapper]], data: Inner) -> dict:
        result = unstructure_by_type(ctx, data)
        return {**result, "val": result["val"] + "_wrapped"}

    with ctxure_config(dispatcher=testregister):
        assert unstructure(Wrapper, Wrapper(Inner("hello"))) == {"inner": {"val": "hello_wrapped"}}


def test_unstructure_with_stripped_ctx_child_get_owner(testregister):
    @dataclass
    class Inner:
        val: str

    @dataclass
    class Wrapper:
        inner: Inner

    @testregister
    def unstructure_hook(ctx: Ctx[str, Of[Inner]], data: str) -> str:
        return data.upper()

    @testregister
    def unstructure_hook(ctx: Ctx[Inner], data: Inner) -> dict:
        return unstructure_default(ctx, data)

    @testregister
    def unstructure_hook(ctx: Ctx[Inner, Of[Wrapper]], data: Inner) -> dict:
        result = unstructure_by_type(ctx, data)
        return {**result, "val": result["val"] + "_wrapped"}

    with ctxure_config(dispatcher=testregister):
        assert unstructure(Wrapper, Wrapper(Inner("hello"))) == {"inner": {"val": "HELLO_wrapped"}}


def test_unstructure_by_type_redispatches_per_data_type(testregister):
    @dataclass
    class Target:
        x: int

    @testregister
    def unstructure_hook(ctx: Ctx[Target], data: Target) -> str:
        return f"T:{data.x}"

    @testregister
    def unstructure_hook(ctx: Ctx[Target], data: dict) -> str:
        return f"D:{data['x']}"

    @dataclass
    class Owner:
        inner: Target

    @testregister
    def unstructure_hook(ctx: Ctx[Target, Of[Owner]], data: Target) -> object:
        if data.x % 2:
            return unstructure_by_type(ctx, {"x": data.x})  # dict path
        return unstructure_by_type(ctx, data)  # Target path

    with ctxure_config(dispatcher=testregister):
        assert unstructure(Owner, Owner(Target(4))) == {"inner": "T:4"}
        assert unstructure(Owner, Owner(Target(5))) == {"inner": "D:5"}
        assert unstructure(Owner, Owner(Target(6))) == {"inner": "T:6"}


def test_unstructure_hook_ambiguous_at_union_member(testregister):
    @testregister.ctx_subtypes
    def unstructure_hook(ctx: Ctx[int | float], data: int) -> int:
        return data * 2

    @testregister.ctx_subtypes
    def unstructure_hook(ctx: Ctx[int | bytes], data: int) -> int:
        return data * 3

    with ctxure_config(dispatcher=testregister):
        with pytest.raises(AmbiguousUnion):
            unstructure(int | str, 1)


def test_unstructure_hook_union_preserve_context(testregister):
    @dataclass
    class Foo:
        a: list[int | str]

    @testregister
    def unstructure_hook(ctx: Ctx[int, Under[Foo], "$.a[1]"], data: int) -> int:
        return data * 10

    with ctxure_config(dispatcher=testregister):
        assert unstructure(Foo, Foo([1, 2, 3])) == {"a": [1, 20, 3]}
        assert unstructure(Foo, Foo([1, "a", 3])) == {"a": [1, "a", 3]}


def test_unstructure_hook_under_root(testregister):
    @testregister
    def unstructure_hook(ctx: Ctx[int, Under[int]], data: int) -> int:
        return data * 10

    with ctxure_config(dispatcher=testregister):
        assert unstructure(int, 5) == 50


def test_unstructure_hook_under_matches_nested_position_with_inherited_root(testregister):
    @testregister
    def unstructure_hook(ctx: Ctx[int, Under[list[int]]], data: int) -> int:
        return data * 10

    with ctxure_config(dispatcher=testregister):
        assert unstructure(list[int], [1, 2]) == [10, 20]
        assert unstructure(int, 5) == 5


def test_unstructure_hook_under_preserved_through_union_narrowing_at_root(testregister):
    @testregister
    def unstructure_hook(ctx: Ctx[int, Under[int | str]], data: int) -> int:
        return data * 10

    with ctxure_config(dispatcher=testregister):
        assert unstructure(int | str, 5) == 50


def test_unstructure_hook_under_preserved_through_dataclass_union_dispatch_at_root(testregister):
    @dataclass
    class A:
        a: int

    @dataclass
    class B:
        b: int

    @testregister
    def unstructure_hook(ctx: Ctx[int, Under[A | B]], data: int) -> int:
        return data * 10

    with ctxure_config(dispatcher=testregister):
        assert unstructure(A | B, A(5)) == {"a": 50}
        assert unstructure(A | B, B(7)) == {"b": 70}


def test_unstructure_default_preserves_root(testregister):
    saw_roots = []

    @testregister
    def unstructure_hook(ctx: Ctx[int], data: int) -> int:
        c = ctx
        while c.parent is not None:
            c = c.parent
        saw_roots.append(c.structured_type)
        return unstructure_default(ctx, data)

    with ctxure_config(dispatcher=testregister):
        unstructure(list[int], [1, 2])

    assert saw_roots == [list[int], list[int]]


def test_unstructure_extra_visible_through_root_level_typeddict_union(testregister):
    class TDA(TypedDict):
        a: int

    class TDB(TypedDict):
        b: int

    seen = []

    @testregister
    def unstructure_hook(ctx: Ctx[int], data: int) -> int:
        seen.append(get_extra(ctx))
        return unstructure_default(ctx, data)

    with ctxure_config(dispatcher=testregister):
        unstructure(TDA | TDB, {"a": 5}, extra={"tag": "root-union"})

    assert seen == [{"tag": "root-union"}]


def test_unstructure_hook_literal_data(testregister):
    @testregister
    def unstructure_hook(ctx: Ctx[Literal[1, 2]], data: Literal[1, 2]) -> int:
        return data * 10

    with ctxure_config(dispatcher=testregister):
        assert unstructure(Literal[1, 2], 1) == 10
        assert unstructure(Literal[1, 2], 2) == 20
        assert unstructure(Literal[1], 1) == 1
        assert unstructure(int, 3) == 3

    @testregister
    def unstructure_hook(ctx: Ctx[int], data: int) -> int:
        return data * 100

    with ctxure_config(dispatcher=testregister):
        assert unstructure(Literal[1, 2], 1) == 10
        assert unstructure(Literal[1, 2], 2) == 20
        assert unstructure(Literal[1], 1) == 1
        assert unstructure(int, 3) == 300

    with ctxure_config(dispatcher=testregister.copy()):
        assert unstructure(Literal[1, 2], 1) == 10
        assert unstructure(Literal[1, 2], 2) == 20
        assert unstructure(Literal[1], 1) == 1
        assert unstructure(int, 3) == 300


def test_unstructure_hook_multitype_literal_data(testregister):
    class Foo(Enum):
        A = "A"

    @testregister
    def unstructure_hook(ctx: Ctx[Literal[1, "a", Foo.A]], data: Literal[1, "a", Foo.A]) -> int:
        return -1

    with ctxure_config(dispatcher=testregister):
        assert unstructure(Literal[1, "a", Foo.A], 1) == -1
        assert unstructure(Literal[1, "a", Foo.A], "a") == -1
        assert unstructure(Literal[1, "a", Foo.A], Foo.A) == -1
        assert unstructure(Literal[1, "a", Foo.A], "b") == "b"
        assert unstructure(Literal[1, "a", Foo.A], "A") == "A"


def test_unstructure_union_literal_hook_checks_membership(testregister):
    @testregister
    def unstructure_hook(ctx: Ctx[Literal["a"]], data: str) -> str:
        return "literal-a"

    target = Literal["a"] | str

    with ctxure_config(dispatcher=testregister):
        assert unstructure(target, "b") == "b"
        assert unstructure(target, "a") == "literal-a"
        assert unstructure(target, "b") == "b"


def test_unstructure_hook_field_get_data(testregister):
    @dataclass
    class Foo:
        a: int
        b: int  # hook-free sibling

    seen = []

    @testregister
    def unstructure_hook(ctx: Ctx[".a", Of[Foo], int], data: int) -> int:
        seen.append(get_data(ctx))
        return data * 2

    with ctxure_config(dispatcher=testregister):
        assert unstructure(Foo, Foo(3, 1)) == {"a": 6, "b": 1}
        assert unstructure(Foo, Foo(5, 2)) == {"a": 10, "b": 2}

    assert seen == [3, 5]


def test_unstructure_hook_get_parent_data(testregister):
    @dataclass
    class Inner:
        a: int
        b: int

    @dataclass
    class Outer:
        inner: Inner  # no hook on Inner itself → is_hook_free=True → bypassed

    seen = []

    @testregister
    def unstructure_hook(ctx: Ctx[".a", Of[Inner], int], data: int) -> int:
        assert ctx.parent is not None
        seen.append(get_data(ctx.parent))  # should be the current Inner instance
        return data * 2

    with ctxure_config(dispatcher=testregister):
        assert unstructure(Outer, Outer(Inner(3, 1))) == {"inner": {"a": 6, "b": 1}}
        assert unstructure(Outer, Outer(Inner(5, 2))) == {"inner": {"a": 10, "b": 2}}

    assert seen == [Inner(3, 1), Inner(5, 2)]


def test_unstructure_hook_get_parent_data_list(testregister):
    @dataclass
    class Outer:
        items: list[int]  # no hook on list → bypassed by Outer until propagation

    seen = []

    @testregister
    def unstructure_hook(ctx: Ctx["[0]", int], data: int) -> int:
        assert ctx.parent is not None
        seen.append(get_data(ctx.parent))  # should be the current list being unstructured
        return data * 2

    with ctxure_config(dispatcher=testregister):
        assert unstructure(Outer, Outer([3, 4])) == {"items": [6, 4]}
        assert unstructure(Outer, Outer([5, 6])) == {"items": [10, 6]}

    assert seen == [[3, 4], [5, 6]]


def test_unstructure_hook_enum_type_ctx(testregister):
    class Foo(Enum):
        A = 1
        B = 2

    class Bar(Enum):
        A = 1
        B = 2

    @testregister
    def unstructure_hook(ctx: Ctx[Foo], data: Foo) -> str:
        return "a" if data == Foo.A else "b"

    with ctxure_config(testregister):
        assert unstructure(Foo, Foo.A) == "a"
        assert unstructure(Foo, Foo.B) == "b"
        assert unstructure(Bar, Bar.A) == 1
        assert unstructure(Bar, Bar.B) == 2


def test_unstructure_hook_typeddict_ctx(testregister):
    class Foo(TypedDict):
        a: str
        b: str

    @testregister
    def unstructure_hook(ctx: Ctx[Foo], data: dict) -> str:
        return f"{data['a']}:{data['b']}"

    with ctxure_config(testregister):
        assert unstructure(Foo, {"a": "x", "b": "y"}) == "x:y"
        assert unstructure(dict, {"a": "x", "b": "y"}) == {"a": "x", "b": "y"}


def test_unstructure_hook_user_defined_class_ctx(testregister):
    class Foo:
        a: str
        b: str

        def __init__(self, a: str, b: str):
            self.a = a
            self.b = b

    @testregister
    def unstructure_hook(ctx: Ctx[Foo], data: Foo) -> str:
        return f"{data.a}:{data.b}"

    with ctxure_config(testregister):
        assert unstructure(Foo, Foo("x", "y")) == "x:y"


def test_unstructure_default_dataclass_with_keymap(testregister):
    @dataclass
    class Foo:
        a: int
        b: int
        c: int

    keymap = {"b": "B", "c": "C"}

    @testregister
    def unstructure_hook(ctx: Ctx[Foo], data: Foo) -> dict:
        return unstructure_default(ctx, data, keymap)

    with ctxure_config(testregister):
        assert unstructure(Foo, Foo(1, 2, 3)) == {"a": 1, "B": 2, "C": 3}


def test_unstructure_newtype_dict_key_uses_supertype_for_value_path(testregister):
    UserId = NewType("UserId", int)

    @testregister
    def unstructure_hook(ctx: Ctx[str, "$[1]"], data: str) -> str:
        return data.upper()

    with ctxure_config(testregister):
        assert unstructure(dict[UserId, str], {UserId(1): "a"}) == {"1": "A"}


def test_unstructure_default_union_with_keymap_is_not_supported(testregister):
    @dataclass
    class Foo:
        a: int

    @dataclass
    class Bar:
        b: int

    keymap = {"a": "A", "b": "B"}

    @testregister
    def unstructure_hook(ctx: Ctx[Foo | Bar], data: Foo | Bar) -> dict:
        return unstructure_default(ctx, data, keymap)

    with ctxure_config(testregister):
        with pytest.raises(ValidationError, match="keymap is not supported") as e:
            unstructure(Foo | Bar, Foo(1))
        assert e.value.ctx.structured_type == Foo | Bar


def test_unstructure_default_single_key_keypath_is_plain_alias(testregister):
    @dataclass
    class Foo:
        a: int
        b: int

    class Bar(TypedDict):
        a: int
        b: int

    keymap = {"b": KeyPath("B")}

    @testregister
    def unstructure_hook(ctx: Ctx[Foo], data: Foo) -> dict:
        return unstructure_default(ctx, data, keymap)

    @testregister
    def unstructure_hook(ctx: Ctx[Bar], data: dict) -> dict:
        return unstructure_default(ctx, data, keymap)

    with ctxure_config(testregister):
        assert unstructure(Foo, Foo(1, 2)) == {"a": 1, "B": 2}
        assert unstructure(Bar, {"a": 1, "b": 2}) == {"a": 1, "B": 2}


def test_unstructure_default_multikey_keypath_is_not_supported(testregister):
    @dataclass
    class Foo:
        a: int
        b: int

    class Bar(TypedDict):
        a: int
        b: int

    keymap = {"b": KeyPath("x", "b")}

    @testregister
    def unstructure_hook(ctx: Ctx[Foo], data: Foo) -> dict:
        return unstructure_default(ctx, data, keymap)

    @testregister
    def unstructure_hook(ctx: Ctx[Bar], data: dict) -> dict:
        return unstructure_default(ctx, data, keymap)

    with ctxure_config(testregister):
        with pytest.raises(
            ValidationError, match=r"not supported by unstructure_default: 'b' -> KeyPath\('x', 'b'\)"
        ) as e:
            unstructure(Foo, Foo(1, 2))
        assert e.value.ctx.structured_type is Foo

        with pytest.raises(
            ValidationError, match=r"not supported by unstructure_default: 'b' -> KeyPath\('x', 'b'\)"
        ) as e:
            unstructure(Bar, {"a": 1, "b": 2})
        assert e.value.ctx.structured_type is Bar


def test_unstructure_default_ignores_multikey_keypath_for_other_fields(testregister):
    @dataclass
    class Foo:
        a: int

    keymap = {"a": "A", "other": KeyPath("x", "y")}

    @testregister
    def unstructure_hook(ctx: Ctx[Foo], data: Foo) -> dict:
        return unstructure_default(ctx, data, keymap)

    with ctxure_config(testregister):
        assert unstructure(Foo, Foo(1)) == {"A": 1}


def test_unstructure_default_keymap_rejects_invalid_values(testregister):
    @dataclass
    class Foo:
        a: int

    keymap = {"a": ("x", "a")}

    @testregister
    def unstructure_hook(ctx: Ctx[Foo], data: Foo) -> dict:
        return unstructure_default(ctx, data, keymap)  # type: ignore[arg-type]

    with ctxure_config(testregister):
        with pytest.raises(ValidationError, match="keymap value for 'a' must be str or KeyPath"):
            unstructure(Foo, Foo(1))


def test_unstructure_default_keymap_rejects_duplicate_keys(testregister):
    @dataclass
    class Foo:
        a: int
        b: int

    class Bar(TypedDict):
        a: int
        b: int

    keymap = {"a": "x", "b": "x"}

    @testregister
    def unstructure_hook(ctx: Ctx[Foo], data: Foo) -> dict:
        return unstructure_default(ctx, data, keymap)

    @testregister
    def unstructure_hook(ctx: Ctx[Bar], data: dict) -> dict:
        return unstructure_default(ctx, data, keymap)

    with ctxure_config(testregister):
        with pytest.raises(ValidationError, match="keymap maps 'a' and 'b' to the same key 'x'") as e:
            unstructure(Foo, Foo(1, 2))
        assert e.value.ctx.structured_type is Foo

        data = {"a": 1, "b": 2}
        with pytest.raises(ValidationError, match="keymap maps 'a' and 'b' to the same key 'x'") as e:
            unstructure(Bar, data)
        assert e.value.ctx.structured_type is Bar
        assert e.value.data is data


@pytest.mark.parametrize(
    "keymap",
    [
        {"a": "b"},  # `a` is written to "b", and so is the unmapped `b`
        {"a": KeyPath("x"), "b": "x"},  # a single-key KeyPath is the same key as a str
    ],
)
def test_unstructure_default_keymap_rejects_colliding_keys(testregister, keymap):
    @dataclass
    class Foo:
        a: int
        b: int

    @testregister
    def unstructure_hook(ctx: Ctx[Foo], data: Foo) -> dict:
        return unstructure_default(ctx, data, keymap)

    with ctxure_config(testregister):
        with pytest.raises(ValidationError, match="keymap maps 'a' and 'b' to the same key"):
            unstructure(Foo, Foo(1, 2))


def test_unstructure_default_keymap_ignores_duplicates_for_other_fields(testregister):
    @dataclass
    class Foo:
        a: int
        b: int

    keymap = {"a": "A", "other1": "x", "other2": "x"}

    @testregister
    def unstructure_hook(ctx: Ctx[Foo], data: Foo) -> dict:
        return unstructure_default(ctx, data, keymap)

    with ctxure_config(testregister):
        assert unstructure(Foo, Foo(1, 2)) == {"A": 1, "b": 2}


def test_unstructure_default_typeddict_with_keymap(testregister):
    class Foo(TypedDict):
        a: int
        b: int
        c: int

    keymap = {"b": "B", "c": "C"}

    @testregister
    def unstructure_hook(ctx: Ctx[Foo], data: dict) -> dict:
        return unstructure_default(ctx, data, keymap)

    with ctxure_config(testregister):
        assert unstructure(Foo, {"a": 1, "b": 2, "c": 3}) == {"a": 1, "B": 2, "C": 3}


def test_unstructure_default_typeddict_extra_items_with_keymap(testregister):
    class Foo(ExtTypedDict, extra_items=int):
        a: str
        b: str

    keymap = {"b": "B"}

    @testregister
    def unstructure_hook(ctx: Ctx[Foo], data: dict) -> dict:
        return unstructure_default(ctx, data, keymap)

    with ctxure_config(testregister):
        assert unstructure(Foo, {"a": "x", "b": "y"}) == {"a": "x", "B": "y"}
        assert unstructure(Foo, {"a": "x", "b": "y", "extra": 99}) == {"a": "x", "B": "y", "extra": 99}

        data = {"a": "x", "b": "y", "B": 99}
        with pytest.raises(ValidationError) as e:
            unstructure(Foo, data)
        assert "conflicts with declared field: 'B'" in str(e.value)
        assert e.value.data is data


def test_unstructure_default_with_keymap_dynamic_keymap(testregister):
    @dataclass
    class Foo:
        a: int
        b: int

    @testregister
    def unstructure_hook(ctx: Ctx[Foo], data: Foo) -> Foo:
        keymap = {"b": "B"}
        return unstructure_default(ctx, data, keymap)

    with ctxure_config(testregister):
        for _ in range(100):
            assert unstructure(Foo, Foo(1, 2)) == {"a": 1, "B": 2}

    keymap1 = {"b": "B"}
    keymap2 = {"b": "_b"}

    @testregister
    def unstructure_hook(ctx: Ctx[Foo], data: Foo) -> dict:
        km = keymap1 if data.a > 0 else keymap2
        return unstructure_default(ctx, data, km)

    with ctxure_config(testregister):
        assert unstructure(Foo, Foo(1, 2)) == {"a": 1, "B": 2}
        assert unstructure(Foo, Foo(-1, 2)) == {"a": -1, "_b": 2}
        assert unstructure(Foo, Foo(1, 3)) == {"a": 1, "B": 3}
        assert unstructure(Foo, Foo(-1, 3)) == {"a": -1, "_b": 3}


def test_unstructure_hook_newtype_union_with_supertype(testregister):
    Int = NewType("Int", int)

    @testregister.ctx_subtypes
    def unstructure_hook(ctx: Ctx[Int | int], data: int) -> Int:
        return Int(data * 100)

    with ctxure_config(dispatcher=testregister):
        assert unstructure(Int, 1) == 100
        assert unstructure(int, 1) == 100


def test_unstructure_hook_generic_dataclass_union_as_data(testregister):
    T = TypeVar("T")

    @dataclass
    class Foo(Generic[T]):
        a: T

    @testregister
    def unstructure_hook(ctx: Ctx[Foo], data: Foo[int] | Foo[float]) -> dict:
        return {"a": data.a * 10}

    with ctxure_config(dispatcher=testregister):
        assert unstructure(Foo, Foo[int](1)) == {"a": 10}
        assert unstructure(Foo, Foo[int](2)) == {"a": 20}
        assert unstructure(Foo, Foo[float](3.0)) == {"a": 30.0}
        assert unstructure(Foo, Foo[float](5.0)) == {"a": 50.0}


def test_unstructure_hook_reentrance_error(testregister):
    @testregister
    def unstructure_hook(ctx: Ctx[int], data: int) -> int:
        return unstructure(int, data)

    with ctxure_config(dispatcher=testregister):
        with pytest.raises(ReentranceError):
            unstructure(int, 1)


def test_unstructure_hook_get_parent_data_nested_container(testregister):
    # The hook on the elements must stop the inner lists from being bypassed on later calls,
    # otherwise the inner list's recorded data goes stale.
    seen = []

    @testregister
    def unstructure_hook(ctx: Ctx[int], data: int) -> int:
        assert ctx.parent is not None
        seen.append(get_data(ctx.parent))
        return data

    with ctxure_config(dispatcher=testregister):
        assert unstructure(list[list[int]], [[1]]) == [[1]]
        assert unstructure(list[list[int]], [[2]]) == [[2]]

    assert seen == [[1], [2]]
