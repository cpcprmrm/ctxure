from typing import Literal

from ctxure import Ctx, ctxure_config, structure


type A = Literal["a"]

type B = A


def test_structure_hook_for_literal_alias_union_cache(testregister):
    Target = A | str

    @testregister
    def structure_hook(ctx: Ctx[Literal["a"]], data: str) -> str:
        return "literal-a"

    with ctxure_config(dispatcher=testregister):
        assert structure(Target, "a") == "literal-a"
        assert structure(Target, "b") == "b"
        assert structure(Target, "a") == "literal-a"
        assert structure(Target, "b") == "b"


def test_structure_hook_for_nested_literal_alias_union_cache(testregister):
    Target = B | str

    @testregister
    def structure_hook(ctx: Ctx[Literal["a"]], data: str) -> str:
        return "literal-a"

    with ctxure_config(dispatcher=testregister):
        assert structure(Target, "a") == "literal-a"
        assert structure(Target, "b") == "b"
        assert structure(Target, "a") == "literal-a"
        assert structure(Target, "b") == "b"


def test_structure_hook_for_literal_alias_dict_key_path(testregister):
    @testregister
    def structure_hook(ctx: Ctx[int, "$['a']"], data: int) -> int:
        return data + 100

    with ctxure_config(dispatcher=testregister):
        assert structure(dict[A, int], {"a": 1}) == {"a": 101}
        assert structure(dict[A, int], {"a": 2}) == {"a": 102}
