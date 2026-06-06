from __future__ import annotations

from dataclasses import dataclass

from ctxure import Ctx, ctxure_config, register, structure


def test_structure_hook_future_annotations():
    local = register.copy()

    @local
    def structure_hook(ctx: Ctx[int], data: int) -> int:
        return data * 10

    with ctxure_config(local):
        assert structure(int, 2) == 20


def test_structure_hook_future_annotations_with_path():
    local = register.copy()

    @dataclass
    class User:
        name: str

    @local
    def structure_hook(ctx: Ctx[str, ".name"], data: str) -> str:
        return data.upper()

    with ctxure_config(local):
        assert structure(User, {"name": "ada"}) == User("ADA")
