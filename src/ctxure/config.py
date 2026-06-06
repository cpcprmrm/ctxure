from contextlib import contextmanager
from contextvars import ContextVar

from ctxure.ctxdispatch import CtxureDispatch

register = CtxureDispatch()


_dispatcher = ContextVar("_dispatcher", default=register)


@contextmanager
def ctxure_config(dispatcher: CtxureDispatch | None = None):
    tokens = []
    if dispatcher is not None:
        tokens.append(_dispatcher.set(dispatcher))
    try:
        yield
    finally:
        for t in reversed(tokens):
            t.var.reset(t)
