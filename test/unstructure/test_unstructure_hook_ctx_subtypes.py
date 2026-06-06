from dataclasses import dataclass

import pytest

from ctxure import Ctx, NoUnstructureHook, ctxure_config, unstructure


def test_unstructure_ctx_subtypes_simple(testregister):
    @dataclass
    class Foo:
        a: int

    @dataclass
    class Bar(Foo):
        pass

    @testregister.ctx_subtypes
    def unstructure_hook(ctx: Ctx[Foo], data: int) -> dict:
        return {"a": data * 10}

    @testregister.ctx_subtypes
    def unstructure_hook(ctx: Ctx[Foo], data: float) -> dict:
        return {"a": int(data * 100)}

    with ctxure_config(dispatcher=testregister):
        assert unstructure(Foo, 1) == {"a": 10}
        assert unstructure(Bar, 1) == {"a": 10}
        assert unstructure(Foo, 1.0) == {"a": 100}

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(Bar, 1.0)
    assert e.value.ctx.structured_type == Bar
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 1.0


def test_unstructure_ctx_subtypes_union_basic(testregister):
    @dataclass
    class Foo:
        a: int

    @testregister.ctx_subtypes
    def unstructure_hook(ctx: Ctx[int | None], data: int | None) -> int | None:
        if data is None:
            return None
        return data * 10

    with ctxure_config(dispatcher=testregister):
        assert unstructure(int | None, 1) == 10
        assert unstructure(int | None, None) is None
        assert unstructure(int, 1) == 10
        assert unstructure(Foo, Foo(1)) == {"a": 10}
        assert unstructure(list[int], [1, 2]) == [10, 20]
        assert unstructure(float, 1.1) == 1.1
        assert unstructure(str | None, "a") == "a"
        assert unstructure(str, "a") == "a"


def test_unstructure_ctx_subtypes_multiple_union_hooks(testregister):
    @dataclass
    class Foo:
        a: int

    @testregister.ctx_subtypes
    def unstructure_hook(ctx: Ctx[int | float], data: int | float) -> int | float:
        return data * 10

    @testregister.ctx_subtypes
    def unstructure_hook(ctx: Ctx[str | float], data: str | float) -> str | float:
        return data * 2

    with ctxure_config(dispatcher=testregister):
        assert unstructure(int | float, 1) == 10
        assert unstructure(int | float, 1.1) == 11.0
        assert unstructure(int, 1) == 10
        assert unstructure(float, 1.1) == 11.0
        assert unstructure(Foo, Foo(1)) == {"a": 10}
        assert unstructure(list[int], [1, 2]) == [10, 20]
        assert unstructure(str | float, "a") == "aa"
        assert unstructure(str | float, 1.1) == 2.2
        assert unstructure(str, "a") == "aa"
        assert unstructure(list[str], ["a", "b"]) == ["aa", "bb"]


def test_unstructure_ctx_subtypes_with_path(testregister):
    @dataclass
    class Foo:
        field: int

    @dataclass
    class Bar:
        field: str

    @testregister.ctx_subtypes
    def unstructure_hook(ctx: Ctx[int | str, "$.field"], data: int | str) -> int | str:
        if isinstance(data, int):
            return data * 2
        return data * 2

    with ctxure_config(dispatcher=testregister):
        assert unstructure(Foo, Foo(1)) == {"field": 2}
        assert unstructure(int, 1) == 1
        assert unstructure(Bar, Bar("a")) == {"field": "aa"}
        assert unstructure(str, "a") == "a"


def test_unstructure_ctx_subtypes_matches_in_hierarchy(testregister):
    @testregister.ctx_subtypes
    def unstructure_hook(ctx: Ctx[int], data: int) -> int:
        return data * 10

    @testregister.ctx_subtypes
    def unstructure_hook(ctx: Ctx[int | str], data: int | str) -> int | str:
        return data * 2

    with ctxure_config(dispatcher=testregister):
        assert unstructure(bool, True) == 10
        assert unstructure(int, 1) == 10
        assert unstructure(int | str, 1) == 2
        assert unstructure(int | str, "a") == "aa"


def test_unstructure_no_ctx_subtypes_and_ctx_subtypes_mixing(testregister):
    @testregister
    def unstructure_hook(ctx: Ctx[int], data: int) -> int:
        return data * 10

    @testregister.ctx_subtypes
    def unstructure_hook(ctx: Ctx[int | str], data: int | str) -> int | str:
        return data * 2

    with ctxure_config(dispatcher=testregister):
        assert unstructure(bool, True) == 2
        assert unstructure(int, 1) == 10
        assert unstructure(int | str, 1) == 2
        assert unstructure(int | str, "a") == "aa"
