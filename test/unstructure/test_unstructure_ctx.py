from dataclasses import dataclass, fields
from typing import Any, Generic, NewType, TypedDict, TypeVar

from ctxure import Ctx, ctxure_config, unstructure, unstructure_default
from ctxure.context import CtxImpl

from ..util import loc


def test_unstructure_ctx_root(testregister):
    ctxs = []

    @testregister
    def unstructure_hook(ctx: Ctx[Any], data: Any) -> Any:
        ctxs.append(ctx)
        return unstructure_default(ctx, data)

    with ctxure_config(dispatcher=testregister):
        unstructure(int, 1, extra=ctxs)
        assert ctxs == [CtxImpl[int, int, None, loc("$")](None, int, "$", "$", None)]
        ctxs.clear()


def test_unstructure_ctx_list_1(testregister):
    ctxs = []

    @testregister
    def unstructure_hook(ctx: Ctx[Any], data: Any) -> Any:
        ctxs.append(ctx)
        return unstructure_default(ctx, data)

    with ctxure_config(dispatcher=testregister):
        unstructure(list[int], [1, 2], extra=ctxs)
        assert ctxs == [
            c0 := CtxImpl[list[int], list[int], None, loc("$")](None, list[int], "$", "$", None),
            CtxImpl[int, list[int], list[int], loc("$[0]")](c0, int, "$[0]", "$[0]", 0),
            CtxImpl[int, list[int], list[int], loc("$[1]")](c0, int, "$[1]", "$[1]", 1),
        ]
        ctxs.clear()


def test_unstructure_ctx_tuple_1(testregister):
    ctxs = []

    @testregister
    def unstructure_hook(ctx: Ctx[Any], data: Any) -> Any:
        ctxs.append(ctx)
        return unstructure_default(ctx, data)

    with ctxure_config(dispatcher=testregister):
        unstructure(tuple[int, float], (1, 1.1), extra=ctxs)
        assert ctxs == [
            c0 := CtxImpl[tuple[int, float], tuple[int, float], None, loc("$")](
                None, tuple[int, float], "$", "$", None
            ),
            CtxImpl[int, tuple[int, float], tuple[int, float], loc("$[0]")](c0, int, "$[0]", "$[0]", 0),
            CtxImpl[float, tuple[int, float], tuple[int, float], loc("$[1]")](c0, float, "$[1]", "$[1]", 1),
        ]
        ctxs.clear()


def test_unstructure_ctx_set_1(testregister):
    ctxs = []

    @testregister
    def unstructure_hook(ctx: Ctx[Any], data: Any) -> Any:
        ctxs.append(ctx)
        return unstructure_default(ctx, data)

    with ctxure_config(dispatcher=testregister):
        data = {"a", "b"}
        unstructure(set[str], data, extra=ctxs)
        assert ctxs[0] == (c0 := CtxImpl[set[str], set[str], None, loc("$")](None, set[str], "$", "$", None))
        assert CtxImpl[str, set[str], set[str], loc("$[?]")](c0, str, "$[?]", "$[0]", None) in ctxs
        assert CtxImpl[str, set[str], set[str], loc("$[?]")](c0, str, "$[?]", "$[1]", None) in ctxs
        ctxs.clear()


def test_unstructure_ctx_frozenset_1(testregister):
    ctxs = []

    @testregister
    def unstructure_hook(ctx: Ctx[Any], data: Any) -> Any:
        ctxs.append(ctx)
        return unstructure_default(ctx, data)

    with ctxure_config(dispatcher=testregister):
        data = frozenset({"a", "b"})
        unstructure(frozenset[str], data, extra=ctxs)
        assert ctxs[0] == (
            c0 := CtxImpl[frozenset[str], frozenset[str], None, loc("$")](None, frozenset[str], "$", "$", None)
        )
        assert CtxImpl[str, frozenset[str], frozenset[str], loc("$[?]")](c0, str, "$[?]", "$[0]", None) in ctxs
        assert CtxImpl[str, frozenset[str], frozenset[str], loc("$[?]")](c0, str, "$[?]", "$[1]", None) in ctxs
        ctxs.clear()


def test_unstructure_ctx_dict_1(testregister):
    ctxs = []

    @testregister
    def unstructure_hook(ctx: Ctx[Any], data: Any) -> Any:
        ctxs.append(ctx)
        return unstructure_default(ctx, data)

    with ctxure_config(dispatcher=testregister):
        unstructure(dict[int, str], {10: "a", 20: "b"}, extra=ctxs)
        assert ctxs == [
            c0 := CtxImpl[dict[int, str], dict[int, str], None, loc("$")](None, dict[int, str], "$", "$", None),
            CtxImpl[int, dict[int, str], dict[int, str], loc("$[~10]")](c0, int, "$[~10]", "$[~?]", 10),
            CtxImpl[str, dict[int, str], dict[int, str], loc("$[10]")](c0, str, "$[10]", "$['10']", 10),
            CtxImpl[int, dict[int, str], dict[int, str], loc("$[~20]")](c0, int, "$[~20]", "$[~?]", 20),
            CtxImpl[str, dict[int, str], dict[int, str], loc("$[20]")](c0, str, "$[20]", "$['20']", 20),
        ]
        ctxs.clear()

        unstructure(dict[Any, Any], {"x": "a", "y": "b"}, extra=ctxs)
        assert ctxs == [
            c0 := CtxImpl[dict[Any, Any], dict[Any, Any], None, loc("$")](None, dict[Any, Any], "$", "$", None),
            CtxImpl[Any, dict[Any, Any], dict[Any, Any], loc("$[~'x']")](c0, Any, "$[~'x']", "$[~?]", "x"),
            CtxImpl[Any, dict[Any, Any], dict[Any, Any], loc("$['x']")](c0, Any, "$['x']", "$['x']", "x"),
            CtxImpl[Any, dict[Any, Any], dict[Any, Any], loc("$[~'y']")](c0, Any, "$[~'y']", "$[~?]", "y"),
            CtxImpl[Any, dict[Any, Any], dict[Any, Any], loc("$['y']")](c0, Any, "$['y']", "$['y']", "y"),
        ]
        ctxs.clear()


def test_unstructure_ctx_dataclass_1(testregister):
    ctxs = []

    @testregister
    def unstructure_hook(ctx: Ctx[Any], data: Any) -> Any:
        ctxs.append(ctx)
        return unstructure_default(ctx, data)

    @dataclass
    class Foo:
        a: int
        b: str

    foo_fields = {f.name: f for f in fields(Foo)}

    with ctxure_config(dispatcher=testregister):
        unstructure(Foo, Foo(1, "x"), extra=ctxs)
        assert ctxs == [
            c0 := CtxImpl[Foo, Foo, None, loc("$")](None, Foo, "$", "$", None),
            CtxImpl[int, Foo, Foo, loc("$.a")](c0, int, "$.a", "$['a']", foo_fields["a"]),
            CtxImpl[str, Foo, Foo, loc("$.b")](c0, str, "$.b", "$['b']", foo_fields["b"]),
        ]
        ctxs.clear()


