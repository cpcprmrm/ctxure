from __future__ import annotations

from dataclasses import dataclass

from ctxure import Ctx, ctxure_config, register, unstructure


def test_unstructure_hook_future_annotations():
    local = register.copy()

    @local
    def unstructure_hook(ctx: Ctx[int], data: int) -> int:
        return data * 10

    with ctxure_config(local):
        assert unstructure(int, 2) == 20


def test_unstructure_hook_future_annotations_with_path():
    local = register.copy()

    @dataclass
    class User:
        name: str

    @local
    def unstructure_hook(ctx: Ctx[str, ".name"], data: str) -> str:
        return data.upper()

    with ctxure_config(local):
        assert unstructure(User, User("ada")) == {"name": "ADA"}
