from dataclasses import dataclass
from enum import Enum
from typing import Generic, TypedDict, TypeVar

import pytest

from ctxure import NoUnstructureHook, unstructure


def test_unstructure_default_list_of_complex_type():
    class Foo(Enum):
        A = 1
        B = 2

    @dataclass
    class Bar:
        a: int

    assert unstructure(list[list[int]], [[]]) == [[]]
    assert unstructure(list[list[int]], [[1, 2], [3]]) == [[1, 2], [3]]

    assert unstructure(list[tuple[()]], [()]) == [[]]
    with pytest.raises(NoUnstructureHook):
        unstructure(list[tuple[()]], [(1,)])
    assert unstructure(list[tuple[int, ...]], [(1, 2), (1, 2, 3)]) == [[1, 2], [1, 2, 3]]
    assert unstructure(list[tuple[int, str]], [(1, "a"), (2, "b")]) == [[1, "a"], [2, "b"]]

    assert sorted(unstructure(list[set[Foo]], [set()])) == [[]]
    r = unstructure(list[set[Foo]], [{Foo.A, Foo.B}, {Foo.A}])
    assert [sorted(x) for x in r] == [[1, 2], [1]]

    r = unstructure(list[frozenset[Foo]], [frozenset({Foo.A, Foo.B}), frozenset({Foo.A})])
    assert [sorted(x) for x in r] == [[1, 2], [1]]

    assert unstructure(list[dict[Foo, Bar]], [{}]) == [{}]
    assert unstructure(list[dict[Foo, Bar]], [{Foo.A: Bar(10), Foo.B: Bar(20)}]) == [{"1": {"a": 10}, "2": {"a": 20}}]

    assert unstructure(list[list[Bar]], [[]]) == [[]]
    assert unstructure(list[list[Bar]], [[Bar(0), Bar(1)], [Bar(2)]]) == [[{"a": 0}, {"a": 1}], [{"a": 2}]]

    class Custom:
        pass

    custom = Custom()
    with pytest.raises(NoUnstructureHook) as e:
        unstructure(list[list[Custom]], [[custom]])
    assert e.value.ctx.structured_type is Custom
    assert e.value.ctx.structured_path == "$[0][0]"
    assert e.value.ctx.unstructured_path == "$[0][0]"
    assert e.value.data is custom


def test_unstructure_default_tuple_of_complex_type():
    class Foo(Enum):
        A = 1
        B = 2

    @dataclass
    class Bar:
        a: int

    assert unstructure(tuple[list[int]], ([],)) == [[]]
    assert unstructure(tuple[tuple[()]], ((),)) == [[]]
    assert unstructure(tuple[tuple[int, str]], ((1, "a"),)) == [[1, "a"]]
    assert unstructure(tuple[list[int], list[str]], ([1], ["a"])) == [[1], ["a"]]

    assert unstructure(tuple[list[int], ...], ([], [])) == [[], []]
    assert unstructure(tuple[list[int], ...], ([1], [2, 3])) == [[1], [2, 3]]

    assert unstructure(tuple[tuple[int, ...], ...], ((), (1,), (1, 2))) == [[], [1], [1, 2]]
    assert unstructure(tuple[tuple[int, str], ...], ((1, "a"),)) == [[1, "a"]]

    r = unstructure(tuple[set[Foo], ...], (set(), {Foo.A, Foo.B}))
    assert r[0] == []
    assert sorted(r[1]) == [1, 2]

    r = unstructure(tuple[frozenset[Foo], ...], (frozenset({Foo.A}), frozenset({Foo.B})))
    assert r == [[1], [2]]

    assert unstructure(tuple[dict[Foo, Bar], ...], ({},)) == [{}]
    assert unstructure(tuple[dict[Foo, Bar], ...], ({Foo.A: Bar(10)}, {Foo.B: Bar(20)})) == [
        {"1": {"a": 10}},
        {"2": {"a": 20}},
    ]

    assert unstructure(tuple[list[Bar], ...], ([],)) == [[]]
    assert unstructure(tuple[list[Bar], ...], ([Bar(0)], [Bar(1), Bar(2)])) == [[{"a": 0}], [{"a": 1}, {"a": 2}]]

    class Custom:
        pass

    custom = Custom()
    with pytest.raises(NoUnstructureHook) as e:
        unstructure(tuple[list[Custom], ...], ([custom],))
    assert e.value.ctx.structured_type is Custom
    assert e.value.ctx.structured_path == "$[0][0]"
    assert e.value.ctx.unstructured_path == "$[0][0]"
    assert e.value.data is custom


