from dataclasses import dataclass
from typing import Any

from ctxure import Ctx, Of, ctxure_config, get_extra, unstructure, unstructure_default


class Counter:
    def __init__(self, wrapped):
        self.wrapped = wrapped
        self.count = 0

    def __call__(self, *args, **kwargs):
        self.count += 1
        return self.wrapped(*args, **kwargs)


def test_unstructure_site_cache_hit(testregister):
    with ctxure_config(dispatcher=testregister):
        first = unstructure(int, 1)
        site = testregister.unstructure_cache.get(int)
        assert site is not None

        counter = Counter(site.dispatch)
        site.dispatch = counter

        second = unstructure(int, 2)
        assert counter.count == 0

    assert first == 1
    assert second == 2


def test_unstructure_site_cache_miss_on_new_data_type(testregister):
    with ctxure_config(dispatcher=testregister):
        first = unstructure(int, 1)
        site = testregister.unstructure_cache.get(int)
        counter = Counter(site.dispatch)
        site.dispatch = counter
        second = unstructure(int, True)
        assert counter.count == 1

    assert first == 1
    assert second == 1


def test_unstructure_site_secondary_cache_hit(testregister):
    with ctxure_config(dispatcher=testregister):
        unstructure(int, 1)
        unstructure(int, True)

        site = testregister.unstructure_cache.get(int)
        counter = Counter(site.dispatch)
        site.dispatch = counter

        unstructure(int, 2)
        unstructure(int, False)
        assert counter.count == 0


def test_unstructure_cache_cleared_on_hook_registration(testregister):
    with ctxure_config(dispatcher=testregister):
        assert unstructure(int, 5) == 5

        @testregister
        def unstructure_hook(ctx: Ctx[int], data: int) -> int:
            return data * 100

        assert unstructure(int, 5) == 500


def test_unstructure_child_site_hook_free_bypasses_dispatch(testregister):
    """
    Hook-free child sites bypass Site.__call__ after warmup. Hook-having ones still fire.
    """

    @testregister
    def unstructure_hook(ctx: Ctx["[0]", int], data: int) -> int:
        return data * 10

    with ctxure_config(dispatcher=testregister):
        assert unstructure(list[int], [1, 2, 3]) == [10, 2, 3]  # warm up

        list_site = testregister.unstructure_cache.get(list[int])
        children = list_site.exe.children

        assert not children[0].is_bypass_safe
        assert children[1].is_bypass_safe
        assert children[2].is_bypass_safe

        counter = Counter(children[1].dispatch)
        children[1].dispatch = counter

        assert unstructure(list[int], [1, 2, 3]) == [10, 2, 3]
        assert unstructure(list[int], [4, 5, 6]) == [40, 5, 6]
        assert counter.count == 0


def test_unstructure_child_site_hook_free_flag_dataclass(testregister):
    """
    Fields with a matching hook are not hook-free. Others are.
    """

    @dataclass
    class Foo:
        a: int
        b: int

    @testregister
    def unstructure_hook(ctx: Ctx[".a", Of[Foo], int], data: int) -> int:
        return data * 10

    with ctxure_config(dispatcher=testregister):
        assert unstructure(Foo, Foo(1, 2)) == {"a": 10, "b": 2}  # warm up

        site = testregister.unstructure_cache.get(Foo)
        children = {f: s for f, _, s in site.exe.children}

        assert not children["a"].is_bypass_safe  # has a hook
        assert children["b"].is_bypass_safe  # hook-free

        counter = Counter(children["b"].dispatch)
        children["b"].dispatch = counter

        assert unstructure(Foo, Foo(3, 4)) == {"a": 30, "b": 4}
        assert unstructure(Foo, Foo(5, 6)) == {"a": 50, "b": 6}
        assert counter.count == 0


def test_unstructure_default_keymap_secondary_cache(testregister):
    @dataclass
    class Foo:
        a: int
        b: int

    keymap1 = {"b": "B"}
    keymap2 = {"b": "_b"}

    @testregister
    def unstructure_hook(ctx: Ctx[Foo], data: Foo) -> dict:
        km = keymap1 if data.a > 0 else keymap2
        return unstructure_default(ctx, data, km)

    with ctxure_config(testregister):
        unstructure(Foo, Foo(1, 2))
        unstructure(Foo, Foo(-1, 2))

        exe_holder = testregister.unstructure_cache.get(Foo).exe
        exe1 = exe_holder.keymap_cache[id(keymap1)][0]
        exe2 = exe_holder.keymap_cache[id(keymap2)][0]

        for _ in range(4):
            unstructure(Foo, Foo(1, 3))
            unstructure(Foo, Foo(-1, 3))

        assert exe_holder.keymap_cache[id(keymap1)][0] is exe1
        assert exe_holder.keymap_cache[id(keymap2)][0] is exe2


def test_unstructure_extra_updated_on_cached_site(testregister):
    @testregister
    def unstructure_hook(ctx: Ctx[int], data: Any) -> Any:
        return get_extra(ctx)

    with ctxure_config(dispatcher=testregister):
        assert unstructure(int, 0, extra="first") == "first"
        assert unstructure(int, 0, extra="second") == "second"
        assert unstructure(int, 0, extra=None) is None
