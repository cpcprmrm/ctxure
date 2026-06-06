import inspect
from collections.abc import Callable
from typing import Any, Self, get_args, get_origin, get_type_hints

from ctxure._exetree import Site
from ctxure._location import KeySeg
from ctxure.context import CtxImpl
from ctxure.multidispatch import Dispatch, Multimethod


class CtxureDispatch:
    dispatch: Dispatch
    structure_cache: dict[Any, Site]
    unstructure_cache: dict[Any, Site]
    active_structure: bool
    active_unstructure: bool

    def __init__(self):
        self.dispatch = Dispatch()
        self.structure_cache = {}
        self.unstructure_cache = {}
        self.active_structure = False
        self.active_unstructure = False

    @property
    def ctx_subtypes(self) -> Callable[..., Multimethod]:
        def decorator(func: Callable) -> Multimethod:
            if self._is_ctxure_handler(func):
                return self(func, ctx_subtypes=True)
            else:
                raise TypeError("Only ctxure handlers can be registered with ctx_subtypes")

        return decorator

    def __call__(
        self,
        func: Callable[..., Any],
        ctx_subtypes: bool = False,
    ) -> Multimethod:
        if self._is_ctxure_handler(func):
            if func.__name__ == "structure_hook":
                self._validate_structure_hook(func)
            elif func.__name__ == "unstructure_hook":
                self._validate_unstructure_hook(func)
            covariant_args = (0, 1) if ctx_subtypes else (1,)
            mm = self.dispatch(func, covariant_args=covariant_args)
            self.structure_cache.clear()
            self.unstructure_cache.clear()
        else:
            mm = self.dispatch(func)
        return mm

    _ctxure_HANDLER_NAMES = {
        "structure_hook",
        "unstructure_hook",
        "_structure_default",
        "_unstructure_default",
    }

    def _is_ctxure_handler(self, func: Callable) -> bool:
        return func.__name__ in self._ctxure_HANDLER_NAMES

    def copy(self) -> Self:
        new = object.__new__(type(self))
        new.dispatch = self.dispatch.copy()
        new.structure_cache = {}
        new.unstructure_cache = {}
        new.active_structure = False
        new.active_unstructure = False
        return new

    def _validate_structure_hook(self, func) -> None:
        ctx_hint = _ctx_param_hint(func)
        for seg in _path_segs(ctx_hint):
            if get_origin(seg) is not KeySeg:
                continue
            seg_args = get_args(seg)
            if seg_args and seg_args[0] is not Any:
                raise TypeError(
                    f"Specific dict-key constraint in structure_hook is meaningless: "
                    f"the structured key does not exist yet during structuring. "
                    f"Use `[~?]` instead. (at {func.__module__}.{func.__qualname__})"
                )

    def _validate_unstructure_hook(self, func) -> None:
        _ctx_param_hint(func)


def _ctx_param_hint(func: Callable) -> Any:
    sig = inspect.signature(func)
    params = [
        p
        for p in sig.parameters.values()
        if p.kind in {inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD}
    ]
    if len(params) != 2:
        raise TypeError("The signature of a hook should be (ctx: Ctx[...], data: ...)")
    hints = get_type_hints(func, include_extras=True)
    ctx_hint = hints.get(params[0].name)
    if ctx_hint is None or get_origin(ctx_hint) is not CtxImpl:
        raise TypeError("The signature of a hook should be (ctx: Ctx[...], data: ...)")
    return ctx_hint


def _path_segs(ctx_hint: Any):  # pragma: no cover
    args = get_args(ctx_hint)
    if len(args) < 4:
        return
    path = args[3]
    if path is Any:
        return
    pargs = get_args(path)
    if len(pargs) != 2:
        return
    prefix, last_seg = pargs
    if get_origin(prefix) is tuple:
        yield from get_args(prefix)
    yield last_seg