def test_unstructure_default_set_of_complex_type():
    assert unstructure(set[frozenset[int]], {frozenset(), frozenset({1})}) == [[], [1]]
    r = unstructure(set[frozenset[int]], {frozenset({1, 2}), frozenset({3})})
    assert sorted(r, key=sorted) == [[1, 2], [3]]

    r = unstructure(set[tuple[int, ...]], {(1,), (1, 2)})
    assert sorted(r, key=len) == [[1], [1, 2]]

    r = unstructure(set[tuple[int, str]], {(1, "a"), (2, "b")})
    assert sorted(r) == [[1, "a"], [2, "b"]]


def test_unstructure_default_frozenset_of_complex_type():
    r = unstructure(frozenset[frozenset[int]], frozenset({frozenset(), frozenset({1})}))
    assert sorted(r, key=len) == [[], [1]]

    r = unstructure(frozenset[frozenset[int]], frozenset({frozenset({1, 2}), frozenset({3})}))
    assert sorted(r, key=sorted) == [[1, 2], [3]]

    r = unstructure(frozenset[tuple[int, ...]], frozenset({(1,), (1, 2)}))
    assert sorted(r, key=len) == [[1], [1, 2]]

    r = unstructure(frozenset[tuple[int, str]], frozenset({(1, "a"), (2, "b")}))
    assert sorted(r) == [[1, "a"], [2, "b"]]


def test_unstructure_default_dict_of_complex_type():
    class Foo(Enum):
        A = 1
        B = 2

    @dataclass
    class Bar:
        a: int

    assert unstructure(dict[str, list[int]], {}) == {}
    assert unstructure(dict[str, list[int]], {"x": []}) == {"x": []}
    assert unstructure(dict[str, list[int]], {"x": [1], "y": [2, 3]}) == {"x": [1], "y": [2, 3]}

    assert unstructure(dict[str, dict[str, int]], {"a": {}}) == {"a": {}}
    assert unstructure(dict[str, dict[str, int]], {"a": {"b": 1}}) == {"a": {"b": 1}}

    r = unstructure(dict[str, set[Foo]], {"x": {Foo.A, Foo.B}, "y": {Foo.A}})
    assert sorted(r["x"]) == [1, 2]
    assert r["y"] == [1]

    r = unstructure(dict[str, frozenset[Foo]], {"x": frozenset({Foo.A})})
    assert r == {"x": [1]}

    assert unstructure(dict[str, list[Bar]], {"items": []}) == {"items": []}
    assert unstructure(dict[str, list[Bar]], {"items": [Bar(1), Bar(2)]}) == {"items": [{"a": 1}, {"a": 2}]}

    assert unstructure(dict[Foo, list[int]], {Foo.A: [10], Foo.B: [20, 30]}) == {"1": [10], "2": [20, 30]}

    assert unstructure(dict[str, dict[Foo, Bar]], {"data": {Foo.A: Bar(5)}}) == {"data": {"1": {"a": 5}}}

    class Custom:
        pass

    custom = Custom()
    with pytest.raises(NoUnstructureHook) as e:
        unstructure(dict[str, list[Custom]], {"x": [custom]})
    assert e.value.ctx.structured_type is Custom
    assert e.value.ctx.structured_path == "$['x'][0]"
    assert e.value.ctx.unstructured_path == "$['x'][0]"
    assert e.value.data is custom


