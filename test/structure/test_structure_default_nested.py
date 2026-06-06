from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Generic, TypedDict, TypeVar

import pytest

from ctxure import MissingFields, NoStructureHook, structure


def test_structure_default_list_of_complex_type():
    class Foo(Enum):
        A = 1
        B = 2

    @dataclass
    class Bar:
        a: int

    assert structure(list[list[int]], [[]]) == [[]]
    assert structure(list[list[date]], [["2025-01-01"]]) == [[date(2025, 1, 1)]]
    assert structure(list[list[int]], [[1, 2], [3]]) == [[1, 2], [3]]

    assert structure(list[tuple[()]], [()]) == [()]
    with pytest.raises(NoStructureHook):
        structure(list[tuple[()]], [(1,)])
    assert structure(list[tuple[int, ...]], [(1, 2), (1, 2, 3)]) == [(1, 2), (1, 2, 3)]
    assert structure(list[tuple[int, Path]], [(1, "/a"), (1, "/b")]) == [(1, Path("/a")), (1, Path("/b"))]

    assert structure(list[set[Foo]], [set([])]) == [set()]
    assert structure(list[set[Foo]], [{1, 2}, {1}, {2}]) == [{Foo.A, Foo.B}, {Foo.A}, {Foo.B}]
    assert structure(list[frozenset[Foo]], [{1, 2}, {1}, {2}]) == [
        frozenset({Foo.A, Foo.B}),
        frozenset({Foo.A}),
        frozenset({Foo.B}),
    ]

    assert structure(list[dict[Foo, Bar]], [{}]) == [{}]
    assert structure(list[dict[Foo, Bar]], [{1: {"a": 10}, 2: {"a": 20}}]) == [{Foo.A: Bar(10), Foo.B: Bar(20)}]

    assert structure(list[list[Bar]], [[]]) == [[]]
    assert structure(list[list[Bar]], [[{"a": 0}, {"a": 1}], [{"a": 2}]]) == [[Bar(0), Bar(1)], [Bar(2)]]

    with pytest.raises(NoStructureHook) as e:
        structure(list[list[int]], [[1, "a"]])
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$[0][1]"
    assert e.value.ctx.unstructured_path == "$[0][1]"
    assert e.value.data == "a"

    with pytest.raises(NoStructureHook) as e:
        structure(list[list[Bar]], [[{"a": 0}], [{"a": "x"}]])
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$[1][0].a"
    assert e.value.ctx.unstructured_path == "$[1][0]['a']"
    assert e.value.data == "x"


def test_structure_default_tuple_of_complex_type():
    class Foo(Enum):
        A = 1
        B = 2

    @dataclass
    class Bar:
        a: int

    assert structure(tuple[list[int]], ([],)) == ([],)
    assert structure(tuple[tuple[()]], ((),)) == ((),)
    assert structure(tuple[tuple[(int, str)]], ((1, "a"),)) == ((1, "a"),)
    assert structure(tuple[list[int], list[str]], ([1], ["a"])) == ([1], ["a"])
    assert structure(tuple[set[Foo], dict[str, Bar]], ({1, 2}, {"x": {"a": 5}})) == ({Foo.A, Foo.B}, {"x": Bar(5)})

    assert structure(tuple[list[int], ...], ([], [])) == ([], [])
    assert structure(tuple[list[int], ...], ((), ())) == ([], [])
    assert structure(tuple[list[int], ...], ([1], [2, 3])) == ([1], [2, 3])
    assert structure(tuple[list[int], ...], ((1,), (2, 3))) == ([1], [2, 3])

    assert structure(tuple[tuple[int, ...], ...], ((), (1,), (1, 2))) == ((), (1,), (1, 2))
    assert structure(tuple[tuple[int, str], ...], ((1, "a"),)) == ((1, "a"),)
    assert structure(tuple[tuple[int, str], ...], ([1, "a"],)) == ((1, "a"),)

    assert structure(tuple[set[Foo], ...], (set(), {1, 2})) == (set(), {Foo.A, Foo.B})
    assert structure(tuple[frozenset[Foo], ...], ({1}, {2})) == (frozenset({Foo.A}), frozenset({Foo.B}))

    assert structure(tuple[dict[Foo, Bar], ...], ({},)) == ({},)
    assert structure(tuple[dict[Foo, Bar], ...], ({1: {"a": 10}}, {2: {"a": 20}})) == (
        {Foo.A: Bar(10)},
        {Foo.B: Bar(20)},
    )

    assert structure(tuple[list[Bar], ...], ([],)) == ([],)
    assert structure(tuple[list[Bar], ...], ([{"a": 0}], [{"a": 1}, {"a": 2}])) == ([Bar(0)], [Bar(1), Bar(2)])

    with pytest.raises(NoStructureHook) as e:
        structure(tuple[list[int], ...], ([1, "a"],))
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$[0][1]"
    assert e.value.ctx.unstructured_path == "$[0][1]"
    assert e.value.data == "a"

    with pytest.raises(NoStructureHook) as e:
        structure(tuple[list[Bar], ...], ([{"a": 0}], [{"a": "x"}]))
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$[1][0].a"
    assert e.value.ctx.unstructured_path == "$[1][0]['a']"
    assert e.value.data == "x"


