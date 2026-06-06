from dataclasses import dataclass

import pytest

from ctxure import Ctx, NoStructureHook, ctxure_config, structure


def test_structure_ctx_subtypes_simple(testregister):
    @dataclass
    class Foo:
        a: int

    @dataclass
    class Bar(Foo):
        pass

    @testregister.ctx_subtypes
    def structure_hook(ctx: Ctx[Foo], data: int) -> Foo:
        return Foo(data * 10)

    @testregister.ctx_subtypes
    def structure_hook(ctx: Ctx[Foo], data: float) -> Foo:
        return Foo(int(data * 100))

    with ctxure_config(dispatcher=testregister):
        assert structure(Foo, 1) == Foo(10)
        assert structure(Bar, 1) == Foo(10)
        assert structure(Foo, 1.0) == Foo(100)

    with pytest.raises(NoStructureHook) as e:
        structure(Bar, 1.0)
    assert e.value.ctx.structured_type == Bar
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 1.0


def test_structure_ctx_subtypes_union_basic(testregister):
    @dataclass
    class Foo:
        a: int

    @testregister.ctx_subtypes
    def structure_hook(ctx: Ctx[int | None], data: int | None) -> int | None:
        if data is None:
            return None
        return data * 10

    with ctxure_config(dispatcher=testregister):
        assert structure(int | None, 1) == 10
        assert structure(int | None, None) is None
        assert structure(int, 1) == 10
        assert structure(Foo, {"a": 1}) == Foo(10)
        assert structure(list[int], [1, 2]) == [10, 20]
        assert structure(float, 1.1) == 1.1
        assert structure(str | None, "a") == "a"
        assert structure(str, "a") == "a"


def test_structure_ctx_subtypes_multiple_union_hooks(testregister):
    @dataclass
    class Foo:
        a: int

    @testregister.ctx_subtypes
    def structure_hook(ctx: Ctx[int | float], data: int | float) -> int | float:
        return data * 10

    @testregister.ctx_subtypes
    def structure_hook(ctx: Ctx[str | float], data: str | float) -> str | float:
        return data * 2

    with ctxure_config(dispatcher=testregister):
        assert structure(int | float, 1) == 10
        assert structure(int | float, 1.1) == 11.0
        assert structure(int, 1) == 10
        assert structure(float, 1.1) == 11.0
        assert structure(Foo, {"a": 1}) == Foo(10)
        assert structure(list[int], [1, 2]) == [10, 20]
        assert structure(str | float, "a") == "aa"
        assert structure(str | float, 1.1) == 2.2
        assert structure(str, "a") == "aa"
        assert structure(list[str], ["a", "b"]) == ["aa", "bb"]


def test_structure_ctx_subtypes_with_path(testregister):
    @dataclass
    class Foo:
        field: int

    @dataclass
    class Bar:
        field: str

    @testregister.ctx_subtypes
    def structure_hook(ctx: Ctx[int | str, "$.field"], data: int | str) -> int | str:
        if isinstance(data, int):
            return data * 2
        return data * 2

    with ctxure_config(dispatcher=testregister):
        assert structure(Foo, {"field": 1}) == Foo(2)
        assert structure(int, 1) == 1
        assert structure(Bar, {"field": "a"}) == Bar("aa")
        assert structure(str, "a") == "a"


def test_structure_ctx_subtypes_matches_in_hierarchy(testregister):
    @testregister.ctx_subtypes
    def structure_hook(ctx: Ctx[int], data: int) -> int:
        return data * 10

    @testregister.ctx_subtypes
    def structure_hook(ctx: Ctx[int | str], data: int | str) -> int | str:
        return data * 2

    with ctxure_config(dispatcher=testregister):
        assert structure(bool, True) == 10
        assert structure(int, 1) == 10
        assert structure(int | str, 1) == 2
        assert structure(int | str, "a") == "aa"


def test_structure_no_ctx_subtypes_and_ctx_subtypes_mixing(testregister):
    @testregister
    def structure_hook(ctx: Ctx[int], data: int) -> int:
        return data * 10

    @testregister.ctx_subtypes
    def structure_hook(ctx: Ctx[int | str], data: int | str) -> int | str:
        return data * 2

    with ctxure_config(dispatcher=testregister):
        assert structure(bool, True) == 2
        assert structure(int, 1) == 10
        assert structure(int | str, 1) == 2
        assert structure(int | str, "a") == "aa"
