from collections.abc import Mapping
from typing import Any, Literal

from ctxure import Ctx, Of, ctxure_config, structure, structure_default


def test_structure_hook_frozendict_target(testregister):
    @testregister
    def structure_hook(ctx: Ctx[frozendict[str, int]], data: dict) -> frozendict:
        return structure_default(ctx, {k.upper(): v for k, v in data.items()})

    with ctxure_config(dispatcher=testregister):
        assert structure(frozendict[str, int], {"a": 1}) == frozendict(A=1)
        # Not fired for other type arguments or for dict.
        assert structure(frozendict[str, float], {"a": 1}) == frozendict(a=1.0)
        assert structure(dict[str, int], {"a": 1}) == {"a": 1}


def test_structure_hook_frozendict_data(testregister):
    @testregister
    def structure_hook(ctx: Ctx[dict[str, int]], data: frozendict) -> dict:
        return {"from": len(data)}

    with ctxure_config(dispatcher=testregister):
        assert structure(dict[str, int], frozendict(a=1, b=2)) == {"from": 2}
        assert structure(dict[str, int], {"a": 1}) == {"a": 1}


def test_structure_hook_frozendict_any_data(testregister):
    @testregister
    def structure_hook(ctx: Ctx[str], data: frozendict[Any, Any]) -> str:
        return ",".join(data)

    with ctxure_config(dispatcher=testregister):
        assert structure(str, frozendict(a=1, b=2)) == "a,b"


def test_structure_hook_ctx_subtypes_mapping(testregister):
    @testregister.ctx_subtypes
    def structure_hook(ctx: Ctx[Mapping[str, int]], data: dict) -> Any:
        return "mapping"

    with ctxure_config(dispatcher=testregister):
        assert structure(frozendict[str, int], {"a": 1}) == "mapping"
        assert structure(dict[str, int], {"a": 1}) == "mapping"
        assert structure(frozendict[str, str], {"a": "x"}) == frozendict(a="x")


def test_structure_hook_of_frozendict(testregister):
    @testregister
    def structure_hook(ctx: Ctx[int, Of[frozendict[str, int]]], data: int) -> int:
        return data * 10

    with ctxure_config(dispatcher=testregister):
        assert structure(frozendict[str, int], {"a": 1}) == frozendict(a=10)
        assert structure(dict[str, int], {"a": 1}) == {"a": 1}


def test_structure_hook_literal_data_with_unhashable_frozendict(testregister):
    # A Literal data hint makes every structuring look the data up among literal values.
    # A frozendict holding a list passes isinstance(_, Hashable) but raises TypeError when hashed.
    @testregister
    def structure_hook(ctx: Ctx[str], data: Literal["x"]) -> str:
        return "X"

    with ctxure_config(dispatcher=testregister):
        assert structure(dict[str, list[int]], frozendict(a=[1])) == {"a": [1]}
        assert structure(Any, frozendict(a=[1])) == frozendict(a=[1])