def test_structure_default_set_of_complex_type():
    class Foo(Enum):
        A = 1
        B = 2

    assert structure(set[frozenset[int]], [frozenset(), frozenset({1})]) == {frozenset(), frozenset({1})}
    assert structure(set[frozenset[int]], [frozenset({1, 2}), frozenset({3})]) == {frozenset({1, 2}), frozenset({3})}

    assert structure(set[tuple[int, ...]], [(1,), (1, 2)]) == {(1,), (1, 2)}
    assert structure(set[tuple[int, str]], [(1, "a"), (2, "b")]) == {(1, "a"), (2, "b")}

    assert structure(set[frozenset[Foo]], [{1, 2}, {1}]) == {frozenset({Foo.A, Foo.B}), frozenset({Foo.A})}

    with pytest.raises(NoStructureHook) as e:
        structure(set[frozenset[int]], [frozenset({1, "a"})])
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$[?][?]"
    assert e.value.ctx.unstructured_path == "$[0][?]"
    assert e.value.data == "a"

    with pytest.raises(NoStructureHook) as e:
        structure(set[tuple[int, str]], [(1, "a"), (2, 3)])
    assert e.value.ctx.structured_type is str
    assert e.value.ctx.structured_path == "$[?][1]"
    assert e.value.ctx.unstructured_path == "$[1][1]"
    assert e.value.data == 3


def test_structure_default_frozenset_of_complex_type():
    class Foo(Enum):
        A = 1
        B = 2

    assert structure(frozenset[frozenset[int]], [frozenset(), frozenset({1})]) == frozenset(
        {frozenset(), frozenset({1})}
    )
    assert structure(frozenset[frozenset[int]], [frozenset({1, 2}), frozenset({3})]) == frozenset(
        {frozenset({1, 2}), frozenset({3})}
    )

    assert structure(frozenset[tuple[int, ...]], [(1,), (1, 2)]) == frozenset({(1,), (1, 2)})
    assert structure(frozenset[tuple[int, str]], [(1, "a"), (2, "b")]) == frozenset({(1, "a"), (2, "b")})

    assert structure(frozenset[frozenset[Foo]], [{1, 2}, {1}]) == frozenset(
        {frozenset({Foo.A, Foo.B}), frozenset({Foo.A})}
    )

    with pytest.raises(NoStructureHook) as e:
        structure(frozenset[frozenset[int]], [frozenset({1, "a"})])
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$[?][?]"
    assert e.value.ctx.unstructured_path == "$[0][?]"
    assert e.value.data == "a"

    with pytest.raises(NoStructureHook) as e:
        structure(frozenset[tuple[int, str]], [(1, "a"), (2, 3)])
    assert e.value.ctx.structured_type is str
    assert e.value.ctx.structured_path == "$[?][1]"
    assert e.value.ctx.unstructured_path == "$[1][1]"
    assert e.value.data == 3