def test_unstructure_ctx_dataclass_generic_1(testregister):
    ctxs = []

    @testregister
    def unstructure_hook(ctx: Ctx[Any], data: Any) -> Any:
        ctxs.append(ctx)
        return unstructure_default(ctx, data)

    T = TypeVar("T")

    @dataclass
    class Foo(Generic[T]):
        a: T

    foo_fields = {f.name: f for f in fields(Foo)}

    with ctxure_config(dispatcher=testregister):
        unstructure(Foo[int], Foo[int](1), extra=ctxs)
        assert ctxs == [
            c0 := CtxImpl[Foo[int], Foo[int], None, loc("$")](None, Foo[int], "$", "$", None),
            CtxImpl[int, Foo[int], Foo[int], loc("$.a")](c0, int, "$.a", "$['a']", foo_fields["a"]),
        ]
        ctxs.clear()

    with ctxure_config(dispatcher=testregister):
        unstructure(Foo[str], Foo[str]("x"), extra=ctxs)
        assert ctxs == [
            c0 := CtxImpl[Foo[str], Foo[str], None, loc("$")](None, Foo[str], "$", "$", None),
            CtxImpl[str, Foo[str], Foo[str], loc("$.a")](c0, str, "$.a", "$['a']", foo_fields["a"]),
        ]
        ctxs.clear()

    with ctxure_config(dispatcher=testregister):
        unstructure(Foo, Foo(1), extra=ctxs)
        assert ctxs == [
            c0 := CtxImpl[Foo, Foo, None, loc("$")](None, Foo, "$", "$", None),
            CtxImpl[Any, Foo, Foo, loc("$.a")](c0, Any, "$.a", "$['a']", foo_fields["a"]),
        ]
        ctxs.clear()

    with ctxure_config(dispatcher=testregister):
        unstructure(Foo[Any], Foo(1), extra=ctxs)
        assert ctxs == [
            c0 := CtxImpl[Foo[Any], Foo[Any], None, loc("$")](None, Foo[Any], "$", "$", None),
            CtxImpl[Any, Foo[Any], Foo[Any], loc("$.a")](c0, Any, "$.a", "$['a']", foo_fields["a"]),
        ]
        ctxs.clear()


def test_unstructure_ctx_typeddict_1(testregister):
    ctxs = []

    @testregister
    def unstructure_hook(ctx: Ctx[Any], data: Any) -> Any:
        ctxs.append(ctx)
        return unstructure_default(ctx, data)

    class Foo(TypedDict):
        a: int
        b: str

    with ctxure_config(dispatcher=testregister):
        unstructure(Foo, {"a": 1, "b": "x"}, extra=ctxs)
        assert ctxs == [
            c0 := CtxImpl[Foo, Foo, None, loc("$")](None, Foo, "$", "$", None),
            CtxImpl[int, Foo, Foo, loc("$.a")](c0, int, "$.a", "$['a']", "a"),
            CtxImpl[str, Foo, Foo, loc("$.b")](c0, str, "$.b", "$['b']", "b"),
        ]
        ctxs.clear()


def test_unstructure_ctx_typeddict_generic_1(testregister):
    ctxs = []

    @testregister
    def unstructure_hook(ctx: Ctx[Any], data: Any) -> Any:
        ctxs.append(ctx)
        return unstructure_default(ctx, data)

    T = TypeVar("T")

    class Foo(TypedDict, Generic[T]):
        a: T

    with ctxure_config(dispatcher=testregister):
        unstructure(Foo[int], {"a": 1}, extra=ctxs)
        assert ctxs == [
            c0 := CtxImpl[Foo[int], Foo[int], None, loc("$")](None, Foo[int], "$", "$", None),
            CtxImpl[int, Foo[int], Foo[int], loc("$.a")](c0, int, "$.a", "$['a']", "a"),
        ]
        ctxs.clear()

    with ctxure_config(dispatcher=testregister):
        unstructure(Foo[str], {"a": "x"}, extra=ctxs)
        assert ctxs == [
            c0 := CtxImpl[Foo[str], Foo[str], None, loc("$")](None, Foo[str], "$", "$", None),
            CtxImpl[str, Foo[str], Foo[str], loc("$.a")](c0, str, "$.a", "$['a']", "a"),
        ]
        ctxs.clear()