def test_unstructure_default_dataclass_with_complex_fields():
    class Foo(Enum):
        A = 1
        B = 2

    @dataclass
    class Bar:
        a: int

    @dataclass
    class Baz:
        items: list[int]

    assert unstructure(Baz, Baz([])) == {"items": []}
    assert unstructure(Baz, Baz([1, 2, 3])) == {"items": [1, 2, 3]}

    @dataclass
    class Qux:
        data: dict[str, Bar]

    assert unstructure(Qux, Qux({})) == {"data": {}}
    assert unstructure(Qux, Qux({"x": Bar(10)})) == {"data": {"x": {"a": 10}}}

    @dataclass
    class Nested:
        values: list[list[int]]
        mapping: dict[Foo, Bar]

    assert unstructure(Nested, Nested([[]], {})) == {"values": [[]], "mapping": {}}
    assert unstructure(Nested, Nested([[1, 2], [3]], {Foo.A: Bar(5)})) == {
        "values": [[1, 2], [3]],
        "mapping": {"1": {"a": 5}},
    }

    @dataclass
    class Container:
        bars: list[Bar]
        tags: set[Foo]

    assert unstructure(Container, Container([], set())) == {"bars": [], "tags": []}
    r = unstructure(Container, Container([Bar(1)], {Foo.A, Foo.B}))
    assert r["bars"] == [{"a": 1}]
    assert sorted(r["tags"]) == [1, 2]

    @dataclass
    class DeepNested:
        matrix: list[list[list[int]]]

    assert unstructure(DeepNested, DeepNested([[[]]])) == {"matrix": [[[]]]}
    assert unstructure(DeepNested, DeepNested([[[1, 2]], [[3]]])) == {"matrix": [[[1, 2]], [[3]]]}

    class Custom:
        pass

    custom = Custom()
    with pytest.raises(NoUnstructureHook) as e:
        unstructure(Baz, Baz([1, custom]))  # type: ignore
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$.items[1]"
    assert e.value.ctx.unstructured_path == "$['items'][1]"
    assert e.value.data is custom

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(Qux, Qux({"x": Bar(custom)}))  # type: ignore
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$.data['x'].a"
    assert e.value.ctx.unstructured_path == "$['data']['x']['a']"
    assert e.value.data is custom


def test_unstructure_default_typeddict_with_complex_fields():
    class Foo(Enum):
        A = 1
        B = 2

    @dataclass
    class Bar:
        a: int

    class Simple(TypedDict):
        items: list[int]

    assert unstructure(Simple, {"items": []}) == {"items": []}
    assert unstructure(Simple, {"items": [1, 2, 3]}) == {"items": [1, 2, 3]}

    class WithMapping(TypedDict):
        data: dict[str, Bar]

    assert unstructure(WithMapping, {"data": {}}) == {"data": {}}
    assert unstructure(WithMapping, {"data": {"x": Bar(10)}}) == {"data": {"x": {"a": 10}}}

    class Nested(TypedDict):
        values: list[list[int]]
        mapping: dict[Foo, Bar]

    assert unstructure(Nested, {"values": [[]], "mapping": {}}) == {"values": [[]], "mapping": {}}
    assert unstructure(Nested, {"values": [[1, 2], [3]], "mapping": {Foo.A: Bar(5)}}) == {
        "values": [[1, 2], [3]],
        "mapping": {"1": {"a": 5}},
    }

    class Outer(TypedDict):
        inner: Simple

    assert unstructure(Outer, {"inner": {"items": [1]}}) == {"inner": {"items": [1]}}

    @dataclass
    class HasTD:
        payload: Simple

    assert unstructure(HasTD, HasTD({"items": [1, 2]})) == {"payload": {"items": [1, 2]}}

    assert unstructure(list[Simple], [{"items": [1]}, {"items": [2, 3]}]) == [{"items": [1]}, {"items": [2, 3]}]
    assert unstructure(dict[str, Simple], {"a": {"items": [1]}}) == {"a": {"items": [1]}}

    T = TypeVar("T")

    class GenTD(TypedDict, Generic[T]):
        x: T

    assert unstructure(list[GenTD[int]], [{"x": 1}, {"x": 2}]) == [{"x": 1}, {"x": 2}]

    class Custom:
        pass

    custom = Custom()
    with pytest.raises(NoUnstructureHook) as e:
        unstructure(Simple, {"items": [1, custom]})  # type: ignore
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$.items[1]"
    assert e.value.ctx.unstructured_path == "$['items'][1]"
    assert e.value.data is custom

    assert unstructure(Outer, {}) == {}
    assert unstructure(list[Simple], [{"items": [1]}, {}]) == [{"items": [1]}, {}]