def test_structure_default_dict_of_complex_type():
    class Foo(Enum):
        A = 1
        B = 2

    @dataclass
    class Bar:
        a: int

    assert structure(dict[str, list[int]], {}) == {}
    assert structure(dict[str, list[int]], {"x": []}) == {"x": []}
    assert structure(dict[str, list[int]], {"x": [1], "y": [2, 3]}) == {"x": [1], "y": [2, 3]}

    assert structure(dict[str, dict[str, int]], {"a": {}}) == {"a": {}}
    assert structure(dict[str, dict[str, int]], {"a": {"b": 1}}) == {"a": {"b": 1}}

    assert structure(dict[str, set[Foo]], {"x": {1, 2}, "y": {1}}) == {"x": {Foo.A, Foo.B}, "y": {Foo.A}}
    assert structure(dict[str, frozenset[Foo]], {"x": {1}}) == {"x": frozenset({Foo.A})}

    assert structure(dict[str, list[Bar]], {"items": []}) == {"items": []}
    assert structure(dict[str, list[Bar]], {"items": [{"a": 1}, {"a": 2}]}) == {"items": [Bar(1), Bar(2)]}

    assert structure(dict[Foo, list[int]], {1: [10], 2: [20, 30]}) == {Foo.A: [10], Foo.B: [20, 30]}

    assert structure(dict[str, dict[Foo, Bar]], {"data": {1: {"a": 5}}}) == {"data": {Foo.A: Bar(5)}}

    with pytest.raises(NoStructureHook) as e:
        structure(dict[str, list[int]], {"x": [1, "a"]})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$['x'][1]"
    assert e.value.ctx.unstructured_path == "$['x'][1]"
    assert e.value.data == "a"

    with pytest.raises(NoStructureHook) as e:
        structure(dict[str, list[Bar]], {"x": [{"a": 0}], "y": [{"a": "z"}]})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$['y'][0].a"
    assert e.value.ctx.unstructured_path == "$['y'][0]['a']"
    assert e.value.data == "z"

    with pytest.raises(NoStructureHook) as e:
        structure(dict[Foo, list[int]], {1: [1, "x"]})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$[Foo.A][1]"
    assert e.value.ctx.unstructured_path == "$[1][1]"
    assert e.value.data == "x"


def test_structure_default_dataclass_with_complex_fields():
    class Foo(Enum):
        A = 1
        B = 2

    @dataclass
    class Bar:
        a: int

    @dataclass
    class Baz:
        items: list[int]

    assert structure(Baz, {"items": []}) == Baz([])
    assert structure(Baz, {"items": [1, 2, 3]}) == Baz([1, 2, 3])

    @dataclass
    class Qux:
        data: dict[str, Bar]

    assert structure(Qux, {"data": {}}) == Qux({})
    assert structure(Qux, {"data": {"x": {"a": 10}}}) == Qux({"x": Bar(10)})

    @dataclass
    class Nested:
        values: list[list[int]]
        mapping: dict[Foo, Bar]

    assert structure(Nested, {"values": [[]], "mapping": {}}) == Nested([[]], {})
    assert structure(Nested, {"values": [[1, 2], [3]], "mapping": {1: {"a": 5}}}) == Nested(
        [[1, 2], [3]], {Foo.A: Bar(5)}
    )

    @dataclass
    class Container:
        bars: list[Bar]
        tags: set[Foo]

    assert structure(Container, {"bars": [], "tags": []}) == Container([], set())
    assert structure(Container, {"bars": [{"a": 1}], "tags": {1, 2}}) == Container([Bar(1)], {Foo.A, Foo.B})

    @dataclass
    class DeepNested:
        matrix: list[list[list[int]]]

    assert structure(DeepNested, {"matrix": [[[]]]}) == DeepNested([[[]]])
    assert structure(DeepNested, {"matrix": [[[1, 2]], [[3]]]}) == DeepNested([[[1, 2]], [[3]]])

    with pytest.raises(NoStructureHook) as e:
        structure(Baz, {"items": [1, "a"]})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$.items[1]"
    assert e.value.ctx.unstructured_path == "$['items'][1]"
    assert e.value.data == "a"

    with pytest.raises(NoStructureHook) as e:
        structure(Qux, {"data": {"x": {"a": "invalid"}}})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$.data['x'].a"
    assert e.value.ctx.unstructured_path == "$['data']['x']['a']"
    assert e.value.data == "invalid"

    with pytest.raises(NoStructureHook) as e:
        structure(Nested, {"values": [[1, "x"]], "mapping": {}})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$.values[0][1]"
    assert e.value.ctx.unstructured_path == "$['values'][0][1]"
    assert e.value.data == "x"