def test_unstructure_ctx_list_2(testregister):
    ctxs = []

    @testregister
    def unstructure_hook(ctx: Ctx[Any], data: Any) -> Any:
        ctxs.append(ctx)
        return unstructure_default(ctx, data)

    @dataclass
    class Foo:
        a: int
        b: str

    foo_fields = {f.name: f for f in fields(Foo)}

    with ctxure_config(dispatcher=testregister):
        unstructure(list[list[int]], [[1, 2], [3, 4]], extra=ctxs)
        assert ctxs == [
            c0 := CtxImpl[list[list[int]], list[list[int]], None, loc("$")](None, list[list[int]], "$", "$", None),
            c1_1 := CtxImpl[list[int], list[list[int]], list[list[int]], loc("$[0]")](c0, list[int], "$[0]", "$[0]", 0),
            CtxImpl[int, list[list[int]], list[int], loc("$[0][0]")](c1_1, int, "$[0][0]", "$[0][0]", 0),
            CtxImpl[int, list[list[int]], list[int], loc("$[0][1]")](c1_1, int, "$[0][1]", "$[0][1]", 1),
            c1_2 := CtxImpl[list[int], list[list[int]], list[list[int]], loc("$[1]")](c0, list[int], "$[1]", "$[1]", 1),
            CtxImpl[int, list[list[int]], list[int], loc("$[1][0]")](c1_2, int, "$[1][0]", "$[1][0]", 0),
            CtxImpl[int, list[list[int]], list[int], loc("$[1][1]")](c1_2, int, "$[1][1]", "$[1][1]", 1),
        ]
        ctxs.clear()

        unstructure(list[tuple[int, float]], [(1, 2.2), (3, 4.4)], extra=ctxs)
        assert ctxs == [
            c0 := CtxImpl[list[tuple[int, float]], list[tuple[int, float]], None, loc("$")](
                None, list[tuple[int, float]], "$", "$", None
            ),
            c1_1 := CtxImpl[tuple[int, float], list[tuple[int, float]], list[tuple[int, float]], loc("$[0]")](
                c0, tuple[int, float], "$[0]", "$[0]", 0
            ),
            CtxImpl[int, list[tuple[int, float]], tuple[int, float], loc("$[0][0]")](
                c1_1, int, "$[0][0]", "$[0][0]", 0
            ),
            CtxImpl[float, list[tuple[int, float]], tuple[int, float], loc("$[0][1]")](
                c1_1, float, "$[0][1]", "$[0][1]", 1
            ),
            c1_2 := CtxImpl[tuple[int, float], list[tuple[int, float]], list[tuple[int, float]], loc("$[1]")](
                c0, tuple[int, float], "$[1]", "$[1]", 1
            ),
            CtxImpl[int, list[tuple[int, float]], tuple[int, float], loc("$[1][0]")](
                c1_2, int, "$[1][0]", "$[1][0]", 0
            ),
            CtxImpl[float, list[tuple[int, float]], tuple[int, float], loc("$[1][1]")](
                c1_2, float, "$[1][1]", "$[1][1]", 1
            ),
        ]
        ctxs.clear()

        unstructure(list[set[int]], [{1, 2}, {3, 4}], extra=ctxs)
        assert ctxs == [
            c0 := CtxImpl[list[set[int]], list[set[int]], None, loc("$")](None, list[set[int]], "$", "$", None),
            c1_1 := CtxImpl[set[int], list[set[int]], list[set[int]], loc("$[0]")](c0, set[int], "$[0]", "$[0]", 0),
            CtxImpl[int, list[set[int]], set[int], loc("$[0][?]")](c1_1, int, "$[0][?]", "$[0][0]", None),
            CtxImpl[int, list[set[int]], set[int], loc("$[0][?]")](c1_1, int, "$[0][?]", "$[0][1]", None),
            c1_2 := CtxImpl[set[int], list[set[int]], list[set[int]], loc("$[1]")](c0, set[int], "$[1]", "$[1]", 1),
            CtxImpl[int, list[set[int]], set[int], loc("$[1][?]")](c1_2, int, "$[1][?]", "$[1][0]", None),
            CtxImpl[int, list[set[int]], set[int], loc("$[1][?]")](c1_2, int, "$[1][?]", "$[1][1]", None),
        ]
        ctxs.clear()

        unstructure(list[frozenset[int]], [frozenset({1, 2}), frozenset({3, 4})], extra=ctxs)
        assert ctxs == [
            c0 := CtxImpl[list[frozenset[int]], list[frozenset[int]], None, loc("$")](
                None, list[frozenset[int]], "$", "$", None
            ),
            c1_1 := CtxImpl[frozenset[int], list[frozenset[int]], list[frozenset[int]], loc("$[0]")](
                c0, frozenset[int], "$[0]", "$[0]", 0
            ),
            CtxImpl[int, list[frozenset[int]], frozenset[int], loc("$[0][?]")](c1_1, int, "$[0][?]", "$[0][0]", None),
            CtxImpl[int, list[frozenset[int]], frozenset[int], loc("$[0][?]")](c1_1, int, "$[0][?]", "$[0][1]", None),
            c1_2 := CtxImpl[frozenset[int], list[frozenset[int]], list[frozenset[int]], loc("$[1]")](
                c0, frozenset[int], "$[1]", "$[1]", 1
            ),
            CtxImpl[int, list[frozenset[int]], frozenset[int], loc("$[1][?]")](c1_2, int, "$[1][?]", "$[1][0]", None),
            CtxImpl[int, list[frozenset[int]], frozenset[int], loc("$[1][?]")](c1_2, int, "$[1][?]", "$[1][1]", None),
        ]
        ctxs.clear()

        unstructure(list[dict[str, int]], [{"a": 1}, {"b": 2}], extra=ctxs)
        assert ctxs == [
            c0 := CtxImpl[list[dict[str, int]], list[dict[str, int]], None, loc("$")](
                None, list[dict[str, int]], "$", "$", None
            ),
            c1_1 := CtxImpl[dict[str, int], list[dict[str, int]], list[dict[str, int]], loc("$[0]")](
                c0, dict[str, int], "$[0]", "$[0]", 0
            ),
            CtxImpl[str, list[dict[str, int]], dict[str, int], loc("$[0][~'a']")](
                c1_1, str, "$[0][~'a']", "$[0][~?]", "a"
            ),
            CtxImpl[int, list[dict[str, int]], dict[str, int], loc("$[0]['a']")](
                c1_1, int, "$[0]['a']", "$[0]['a']", "a"
            ),
            c1_2 := CtxImpl[dict[str, int], list[dict[str, int]], list[dict[str, int]], loc("$[1]")](
                c0, dict[str, int], "$[1]", "$[1]", 1
            ),
            CtxImpl[str, list[dict[str, int]], dict[str, int], loc("$[1][~'b']")](
                c1_2, str, "$[1][~'b']", "$[1][~?]", "b"
            ),
            CtxImpl[int, list[dict[str, int]], dict[str, int], loc("$[1]['b']")](
                c1_2, int, "$[1]['b']", "$[1]['b']", "b"
            ),
        ]
        ctxs.clear()

        unstructure(list[Foo], [Foo(1, "x"), Foo(2, "y")], extra=ctxs)
        assert ctxs == [
            c0 := CtxImpl[list[Foo], list[Foo], None, loc("$")](None, list[Foo], "$", "$", None),
            c1_1 := CtxImpl[Foo, list[Foo], list[Foo], loc("$[0]")](c0, Foo, "$[0]", "$[0]", 0),
            CtxImpl[int, list[Foo], Foo, loc("$[0].a")](c1_1, int, "$[0].a", "$[0]['a']", foo_fields["a"]),
            CtxImpl[str, list[Foo], Foo, loc("$[0].b")](c1_1, str, "$[0].b", "$[0]['b']", foo_fields["b"]),
            c1_2 := CtxImpl[Foo, list[Foo], list[Foo], loc("$[1]")](c0, Foo, "$[1]", "$[1]", 1),
            CtxImpl[int, list[Foo], Foo, loc("$[1].a")](c1_2, int, "$[1].a", "$[1]['a']", foo_fields["a"]),
            CtxImpl[str, list[Foo], Foo, loc("$[1].b")](c1_2, str, "$[1].b", "$[1]['b']", foo_fields["b"]),
        ]
        ctxs.clear()


