from dataclasses import dataclass, fields
from typing import Any

from ctxure import ctxure_config, structure, structure_default
from ctxure.context import Ctx, CtxImpl, get_extra

from ..util import loc


def test_structure_ctx_dataclass_generic_1_py312(testregister):
    ctxs = []

    @testregister
    def structure_hook(ctx: Ctx[Any], data: Any) -> Any:
        get_extra(ctx).append(ctx)
        return structure_default(ctx, data)

    @dataclass
    class Foo[T]:
        a: T

    foo_fields = {f.name: f for f in fields(Foo)}

    with ctxure_config(dispatcher=testregister):
        structure(Foo[int], {"a": 1}, extra=ctxs)
        assert ctxs == [
            c0 := CtxImpl[Foo[int], Foo[int], None, loc("$")](None, Foo[int], "$", "$", None),
            CtxImpl[int, Foo[int], Foo[int], loc("$.a")](c0, int, "$.a", "$['a']", foo_fields["a"]),
        ]
        ctxs.clear()

    with ctxure_config(dispatcher=testregister):
        structure(Foo[str], {"a": "x"}, extra=ctxs)
        assert ctxs == [
            c0 := CtxImpl[Foo[str], Foo[str], None, loc("$")](None, Foo[str], "$", "$", None),
            CtxImpl[str, Foo[str], Foo[str], loc("$.a")](c0, str, "$.a", "$['a']", foo_fields["a"]),
        ]
        ctxs.clear()

    with ctxure_config(dispatcher=testregister):
        structure(Foo, {"a": 1}, extra=ctxs)
        assert ctxs == [
            c0 := CtxImpl[Foo, Foo, None, loc("$")](None, Foo, "$", "$", None),
            CtxImpl[Any, Foo, Foo, loc("$.a")](c0, Any, "$.a", "$['a']", foo_fields["a"]),
        ]
        ctxs.clear()

    with ctxure_config(dispatcher=testregister):
        structure(Foo[Any], {"a": 1}, extra=ctxs)
        assert ctxs == [
            c0 := CtxImpl[Foo[Any], Foo[Any], None, loc("$")](None, Foo[Any], "$", "$", None),
            CtxImpl[Any, Foo[Any], Foo[Any], loc("$.a")](c0, Any, "$.a", "$['a']", foo_fields["a"]),
        ]
        ctxs.clear()
