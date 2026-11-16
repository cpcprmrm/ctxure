from typing import Any, Literal

from ctxure import Ctx, ctxure_config, unstructure


def test_unstructure_hook_frozendict_declared(testregister):
    @testregister
    def unstructure_hook(ctx: Ctx[frozendict[str, int]], data: frozendict) -> list:
        return sorted(data)

    with ctxure_config(dispatcher=testregister):
        assert unstructure(frozendict[str, int], frozendict(b=1, a=2)) == ["a", "b"]
        assert unstructure(frozendict[str, float], frozendict(a=1.0)) == {"a": 1.0}


def test_unstructure_hook_frozendict_data_at_any(testregister):
    @testregister
    def unstructure_hook(ctx: Ctx[Any], data: frozendict) -> str:
        return "fd"

    with ctxure_config(dispatcher=testregister):
        assert unstructure(Any, [frozendict(a=1), {"a": 1}]) == ["fd", {"a": 1}]


def test_unstructure_hook_literal_data_with_unhashable_frozendict(testregister):
    # A Literal data hint makes every unstructuring look the data up among literal values.
    # A frozendict holding a list passes isinstance(_, Hashable) but raises TypeError when hashed.
    @testregister
    def unstructure_hook(ctx: Ctx[str], data: Literal["x"]) -> str:
        return "X"

    with ctxure_config(dispatcher=testregister):
        assert unstructure(frozendict[str, list[int]], frozendict(a=[1])) == {"a": [1]}
        assert unstructure(Any, frozendict(a=[1])) == {"a": [1]}