def test_unstructure_ctx_tuple_2(testregister):
    ctxs = []

    @testregister
    def unstructure_hook(ctx: Ctx[Any], data: Any) -> Any:
        ctxs.append(ctx)
        return unstructure_default(ctx, data)

    @dataclass
    class Foo:
        a: int
        b: str

    foo_fields = {f.name: f for f in fields(Foo)}

    with ctxure_config(dispatcher=testregister):
        unstructure(tuple[list[int], list[int]], ([1, 2], [3, 4]), extra=ctxs)
        assert ctxs == [
            c0 := CtxImpl[tuple[list[int], list[int]], tuple[list[int], list[int]], None, loc("$")](
                None, tuple[list[int], list[int]], "$", "$", None
            ),
            c1_1 := CtxImpl[list[int], tuple[list[int], list[int]], tuple[list[int], list[int]], loc("$[0]")](
                c0, list[int], "$[0]", "$[0]", 0
            ),
            CtxImpl[int, tuple[list[int], list[int]], list[int], loc("$[0][0]")](c1_1, int, "$[0][0]", "$[0][0]", 0),
            CtxImpl[int, tuple[list[int], list[int]], list[int], loc("$[0][1]")](c1_1, int, "$[0][1]", "$[0][1]", 1),
            c1_2 := CtxImpl[list[int], tuple[list[int], list[int]], tuple[list[int], list[int]], loc("$[1]")](
                c0, list[int], "$[1]", "$[1]", 1
            ),
            CtxImpl[int, tuple[list[int], list[int]], list[int], loc("$[1][0]")](c1_2, int, "$[1][0]", "$[1][0]", 0),
            CtxImpl[int, tuple[list[int], list[int]], list[int], loc("$[1][1]")](c1_2, int, "$[1][1]", "$[1][1]", 1),
        ]
        ctxs.clear()

        unstructure(tuple[tuple[int, float], tuple[int, str]], ((1, 1.1), (2, "a")), extra=ctxs)
        assert ctxs == [
            c0 := CtxImpl[
                tuple[tuple[int, float], tuple[int, str]], tuple[tuple[int, float], tuple[int, str]], None, loc("$")
            ](None, tuple[tuple[int, float], tuple[int, str]], "$", "$", None),
            c1_1 := CtxImpl[
                tuple[int, float],
                tuple[tuple[int, float], tuple[int, str]],
                tuple[tuple[int, float], tuple[int, str]],
                loc("$[0]"),
            ](c0, tuple[int, float], "$[0]", "$[0]", 0),
            CtxImpl[int, tuple[tuple[int, float], tuple[int, str]], tuple[int, float], loc("$[0][0]")](
                c1_1, int, "$[0][0]", "$[0][0]", 0
            ),
            CtxImpl[float, tuple[tuple[int, float], tuple[int, str]], tuple[int, float], loc("$[0][1]")](
                c1_1, float, "$[0][1]", "$[0][1]", 1
            ),
            c1_2 := CtxImpl[
                tuple[int, str],
                tuple[tuple[int, float], tuple[int, str]],
                tuple[tuple[int, float], tuple[int, str]],
                loc("$[1]"),
            ](c0, tuple[int, str], "$[1]", "$[1]", 1),
            CtxImpl[int, tuple[tuple[int, float], tuple[int, str]], tuple[int, str], loc("$[1][0]")](
                c1_2, int, "$[1][0]", "$[1][0]", 0
            ),
            CtxImpl[str, tuple[tuple[int, float], tuple[int, str]], tuple[int, str], loc("$[1][1]")](
                c1_2, str, "$[1][1]", "$[1][1]", 1
            ),
        ]
        ctxs.clear()

        unstructure(tuple[set[int], set[str]], ({1, 2}, {"a", "b"}), extra=ctxs)
        assert ctxs == [
            c0 := CtxImpl[tuple[set[int], set[str]], tuple[set[int], set[str]], None, loc("$")](
                None, tuple[set[int], set[str]], "$", "$", None
            ),
            c1_1 := CtxImpl[set[int], tuple[set[int], set[str]], tuple[set[int], set[str]], loc("$[0]")](
                c0, set[int], "$[0]", "$[0]", 0
            ),
            CtxImpl[int, tuple[set[int], set[str]], set[int], loc("$[0][?]")](c1_1, int, "$[0][?]", "$[0][0]", None),
            CtxImpl[int, tuple[set[int], set[str]], set[int], loc("$[0][?]")](c1_1, int, "$[0][?]", "$[0][1]", None),
            c1_2 := CtxImpl[set[str], tuple[set[int], set[str]], tuple[set[int], set[str]], loc("$[1]")](
                c0, set[str], "$[1]", "$[1]", 1
            ),
            CtxImpl[str, tuple[set[int], set[str]], set[str], loc("$[1][?]")](c1_2, str, "$[1][?]", "$[1][0]", None),
            CtxImpl[str, tuple[set[int], set[str]], set[str], loc("$[1][?]")](c1_2, str, "$[1][?]", "$[1][1]", None),
        ]
        ctxs.clear()

        unstructure(tuple[frozenset[int], frozenset[str]], (frozenset({1, 2}), frozenset({"a", "b"})), extra=ctxs)
        assert ctxs == [
            c0 := CtxImpl[tuple[frozenset[int], frozenset[str]], tuple[frozenset[int], frozenset[str]], None, loc("$")](
                None, tuple[frozenset[int], frozenset[str]], "$", "$", None
            ),
            c1_1 := CtxImpl[
                frozenset[int],
                tuple[frozenset[int], frozenset[str]],
                tuple[frozenset[int], frozenset[str]],
                loc("$[0]"),
            ](c0, frozenset[int], "$[0]", "$[0]", 0),
            CtxImpl[int, tuple[frozenset[int], frozenset[str]], frozenset[int], loc("$[0][?]")](
                c1_1, int, "$[0][?]", "$[0][0]", None
            ),
            CtxImpl[int, tuple[frozenset[int], frozenset[str]], frozenset[int], loc("$[0][?]")](
                c1_1, int, "$[0][?]", "$[0][1]", None
            ),
            c1_2 := CtxImpl[
                frozenset[str],
                tuple[frozenset[int], frozenset[str]],
                tuple[frozenset[int], frozenset[str]],
                loc("$[1]"),
            ](c0, frozenset[str], "$[1]", "$[1]", 1),
            CtxImpl[str, tuple[frozenset[int], frozenset[str]], frozenset[str], loc("$[1][?]")](
                c1_2, str, "$[1][?]", "$[1][0]", None
            ),
            CtxImpl[str, tuple[frozenset[int], frozenset[str]], frozenset[str], loc("$[1][?]")](
                c1_2, str, "$[1][?]", "$[1][1]", None
            ),
        ]
        ctxs.clear()

        unstructure(tuple[dict[str, int], dict[str, float]], ({"a": 1}, {"b": 2.2}), extra=ctxs)
        assert ctxs == [
            c0 := CtxImpl[
                tuple[dict[str, int], dict[str, float]], tuple[dict[str, int], dict[str, float]], None, loc("$")
            ](None, tuple[dict[str, int], dict[str, float]], "$", "$", None),
            c1_1 := CtxImpl[
                dict[str, int],
                tuple[dict[str, int], dict[str, float]],
                tuple[dict[str, int], dict[str, float]],
                loc("$[0]"),
            ](c0, dict[str, int], "$[0]", "$[0]", 0),
            CtxImpl[str, tuple[dict[str, int], dict[str, float]], dict[str, int], loc("$[0][~'a']")](
                c1_1, str, "$[0][~'a']", "$[0][~?]", "a"
            ),
            CtxImpl[int, tuple[dict[str, int], dict[str, float]], dict[str, int], loc("$[0]['a']")](
                c1_1, int, "$[0]['a']", "$[0]['a']", "a"
            ),
            c1_2 := CtxImpl[
                dict[str, float],
                tuple[dict[str, int], dict[str, float]],
                tuple[dict[str, int], dict[str, float]],
                loc("$[1]"),
            ](c0, dict[str, float], "$[1]", "$[1]", 1),
            CtxImpl[str, tuple[dict[str, int], dict[str, float]], dict[str, float], loc("$[1][~'b']")](
                c1_2, str, "$[1][~'b']", "$[1][~?]", "b"
            ),
            CtxImpl[float, tuple[dict[str, int], dict[str, float]], dict[str, float], loc("$[1]['b']")](
                c1_2, float, "$[1]['b']", "$[1]['b']", "b"
            ),
        ]
        ctxs.clear()

        unstructure(tuple[Foo, Foo], (Foo(1, "x"), Foo(2, "y")), extra=ctxs)
        assert ctxs == [
            c0 := CtxImpl[tuple[Foo, Foo], tuple[Foo, Foo], None, loc("$")](None, tuple[Foo, Foo], "$", "$", None),
            c1_1 := CtxImpl[Foo, tuple[Foo, Foo], tuple[Foo, Foo], loc("$[0]")](c0, Foo, "$[0]", "$[0]", 0),
            CtxImpl[int, tuple[Foo, Foo], Foo, loc("$[0].a")](c1_1, int, "$[0].a", "$[0]['a']", foo_fields["a"]),
            CtxImpl[str, tuple[Foo, Foo], Foo, loc("$[0].b")](c1_1, str, "$[0].b", "$[0]['b']", foo_fields["b"]),
            c1_2 := CtxImpl[Foo, tuple[Foo, Foo], tuple[Foo, Foo], loc("$[1]")](c0, Foo, "$[1]", "$[1]", 1),
            CtxImpl[int, tuple[Foo, Foo], Foo, loc("$[1].a")](c1_2, int, "$[1].a", "$[1]['a']", foo_fields["a"]),
            CtxImpl[str, tuple[Foo, Foo], Foo, loc("$[1].b")](c1_2, str, "$[1].b", "$[1]['b']", foo_fields["b"]),
        ]
        ctxs.clear()


