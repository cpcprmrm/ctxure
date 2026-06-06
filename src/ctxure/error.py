from typing import Any

from ctxure._util import format_typeform
from ctxure.context import CtxImpl
from ctxure.multidispatch import Method


class CtxureError(Exception): ...


class NoStructureHook(CtxureError):
    def __init__(self, ctx: CtxImpl, data: Any, msg: str | None = None, msg_with_path: bool = True):
        self.ctx = ctx
        self.data = data
        if not msg:
            msg = f"No structure hook found for data type {_type_repr(data)} with target type {ctx.structured_type}"
        if msg_with_path:
            msg = f"{msg} (at {ctx.structured_path})"
        super().__init__(msg)


class MultipleStructureHooks(CtxureError):
    def __init__(
        self,
        ctx: CtxImpl,
        data: Any,
        candidates: list[Method] | None = None,
        msg: str | None = None,
        msg_with_path: bool = True,
    ):
        self.ctx = ctx
        self.data = data
        self.candidates = candidates or []
        default_msg = msg is None
        if default_msg:
            msg = (
                f"Multiple structure hooks found for data type {_type_repr(data)} "
                f"with target type {ctx.structured_type}"
            )
        if msg_with_path:
            msg = f"{msg} (at {ctx.structured_path})"
        if default_msg and self.candidates:
            msg = msg + "\n" + _format_candidates(self.candidates)
        super().__init__(msg)


class ValidationError(CtxureError):
    def __init__(self, ctx: CtxImpl, data: Any, msg: str | None = None, msg_with_path: bool = True):
        self.ctx = ctx
        self.data = data
        if msg_with_path:
            msg = f"{msg} (at {ctx.structured_path})"
        super().__init__(msg)


class MissingFields(ValidationError):
    def __init__(self, ctx: CtxImpl, data: Any, missing: list[str], msg: str | None = None):
        self.missing = missing
        if not msg:
            label = "field" if len(missing) == 1 else "fields"
            msg = f"Missing {label} {', '.join(missing)} in {ctx.structured_type}"
        super().__init__(ctx, data, msg)


class ExtraFields(ValidationError):
    def __init__(self, ctx: CtxImpl, data: Any, extra: list[Any], msg: str | None = None):
        self.extra = extra
        if not msg:
            label = "field" if len(extra) == 1 else "fields"
            msg = f"Extra {label} {', '.join(repr(k) for k in extra)} in {ctx.structured_type}"
        super().__init__(ctx, data, msg)


class NoUnstructureHook(CtxureError):
    def __init__(self, ctx: CtxImpl, data: Any, msg: str | None = None, msg_with_path: bool = True):
        self.ctx = ctx
        self.data = data
        if not msg:
            msg = f"No unstructure hook found for data type {_type_repr(data)} with declared type {ctx.structured_type}"
        if msg_with_path:
            msg = f"{msg} (at {ctx.structured_path})"
        super().__init__(msg)


class MultipleUnstructureHooks(CtxureError):
    def __init__(
        self,
        ctx: CtxImpl,
        data: Any,
        candidates: list[Method] | None = None,
        msg: str | None = None,
        msg_with_path: bool = True,
    ):
        self.ctx = ctx
        self.data = data
        self.candidates = candidates or []
        default_msg = msg is None
        if default_msg:
            msg = (
                f"Multiple unstructure hooks found for data type {_type_repr(data)} "
                f"with declared type {ctx.structured_type}"
            )
        if msg_with_path:
            msg = f"{msg} (at {ctx.structured_path})"
        if default_msg and self.candidates:
            msg = msg + "\n" + _format_candidates(self.candidates)
        super().__init__(msg)


class AmbiguousUnion(CtxureError):
    def __init__(self, ctx: CtxImpl, data: Any, msg: str, msg_with_path: bool = True):
        self.ctx = ctx
        self.data = data
        if msg_with_path:
            msg = f"{msg} (at {ctx.structured_path})"
        super().__init__(msg)


class ReentranceError(CtxureError):
    def __init__(self):
        super().__init__("Reentrance is not allowed")


def _type_repr(data: Any) -> str:
    if orig_class := getattr(data, "__orig_class__", None):
        return str(orig_class)
    else:
        return str(type(data))


def _format_candidates(candidates: list[Method]) -> str:
    lines = ["Candidates:"]
    for m in candidates:
        code = m.func.__code__
        sig_str = "(" + ", ".join(format_typeform(t) for t in m.signature) + ")"
        lines.append(f"  {sig_str} at {code.co_filename}:{code.co_firstlineno}")
    return "\n".join(lines)
