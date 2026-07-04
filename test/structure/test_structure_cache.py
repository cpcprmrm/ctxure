from dataclasses import dataclass
from typing import Any, Literal

from ctxure import Ctx, Of, ctxure_config, get_extra, structure, structure_default


class Counter:
    def __init__(self, wrapped):
        self.wrapped = wrapped
        self.count = 0

    def __call__(self, *args, **kwargs):
        self.count += 1
        return self.wrapped(*args, **kwargs)


def test_structure_site_cache_hit(testregister):
    with ctxure_config(dispatcher=testregister):
        site = None

        # First call populates the cache
        first = structure(int, 1)
        site = testregister.structure_cache.get(int)
        assert site is not None

        counter = Counter(site.dispatch)
        site.dispatch = counter

        # Same type: should hit primary cache (data_type match), no dispatch
        second = structure(int, 2)
        assert counter.count == 0

    assert first == 1
    assert second == 2


def test_structure_site_cache_miss_on_new_data_type(testregister):
    with ctxure_config(dispatcher=testregister):
        first = structure(int, 1)
        site = testregister.structure_cache.get(int)
        counter = Counter(site.dispatch)
        site.dispatch = counter

        # bool is a different data type than int
        second = structure(int, True)
        assert counter.count == 1

    assert first == 1
    assert second == 1


def test_structure_site_secondary_cache_hit(testregister):
    with ctxure_config(dispatcher=testregister):
        structure(int, 1)  # caches int data type
        structure(int, True)  # caches bool data type, dispatches once

        site = testregister.structure_cache.get(int)
        counter = Counter(site.dispatch)
        site.dispatch = counter

        # Both types are now in secondary_cache
        structure(int, 2)
        structure(int, False)
        assert counter.count == 0


def test_structure_cache_cleared_on_hook_registration(testregister):
    with ctxure_config(dispatcher=testregister):
        assert structure(int, 5) == 5

        @testregister
        def structure_hook(ctx: Ctx[int], data: int) -> int:
            return data * 100

        assert structure(int, 5) == 500


def test_structure_child_site_hook_free_bypasses_dispatch(testregister):
    @testregister
    def structure_hook(ctx: Ctx["[0]", int], data: int) -> int:
        return data * 10

    with ctxure_config(dispatcher=testregister):
        assert structure(list[int], [1, 2, 3]) == [10, 2, 3]  # warm up

        list_site = testregister.structure_cache.get(list[int])
        children = list_site.exe.children

        # Index 0 has a matching hook; indices 1 and 2 do not
        assert not children[0].is_bypass_safe
        assert children[1].is_bypass_safe
        assert children[2].is_bypass_safe

        # Wrap dispatch on the hook-free child to verify it is never re-invoked
        counter = Counter(children[1].dispatch)
        children[1].dispatch = counter

        assert structure(list[int], [1, 2, 3]) == [10, 2, 3]
        assert structure(list[int], [4, 5, 6]) == [40, 5, 6]
        assert counter.count == 0


def test_structure_child_site_hook_free_flag_dataclass(testregister):
    @dataclass
    class Foo:
        a: int
        b: int

    @testregister
    def structure_hook(ctx: Ctx[".a", Of[Foo], int], data: int) -> int:
        return data * 10

    with ctxure_config(dispatcher=testregister):
        assert structure(Foo, {"a": 1, "b": 2}) == Foo(10, 2)  # warm up

        site = testregister.structure_cache.get(Foo)
        children = {f: s for f, _, _, s in site.exe.children}

        assert not children["a"].is_bypass_safe  # has a hook
        assert children["b"].is_bypass_safe  # hook-free

        counter = Counter(children["b"].dispatch)
        children["b"].dispatch = counter

        assert structure(Foo, {"a": 3, "b": 4}) == Foo(30, 4)
        assert structure(Foo, {"a": 5, "b": 6}) == Foo(50, 6)
        assert counter.count == 0


def test_structure_default_keymap_secondary_cache(testregister):
    @dataclass
    class Foo:
        a: int
        b: int

    keymap1 = {"b": "B"}
    keymap2 = {"b": "_b"}

    @testregister
    def structure_hook(ctx: Ctx[Foo], data: dict) -> Foo:
        km = keymap1 if data["a"] > 0 else keymap2
        return structure_default(ctx, data, km)

    with ctxure_config(testregister):
        # Warm up: populate both entries in keymap_cache
        structure(Foo, {"a": 1, "B": 2})
        structure(Foo, {"a": -1, "_b": 2})

        exe_holder = testregister.structure_cache.get(Foo).exe
        # The default-exe cache is keyed by (data dtype, id(keymap)); here the data
        # is always a dict, so dtype is `dict`.
        exe1 = exe_holder.keymap_cache[(dict, id(keymap1))][0]
        exe2 = exe_holder.keymap_cache[(dict, id(keymap2))][0]

        # Alternate several times — secondary cache must reuse the same exe objects
        for _ in range(4):
            structure(Foo, {"a": 1, "B": 3})
            structure(Foo, {"a": -1, "_b": 3})

        assert exe_holder.keymap_cache[(dict, id(keymap1))][0] is exe1
        assert exe_holder.keymap_cache[(dict, id(keymap2))][0] is exe2


def test_structure_default_redispatches_per_data_type(testregister):
    # structure_default must re-resolve the default exe per data type, not reuse
    # an exe built for the first data type it saw.
    @dataclass
    class W:
        payload: int | str

    @testregister
    def structure_hook(ctx: Ctx[int | str], data: dict) -> object:
        return structure_default(ctx, data["v"])

    with ctxure_config(dispatcher=testregister):
        assert structure(W, {"payload": {"v": 5}}) == W(5)
        assert structure(W, {"payload": {"v": "hello"}}) == W("hello")
        assert structure(W, {"payload": {"v": 7}}) == W(7)
        assert structure(W, {"payload": {"v": "bye"}}) == W("bye")


def test_structure_extra_updated_on_cached_site(testregister):
    @testregister
    def structure_hook(ctx: Ctx[int], data: Any) -> int:
        return get_extra(ctx)

    with ctxure_config(dispatcher=testregister):
        assert structure(int, 0, extra="first") == "first"
        assert structure(int, 0, extra="second") == "second"
        assert structure(int, 0, extra=None) is None


def test_literal_union_cache_1(testregister):
    """
    Union of Literals needs attention. Interplay between type, value, hook, and cache can be complex.
    """

    @testregister
    def structure_hook(ctx: Ctx[Literal["a"]], data: Any) -> str:
        return "Literal:a"

    with ctxure_config(dispatcher=testregister):
        assert structure(Literal["a"] | str, "a") == "Literal:a"
        assert structure(Literal["a"] | str, "b") == "b"
        assert structure(Literal["a"] | str, "a") == "Literal:a"
        assert structure(Literal["a"] | str, "b") == "b"


def test_literal_union_cache_2(testregister):
    """
    Union of Literals needs attention. Interplay between type, value, hook, and cache can be complex.
    """

    @testregister
    def structure_hook(ctx: Ctx[Literal["a"]], data: Any) -> str:
        return "Literal:a"

    with ctxure_config(dispatcher=testregister):
        assert structure(Literal["a"] | str, "b") == "b"
        assert structure(Literal["a"] | str, "a") == "Literal:a"
        assert structure(Literal["a"] | str, "b") == "b"
        assert structure(Literal["a"] | str, "a") == "Literal:a"