def test_unstructure_ctx_set_2(testregister):
    ctxs = []

    @testregister
    def unstructure_hook(ctx: Ctx[Any], data: Any) -> Any:
        ctxs.append(ctx)
        return unstructure_default(ctx, data)

    with ctxure_config(dispatcher=testregister):
        data = {(1, 2.2), (3, 4.4)}
        unstructure(set[tuple[int, float]], data, extra=ctxs)
        assert ctxs == [
            c0 := CtxImpl[set[tuple[int, float]], set[tuple[int, float]], None, loc("$")](
                None, set[tuple[int, float]], "$", "$", None
            ),
            c1_1 := CtxImpl[tuple[int, float], set[tuple[int, float]], set[tuple[int, float]], loc("$[?]")](
                c0, tuple[int, float], "$[?]", "$[0]", None
            ),
            CtxImpl[int, set[tuple[int, float]], tuple[int, float], loc("$[?][0]")](c1_1, int, "$[?][0]", "$[0][0]", 0),
            CtxImpl[float, set[tuple[int, float]], tuple[int, float], loc("$[?][1]")](
                c1_1, float, "$[?][1]", "$[0][1]", 1
            ),
            c1_2 := CtxImpl[tuple[int, float], set[tuple[int, float]], set[tuple[int, float]], loc("$[?]")](
                c0, tuple[int, float], "$[?]", "$[1]", None
            ),
            CtxImpl[int, set[tuple[int, float]], tuple[int, float], loc("$[?][0]")](c1_2, int, "$[?][0]", "$[1][0]", 0),
            CtxImpl[float, set[tuple[int, float]], tuple[int, float], loc("$[?][1]")](
                c1_2, float, "$[?][1]", "$[1][1]", 1
            ),
        ]
        ctxs.clear()

        data = {frozenset({1, 2}), frozenset({3, 4})}
        unstructure(set[frozenset[int]], data, extra=ctxs)
        assert ctxs == [
            c0 := CtxImpl[set[frozenset[int]], set[frozenset[int]], None, loc("$")](
                None, set[frozenset[int]], "$", "$", None
            ),
            c1_1 := CtxImpl[frozenset[int], set[frozenset[int]], set[frozenset[int]], loc("$[?]")](
                c0, frozenset[int], "$[?]", "$[0]", None
            ),
            CtxImpl[int, set[frozenset[int]], frozenset[int], loc("$[?][?]")](c1_1, int, "$[?][?]", "$[0][0]", None),
            CtxImpl[int, set[frozenset[int]], frozenset[int], loc("$[?][?]")](c1_1, int, "$[?][?]", "$[0][1]", None),
            c1_2 := CtxImpl[frozenset[int], set[frozenset[int]], set[frozenset[int]], loc("$[?]")](
                c0, frozenset[int], "$[?]", "$[1]", None
            ),
            CtxImpl[int, set[frozenset[int]], frozenset[int], loc("$[?][?]")](c1_2, int, "$[?][?]", "$[1][0]", None),
            CtxImpl[int, set[frozenset[int]], frozenset[int], loc("$[?][?]")](c1_2, int, "$[?][?]", "$[1][1]", None),
        ]
        ctxs.clear()


def test_unstructure_ctx_frozenset_2(testregister):
    ctxs = []

    @testregister
    def unstructure_hook(ctx: Ctx[Any], data: Any) -> Any:
        ctxs.append(ctx)
        return unstructure_default(ctx, data)

    with ctxure_config(dispatcher=testregister):
        data = frozenset({(1, 2.2), (3, 4.4)})
        unstructure(frozenset[tuple[int, float]], data, extra=ctxs)
        assert ctxs == [
            c0 := CtxImpl[frozenset[tuple[int, float]], frozenset[tuple[int, float]], None, loc("$")](
                None, frozenset[tuple[int, float]], "$", "$", None
            ),
            c1_1 := CtxImpl[tuple[int, float], frozenset[tuple[int, float]], frozenset[tuple[int, float]], loc("$[?]")](
                c0, tuple[int, float], "$[?]", "$[0]", None
            ),
            CtxImpl[int, frozenset[tuple[int, float]], tuple[int, float], loc("$[?][0]")](
                c1_1, int, "$[?][0]", "$[0][0]", 0
            ),
            CtxImpl[float, frozenset[tuple[int, float]], tuple[int, float], loc("$[?][1]")](
                c1_1, float, "$[?][1]", "$[0][1]", 1
            ),
            c1_2 := CtxImpl[tuple[int, float], frozenset[tuple[int, float]], frozenset[tuple[int, float]], loc("$[?]")](
                c0, tuple[int, float], "$[?]", "$[1]", None
            ),
            CtxImpl[int, frozenset[tuple[int, float]], tuple[int, float], loc("$[?][0]")](
                c1_2, int, "$[?][0]", "$[1][0]", 0
            ),
            CtxImpl[float, frozenset[tuple[int, float]], tuple[int, float], loc("$[?][1]")](
                c1_2, float, "$[?][1]", "$[1][1]", 1
            ),
        ]
        ctxs.clear()

        data = frozenset({frozenset({1, 2}), frozenset({3, 4})})
        unstructure(frozenset[frozenset[int]], data, extra=ctxs)
        assert ctxs == [
            c0 := CtxImpl[frozenset[frozenset[int]], frozenset[frozenset[int]], None, loc("$")](
                None, frozenset[frozenset[int]], "$", "$", None
            ),
            c1_1 := CtxImpl[frozenset[int], frozenset[frozenset[int]], frozenset[frozenset[int]], loc("$[?]")](
                c0, frozenset[int], "$[?]", "$[0]", None
            ),
            CtxImpl[int, frozenset[frozenset[int]], frozenset[int], loc("$[?][?]")](
                c1_1, int, "$[?][?]", "$[0][0]", None
            ),
            CtxImpl[int, frozenset[frozenset[int]], frozenset[int], loc("$[?][?]")](
                c1_1, int, "$[?][?]", "$[0][1]", None
            ),
            c1_2 := CtxImpl[frozenset[int], frozenset[frozenset[int]], frozenset[frozenset[int]], loc("$[?]")](
                c0, frozenset[int], "$[?]", "$[1]", None
            ),
            CtxImpl[int, frozenset[frozenset[int]], frozenset[int], loc("$[?][?]")](
                c1_2, int, "$[?][?]", "$[1][0]", None
            ),
            CtxImpl[int, frozenset[frozenset[int]], frozenset[int], loc("$[?][?]")](
                c1_2, int, "$[?][?]", "$[1][1]", None
            ),
        ]
        ctxs.clear()