def test_structure_default_nested_dataclass_with_default():
    @dataclass
    class Foo:
        a: int

    @dataclass
    class Bar:
        b: Foo = field(default_factory=lambda: Foo(1))

    assert structure(Bar, {}) == Bar(Foo(1))
    assert structure(Bar, {"b": {"a": 10}}) == Bar(Foo(10))


def test_structure_default_typeddict_with_complex_fields():
    class Foo(Enum):
        A = 1
        B = 2

    @dataclass
    class Bar:
        a: int

    class Simple(TypedDict):
        items: list[int]

    assert structure(Simple, {"items": []}) == {"items": []}
    assert structure(Simple, {"items": [1, 2, 3]}) == {"items": [1, 2, 3]}

    class WithMapping(TypedDict):
        data: dict[str, Bar]

    assert structure(WithMapping, {"data": {}}) == {"data": {}}
    assert structure(WithMapping, {"data": {"x": {"a": 10}}}) == {"data": {"x": Bar(10)}}

    class Nested(TypedDict):
        values: list[list[int]]
        mapping: dict[Foo, Bar]

    assert structure(Nested, {"values": [[]], "mapping": {}}) == {"values": [[]], "mapping": {}}
    assert structure(Nested, {"values": [[1, 2], [3]], "mapping": {1: {"a": 5}}}) == {
        "values": [[1, 2], [3]],
        "mapping": {Foo.A: Bar(5)},
    }

    class Outer(TypedDict):
        inner: Simple

    assert structure(Outer, {"inner": {"items": [1]}}) == {"inner": {"items": [1]}}

    @dataclass
    class HasTD:
        payload: Simple

    assert structure(HasTD, {"payload": {"items": [1, 2]}}) == HasTD({"items": [1, 2]})

    assert structure(list[Simple], [{"items": [1]}, {"items": [2, 3]}]) == [{"items": [1]}, {"items": [2, 3]}]
    assert structure(dict[str, Simple], {"a": {"items": [1]}}) == {"a": {"items": [1]}}

    T = TypeVar("T")

    class GenTD(TypedDict, Generic[T]):
        x: T

    assert structure(list[GenTD[int]], [{"x": 1}, {"x": 2}]) == [{"x": 1}, {"x": 2}]

    with pytest.raises(NoStructureHook) as e:
        structure(Simple, {"items": [1, "a"]})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$.items[1]"
    assert e.value.ctx.unstructured_path == "$['items'][1]"
    assert e.value.data == "a"

    with pytest.raises(NoStructureHook) as e:
        structure(WithMapping, {"data": {"x": {"a": "invalid"}}})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$.data['x'].a"
    assert e.value.ctx.unstructured_path == "$['data']['x']['a']"
    assert e.value.data == "invalid"

    with pytest.raises(MissingFields) as e:
        structure(Outer, {})
    assert e.value.ctx.structured_type is Outer
    assert e.value.ctx.structured_path == "$"
    assert e.value.missing == ["inner"]

    with pytest.raises(MissingFields) as e:
        structure(list[Simple], [{"items": [1]}, {}])
    assert e.value.ctx.structured_type is Simple
    assert e.value.ctx.structured_path == "$[1]"
    assert e.value.missing == ["items"]
