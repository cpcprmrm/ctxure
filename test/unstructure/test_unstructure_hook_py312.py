from typing import Literal

from ctxure import Ctx, ctxure_config, unstructure


type A = Literal["a"]


def test_unstructure_hook_for_literal_alias_dict_key_path(testregister):
    @testregister
    def unstructure_hook(ctx: Ctx[int, "$['a']"], data: int) -> int:
        return data + 100

    with ctxure_config(dispatcher=testregister):
        assert unstructure(dict[A, int], {"a": 1}) == {"a": 101}
        assert unstructure(dict[A, int], {"a": 2}) == {"a": 102}