def test_unstructure_ctx_dict_2(testregister):
    ctxs = []

    @testregister
    def unstructure_hook(ctx: Ctx[Any], data: Any) -> Any:
        ctxs.append(ctx)
        return unstructure_default(ctx, data)

    @dataclass
    class Foo:
        a: int
        b: str

    foo_fields = {f.name: f for f in fields(Foo)}

    with ctxure_config(dispatcher=testregister):
        unstructure(dict[str, list[int]], {"a": [1, 2], "b": [3, 4]}, extra=ctxs)
        assert ctxs == [
            c0 := CtxImpl[dict[str, list[int]], dict[str, list[int]], None, loc("$")](
                None, dict[str, list[int]], "$", "$", None
            ),
            CtxImpl[str, dict[str, list[int]], dict[str, list[int]], loc("$[~'a']")](c0, str, "$[~'a']", "$[~?]", "a"),
            c1_v1 := CtxImpl[list[int], dict[str, list[int]], dict[str, list[int]], loc("$['a']")](
                c0, list[int], "$['a']", "$['a']", "a"
            ),
            CtxImpl[int, dict[str, list[int]], list[int], loc("$['a'][0]")](c1_v1, int, "$['a'][0]", "$['a'][0]", 0),
            CtxImpl[int, dict[str, list[int]], list[int], loc("$['a'][1]")](c1_v1, int, "$['a'][1]", "$['a'][1]", 1),
            CtxImpl[str, dict[str, list[int]], dict[str, list[int]], loc("$[~'b']")](c0, str, "$[~'b']", "$[~?]", "b"),
            c1_v2 := CtxImpl[list[int], dict[str, list[int]], dict[str, list[int]], loc("$['b']")](
                c0, list[int], "$['b']", "$['b']", "b"
            ),
            CtxImpl[int, dict[str, list[int]], list[int], loc("$['b'][0]")](c1_v2, int, "$['b'][0]", "$['b'][0]", 0),
            CtxImpl[int, dict[str, list[int]], list[int], loc("$['b'][1]")](c1_v2, int, "$['b'][1]", "$['b'][1]", 1),
        ]
        ctxs.clear()

        unstructure(dict[str, tuple[int, float]], {"a": (1, 2.2), "b": (3, 4.4)}, extra=ctxs)
        assert ctxs == [
            c0 := CtxImpl[dict[str, tuple[int, float]], dict[str, tuple[int, float]], None, loc("$")](
                None, dict[str, tuple[int, float]], "$", "$", None
            ),
            CtxImpl[str, dict[str, tuple[int, float]], dict[str, tuple[int, float]], loc("$[~'a']")](
                c0, str, "$[~'a']", "$[~?]", "a"
            ),
            c1_v1 := CtxImpl[
                tuple[int, float], dict[str, tuple[int, float]], dict[str, tuple[int, float]], loc("$['a']")
            ](c0, tuple[int, float], "$['a']", "$['a']", "a"),
            CtxImpl[int, dict[str, tuple[int, float]], tuple[int, float], loc("$['a'][0]")](
                c1_v1, int, "$['a'][0]", "$['a'][0]", 0
            ),
            CtxImpl[float, dict[str, tuple[int, float]], tuple[int, float], loc("$['a'][1]")](
                c1_v1, float, "$['a'][1]", "$['a'][1]", 1
            ),
            CtxImpl[str, dict[str, tuple[int, float]], dict[str, tuple[int, float]], loc("$[~'b']")](
                c0, str, "$[~'b']", "$[~?]", "b"
            ),
            c1_v2 := CtxImpl[
                tuple[int, float], dict[str, tuple[int, float]], dict[str, tuple[int, float]], loc("$['b']")
            ](c0, tuple[int, float], "$['b']", "$['b']", "b"),
            CtxImpl[int, dict[str, tuple[int, float]], tuple[int, float], loc("$['b'][0]")](
                c1_v2, int, "$['b'][0]", "$['b'][0]", 0
            ),
            CtxImpl[float, dict[str, tuple[int, float]], tuple[int, float], loc("$['b'][1]")](
                c1_v2, float, "$['b'][1]", "$['b'][1]", 1
            ),
        ]
        ctxs.clear()

        unstructure(dict[str, set[int]], {"a": {1, 2}, "b": {3, 4}}, extra=ctxs)
        assert ctxs == [
            c0 := CtxImpl[dict[str, set[int]], dict[str, set[int]], None, loc("$")](
                None, dict[str, set[int]], "$", "$", None
            ),
            CtxImpl[str, dict[str, set[int]], dict[str, set[int]], loc("$[~'a']")](c0, str, "$[~'a']", "$[~?]", "a"),
            c1_v1 := CtxImpl[set[int], dict[str, set[int]], dict[str, set[int]], loc("$['a']")](
                c0, set[int], "$['a']", "$['a']", "a"
            ),
            CtxImpl[int, dict[str, set[int]], set[int], loc("$['a'][?]")](c1_v1, int, "$['a'][?]", "$['a'][0]", None),
            CtxImpl[int, dict[str, set[int]], set[int], loc("$['a'][?]")](c1_v1, int, "$['a'][?]", "$['a'][1]", None),
            CtxImpl[str, dict[str, set[int]], dict[str, set[int]], loc("$[~'b']")](c0, str, "$[~'b']", "$[~?]", "b"),
            c1_v2 := CtxImpl[set[int], dict[str, set[int]], dict[str, set[int]], loc("$['b']")](
                c0, set[int], "$['b']", "$['b']", "b"
            ),
            CtxImpl[int, dict[str, set[int]], set[int], loc("$['b'][?]")](c1_v2, int, "$['b'][?]", "$['b'][0]", None),
            CtxImpl[int, dict[str, set[int]], set[int], loc("$['b'][?]")](c1_v2, int, "$['b'][?]", "$['b'][1]", None),
        ]
        ctxs.clear()

        unstructure(dict[str, frozenset[int]], {"a": frozenset({1, 2}), "b": frozenset({3, 4})}, extra=ctxs)
        assert ctxs == [
            c0 := CtxImpl[dict[str, frozenset[int]], dict[str, frozenset[int]], None, loc("$")](
                None, dict[str, frozenset[int]], "$", "$", None
            ),
            CtxImpl[str, dict[str, frozenset[int]], dict[str, frozenset[int]], loc("$[~'a']")](
                c0, str, "$[~'a']", "$[~?]", "a"
            ),
            c1_v1 := CtxImpl[frozenset[int], dict[str, frozenset[int]], dict[str, frozenset[int]], loc("$['a']")](
                c0, frozenset[int], "$['a']", "$['a']", "a"
            ),
            CtxImpl[int, dict[str, frozenset[int]], frozenset[int], loc("$['a'][?]")](
                c1_v1, int, "$['a'][?]", "$['a'][0]", None
            ),
            CtxImpl[int, dict[str, frozenset[int]], frozenset[int], loc("$['a'][?]")](
                c1_v1, int, "$['a'][?]", "$['a'][1]", None
            ),
            CtxImpl[str, dict[str, frozenset[int]], dict[str, frozenset[int]], loc("$[~'b']")](
                c0, str, "$[~'b']", "$[~?]", "b"
            ),
            c1_v2 := CtxImpl[frozenset[int], dict[str, frozenset[int]], dict[str, frozenset[int]], loc("$['b']")](
                c0, frozenset[int], "$['b']", "$['b']", "b"
            ),
            CtxImpl[int, dict[str, frozenset[int]], frozenset[int], loc("$['b'][?]")](
                c1_v2, int, "$['b'][?]", "$['b'][0]", None
            ),
            CtxImpl[int, dict[str, frozenset[int]], frozenset[int], loc("$['b'][?]")](
                c1_v2, int, "$['b'][?]", "$['b'][1]", None
            ),
        ]
        ctxs.clear()

        unstructure(dict[str, dict[str, int]], {"a": {"x": 1}, "b": {"y": 2}}, extra=ctxs)
        assert ctxs == [
            c0 := CtxImpl[dict[str, dict[str, int]], dict[str, dict[str, int]], None, loc("$")](
                None, dict[str, dict[str, int]], "$", "$", None
            ),
            CtxImpl[str, dict[str, dict[str, int]], dict[str, dict[str, int]], loc("$[~'a']")](
                c0, str, "$[~'a']", "$[~?]", "a"
            ),
            c1_v1 := CtxImpl[dict[str, int], dict[str, dict[str, int]], dict[str, dict[str, int]], loc("$['a']")](
                c0, dict[str, int], "$['a']", "$['a']", "a"
            ),
            CtxImpl[str, dict[str, dict[str, int]], dict[str, int], loc("$['a'][~'x']")](
                c1_v1, str, "$['a'][~'x']", "$['a'][~?]", "x"
            ),
            CtxImpl[int, dict[str, dict[str, int]], dict[str, int], loc("$['a']['x']")](
                c1_v1, int, "$['a']['x']", "$['a']['x']", "x"
            ),
            CtxImpl[str, dict[str, dict[str, int]], dict[str, dict[str, int]], loc("$[~'b']")](
                c0, str, "$[~'b']", "$[~?]", "b"
            ),
            c1_v2 := CtxImpl[dict[str, int], dict[str, dict[str, int]], dict[str, dict[str, int]], loc("$['b']")](
                c0, dict[str, int], "$['b']", "$['b']", "b"
            ),
            CtxImpl[str, dict[str, dict[str, int]], dict[str, int], loc("$['b'][~'y']")](
                c1_v2, str, "$['b'][~'y']", "$['b'][~?]", "y"
            ),
            CtxImpl[int, dict[str, dict[str, int]], dict[str, int], loc("$['b']['y']")](
                c1_v2, int, "$['b']['y']", "$['b']['y']", "y"
            ),
        ]
        ctxs.clear()

        unstructure(dict[str, Foo], {"a": Foo(1, "x"), "b": Foo(2, "y")}, extra=ctxs)
        assert ctxs == [
            c0 := CtxImpl[dict[str, Foo], dict[str, Foo], None, loc("$")](None, dict[str, Foo], "$", "$", None),
            CtxImpl[str, dict[str, Foo], dict[str, Foo], loc("$[~'a']")](c0, str, "$[~'a']", "$[~?]", "a"),
            c1_v1 := CtxImpl[Foo, dict[str, Foo], dict[str, Foo], loc("$['a']")](c0, Foo, "$['a']", "$['a']", "a"),
            CtxImpl[int, dict[str, Foo], Foo, loc("$['a'].a")](c1_v1, int, "$['a'].a", "$['a']['a']", foo_fields["a"]),
            CtxImpl[str, dict[str, Foo], Foo, loc("$['a'].b")](c1_v1, str, "$['a'].b", "$['a']['b']", foo_fields["b"]),
            CtxImpl[str, dict[str, Foo], dict[str, Foo], loc("$[~'b']")](c0, str, "$[~'b']", "$[~?]", "b"),
            c1_v2 := CtxImpl[Foo, dict[str, Foo], dict[str, Foo], loc("$['b']")](c0, Foo, "$['b']", "$['b']", "b"),
            CtxImpl[int, dict[str, Foo], Foo, loc("$['b'].a")](c1_v2, int, "$['b'].a", "$['b']['a']", foo_fields["a"]),
            CtxImpl[str, dict[str, Foo], Foo, loc("$['b'].b")](c1_v2, str, "$['b'].b", "$['b']['b']", foo_fields["b"]),
        ]
        ctxs.clear()


