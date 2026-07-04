from collections.abc import Callable
from typing import Any, Never

from ctxure.context import CtxImpl
from ctxure.multidispatch import Method

Exe = Callable[[CtxImpl, Any], Any]


class Site:
    __slots__ = (
        "ctx",
        "root",
        "exe",
        "data",
        "extra",
        "data_type",
        "secondary_cache",
        "is_bypass_safe",
        "is_literal_free",
    )

    ctx: CtxImpl
    root: "Site"
    exe: Exe
    data: Any
    extra: Any
    data_type: Any
    secondary_cache: dict[Any, Exe]
    is_literal_free: bool

    def __init__(self, ctx: CtxImpl):
        self.ctx = ctx
        # If ctx was produced by `replace_type` at the root (parent is None) it carries the outer site in `_site`.
        # Honour that chain so `get_extra` keeps working through re-entries like DataClassUnionExe.
        # Otherwise the new site would become its own root and sever it.
        prior_site = ctx._site
        ctx._site = self
        if ctx.parent is not None:
            self.root = ctx.parent._site.root  # type: ignore
        elif prior_site is not None:
            self.root = prior_site.root
        else:
            self.root = self
        self.exe = _dummy_exe
        self.data = None
        self.extra = None
        self.data_type = Never
        self.secondary_cache = {}
        self.is_bypass_safe = False
        self.is_literal_free = True

    def __call__(self, data: Any) -> Any:
        # I'm not happy with the mutations here. However, it buys large performance benefits.
        self.data = data
        if self.is_literal_free and type(data) is self.data_type:  # fast path for common cases
            return self.exe(self.ctx, data)
        dtype = self.dtype(data)
        if dtype == self.data_type:
            return self.exe(self.ctx, data)
        if exe := self.secondary_cache.get(dtype):
            self.exe = exe
            self.data_type = dtype
            return exe(self.ctx, data)
        if exe := self.dispatch(self.ctx, data):
            self.exe = exe
            self.data_type = dtype
            self.secondary_cache[self.data_type] = exe
            return self.exe(self.ctx, data)
        raise AssertionError("Bug: unreachable")  # pragma: no cover

    def dispatch(self, ctx: CtxImpl, data: Any) -> Exe:
        raise NotImplementedError()  # pragma: no cover

    def dtype(self, data: Any) -> Any:
        raise NotImplementedError()  # pragma: no cover


def _dummy_exe(ctx, data) -> None:  # pragma: no cover
    raise AssertionError("Bug: unreachable")


def mark_not_bypass_safe(site: Site) -> None:
    current: Site | None = site
    while current is not None:
        if not current.is_bypass_safe:
            break
        current.is_bypass_safe = False
        parent_ctx = current.ctx.parent
        current = parent_ctx._site if parent_ctx is not None else None


_KeymapType = dict[str, str]


class HookExe:
    __slots__ = ("hook", "default_exe", "default_dtype", "by_type_site", "keymap", "keymap_cache")

    hook: Method
    default_exe: Exe | None
    default_dtype: Any
    by_type_site: "Site | None"
    keymap: _KeymapType | None
    keymap_cache: dict[tuple[Any, int], tuple[Exe, _KeymapType]] | None

    def __init__(self, hook: Method):
        self.hook = hook
        self.default_exe = None
        self.default_dtype = None
        self.by_type_site = None
        self.keymap = None
        self.keymap_cache = None

    def __call__(self, ctx: CtxImpl, data: Any):
        return self.hook(ctx, data)