def test_unstructure_ctx_dataclass_2(testregister):
    ctxs = []

    @testregister
    def unstructure_hook(ctx: Ctx[Any], data: Any) -> Any:
        ctxs.append(ctx)
        return unstructure_default(ctx, data)

    @dataclass
    class Bar:
        x: int
        y: str

    @dataclass
    class Foo:
        a: list[int]
        b: tuple[int, float]
        c: set[int]
        d: frozenset[int]
        e: dict[str, int]
        f: Bar

    foo_fields = {f.name: f for f in fields(Foo)}
    bar_fields = {f.name: f for f in fields(Bar)}

    data = Foo(a=[1, 2], b=(3, 4.4), c={5, 6}, d=frozenset({7, 8}), e={"p": 9}, f=Bar(x=10, y="hello"))

    with ctxure_config(dispatcher=testregister):
        unstructure(Foo, data, extra=ctxs)
        assert ctxs == [
            c0 := CtxImpl[Foo, Foo, None, loc("$")](None, Foo, "$", "$", None),
            c_a := CtxImpl[list[int], Foo, Foo, loc("$.a")](c0, list[int], "$.a", "$['a']", foo_fields["a"]),
            CtxImpl[int, Foo, list[int], loc("$.a[0]")](c_a, int, "$.a[0]", "$['a'][0]", 0),
            CtxImpl[int, Foo, list[int], loc("$.a[1]")](c_a, int, "$.a[1]", "$['a'][1]", 1),
            c_b := CtxImpl[tuple[int, float], Foo, Foo, loc("$.b")](
                c0, tuple[int, float], "$.b", "$['b']", foo_fields["b"]
            ),
            CtxImpl[int, Foo, tuple[int, float], loc("$.b[0]")](c_b, int, "$.b[0]", "$['b'][0]", 0),
            CtxImpl[float, Foo, tuple[int, float], loc("$.b[1]")](c_b, float, "$.b[1]", "$['b'][1]", 1),
            c_c := CtxImpl[set[int], Foo, Foo, loc("$.c")](c0, set[int], "$.c", "$['c']", foo_fields["c"]),
            CtxImpl[int, Foo, set[int], loc("$.c[?]")](c_c, int, "$.c[?]", "$['c'][0]", None),
            CtxImpl[int, Foo, set[int], loc("$.c[?]")](c_c, int, "$.c[?]", "$['c'][1]", None),
            c_d := CtxImpl[frozenset[int], Foo, Foo, loc("$.d")](c0, frozenset[int], "$.d", "$['d']", foo_fields["d"]),
            CtxImpl[int, Foo, frozenset[int], loc("$.d[?]")](c_d, int, "$.d[?]", "$['d'][0]", None),
            CtxImpl[int, Foo, frozenset[int], loc("$.d[?]")](c_d, int, "$.d[?]", "$['d'][1]", None),
            c_e := CtxImpl[dict[str, int], Foo, Foo, loc("$.e")](c0, dict[str, int], "$.e", "$['e']", foo_fields["e"]),
            CtxImpl[str, Foo, dict[str, int], loc("$.e[~'p']")](c_e, str, "$.e[~'p']", "$['e'][~?]", "p"),
            CtxImpl[int, Foo, dict[str, int], loc("$.e['p']")](c_e, int, "$.e['p']", "$['e']['p']", "p"),
            c_f := CtxImpl[Bar, Foo, Foo, loc("$.f")](c0, Bar, "$.f", "$['f']", foo_fields["f"]),
            CtxImpl[int, Foo, Bar, loc("$.f.x")](c_f, int, "$.f.x", "$['f']['x']", bar_fields["x"]),
            CtxImpl[str, Foo, Bar, loc("$.f.y")](c_f, str, "$.f.y", "$['f']['y']", bar_fields["y"]),
        ]
        ctxs.clear()


def test_unstructure_ctx_typeddict_2(testregister):
    ctxs = []

    @testregister
    def unstructure_hook(ctx: Ctx[Any], data: Any) -> Any:
        ctxs.append(ctx)
        return unstructure_default(ctx, data)

    class Bar(TypedDict):
        x: int
        y: str

    class Foo(TypedDict):
        a: list[int]
        b: tuple[int, float]
        c: set[int]
        d: frozenset[int]
        e: dict[str, int]
        f: Bar

    data = {
        "a": [1, 2],
        "b": (3, 4.4),
        "c": {5, 6},
        "d": frozenset({7, 8}),
        "e": {"p": 9},
        "f": {"x": 10, "y": "hello"},
    }

    with ctxure_config(dispatcher=testregister):
        unstructure(Foo, data, extra=ctxs)
        assert ctxs == [
            c0 := CtxImpl[Foo, Foo, None, loc("$")](None, Foo, "$", "$", None),
            c_a := CtxImpl[list[int], Foo, Foo, loc("$.a")](c0, list[int], "$.a", "$['a']", "a"),
            CtxImpl[int, Foo, list[int], loc("$.a[0]")](c_a, int, "$.a[0]", "$['a'][0]", 0),
            CtxImpl[int, Foo, list[int], loc("$.a[1]")](c_a, int, "$.a[1]", "$['a'][1]", 1),
            c_b := CtxImpl[tuple[int, float], Foo, Foo, loc("$.b")](c0, tuple[int, float], "$.b", "$['b']", "b"),
            CtxImpl[int, Foo, tuple[int, float], loc("$.b[0]")](c_b, int, "$.b[0]", "$['b'][0]", 0),
            CtxImpl[float, Foo, tuple[int, float], loc("$.b[1]")](c_b, float, "$.b[1]", "$['b'][1]", 1),
            c_c := CtxImpl[set[int], Foo, Foo, loc("$.c")](c0, set[int], "$.c", "$['c']", "c"),
            CtxImpl[int, Foo, set[int], loc("$.c[?]")](c_c, int, "$.c[?]", "$['c'][0]", None),
            CtxImpl[int, Foo, set[int], loc("$.c[?]")](c_c, int, "$.c[?]", "$['c'][1]", None),
            c_d := CtxImpl[frozenset[int], Foo, Foo, loc("$.d")](c0, frozenset[int], "$.d", "$['d']", "d"),
            CtxImpl[int, Foo, frozenset[int], loc("$.d[?]")](c_d, int, "$.d[?]", "$['d'][0]", None),
            CtxImpl[int, Foo, frozenset[int], loc("$.d[?]")](c_d, int, "$.d[?]", "$['d'][1]", None),
            c_e := CtxImpl[dict[str, int], Foo, Foo, loc("$.e")](c0, dict[str, int], "$.e", "$['e']", "e"),
            CtxImpl[str, Foo, dict[str, int], loc("$.e[~'p']")](c_e, str, "$.e[~'p']", "$['e'][~?]", "p"),
            CtxImpl[int, Foo, dict[str, int], loc("$.e['p']")](c_e, int, "$.e['p']", "$['e']['p']", "p"),
            c_f := CtxImpl[Bar, Foo, Foo, loc("$.f")](c0, Bar, "$.f", "$['f']", "f"),
            CtxImpl[int, Foo, Bar, loc("$.f.x")](c_f, int, "$.f.x", "$['f']['x']", "x"),
            CtxImpl[str, Foo, Bar, loc("$.f.y")](c_f, str, "$.f.y", "$['f']['y']", "y"),
        ]
        ctxs.clear()


def _set_item(s: set | frozenset, idx: int) -> Any:
    for i, e in enumerate(s):
        if i == idx:
            return e
    raise ValueError()


def test_unstructure_newtype(testregister):
    ctxs = []

    @testregister
    def unstructure_hook(ctx: Ctx[Any], data: Any) -> Any:
        ctxs.append(ctx)
        return unstructure_default(ctx, data)

    Int = NewType("Int", int)

    with ctxure_config(dispatcher=testregister):
        unstructure(Int, 1, extra=ctxs)
        assert ctxs == [CtxImpl[Int, Int, None, loc("$")](None, Int, "$", "$", None)]

    ctxs.clear()

    with ctxure_config(dispatcher=testregister):
        unstructure(list[list[Int]], [[1, 2]], extra=ctxs)
        assert ctxs[2:] == [
            CtxImpl[Int, list[list[Int]], list[Int], loc("$[0][0]")](ctxs[1], Int, "$[0][0]", "$[0][0]", 0),
            CtxImpl[Int, list[list[Int]], list[Int], loc("$[0][1]")](ctxs[1], Int, "$[0][1]", "$[0][1]", 1),
        ]


def test_unstructure_union_hook(testregister):
    ctxs = []

    @testregister
    def unstructure_hook(ctx: Ctx[int | str], data: Any) -> Any:
        ctxs.append(ctx)
        return unstructure_default(ctx, data)

    with ctxure_config(dispatcher=testregister):
        unstructure(int | str, 1, extra=ctxs)
        assert ctxs == [CtxImpl[int | str, int | str, None, loc("$")](None, int | str, "$", "$", None)]

    ctxs.clear()

    with ctxure_config(dispatcher=testregister):
        unstructure(list[list[int | str]], [[1, 2]], extra=ctxs)
        ctx_0 = CtxImpl[list[list[int | str]], list[list[int | str]], None, loc("$")](
            None, list[list[int | str]], "$", "$", None
        )
        ctx_1 = CtxImpl[list[int | str], list[list[int | str]], list[list[int | str]], loc("$[0]")](
            ctx_0, list[int | str], "$[0]", "$[0]", 0
        )
        assert ctxs == [
            CtxImpl[int | str, list[list[int | str]], list[int | str], loc("$[0][0]")](
                ctx_1, int | str, "$[0][0]", "$[0][0]", 0
            ),
            CtxImpl[int | str, list[list[int | str]], list[int | str], loc("$[0][1]")](
                ctx_1, int | str, "$[0][1]", "$[0][1]", 1
            ),
        ]


def test_unstructure_union_member_hook(testregister):
    ctxs = []

    @testregister
    def unstructure_hook(ctx: Ctx[int], data: Any) -> Any:
        ctxs.append(ctx)
        return unstructure_default(ctx, data)

    with ctxure_config(dispatcher=testregister):
        unstructure(int | str, 1, extra=ctxs)
        assert ctxs == [CtxImpl[int, int | str, None, loc("$")](None, int, "$", "$", None)]

    ctxs.clear()

    with ctxure_config(dispatcher=testregister):
        unstructure(list[list[int | str]], [[1, 2]], extra=ctxs)
        ctx_0 = CtxImpl[list[list[int | str]], list[list[int | str]], None, loc("$")](
            None, list[list[int | str]], "$", "$", None
        )
        ctx_1 = CtxImpl[list[int | str], list[list[int | str]], list[list[int | str]], loc("$[0]")](
            ctx_0, list[int | str], "$[0]", "$[0]", 0
        )
        assert ctxs == [
            CtxImpl[int, list[list[int | str]], list[int | str], loc("$[0][0]")](ctx_1, int, "$[0][0]", "$[0][0]", 0),
            CtxImpl[int, list[list[int | str]], list[int | str], loc("$[0][1]")](ctx_1, int, "$[0][1]", "$[0][1]", 1),
        ]
