import base64
import typing
from collections.abc import Hashable, Sequence
from dataclasses import fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from functools import partial
from pathlib import Path
from types import NoneType
from typing import Any, Literal, Never, cast, get_args, get_origin
from uuid import UUID

from typing_extensions import is_typeddict

from ctxure import config
from ctxure._exetree import Exe, HookExe, Site, mark_not_bypass_safe
from ctxure._location import KeySeg, format_field
from ctxure._typeutil import (
    get_typeddict_extras_policy,
    is_union,
    literal_key,
    literal_values_contain,
    normalized_origin_args,
    resolve_field_types,
    resolve_typeddict_field_types,
)
from ctxure._unionutil import generate_decision_func, probe_union_candidates, select_union_candidate
from ctxure._util import get_type_param, itemref_path, key_repr, typeddict_key_path
from ctxure.context import CtxImpl
from ctxure.error import (
    AmbiguousUnion,
    MultipleUnstructureHooks,
    NoUnstructureHook,
    ReentranceError,
    ValidationError,
)
from ctxure.multidispatch import (
    DataClassBase,
    LiteralBase,
    NewTypeBase,
    NoMatchFound,
    TypedDictBase,
    UnionBase,
    is_subtype_covariant,
)

register = config.register


class UnstructureSite(Site):
    _mm_arg_type: Any
    _literal_targets: dict[tuple[type, Any], Any]

    def __init__(self, ctx: CtxImpl):
        super().__init__(ctx)
        dispatch = config._dispatcher.get().dispatch
        hook = dispatch.get("unstructure_hook")
        default = dispatch["_unstructure_default"]
        self._mm_arg_type = partial((hook or default).arg_type, 1)  # Dirty micro-optimization # type: ignore
        self._literal_targets = _collect_target_literals(ctx.structured_type)
        self.is_literal_free = not self._literal_targets
        self.is_bypass_safe = (not hook or not hook.partial_dispatch(ctx.__orig_class__)) and self.is_literal_free
        if not self.is_bypass_safe and ctx.parent is not None:
            mark_not_bypass_safe(ctx.parent._site)  # type: ignore

    def dispatch(self, ctx: CtxImpl, data: Any) -> Exe:
        try:
            return _unstructure_exe(ctx, data)
        except NoMatchFound:
            raise NoUnstructureHook(ctx, data)

    def dtype(self, data: Any) -> Any:
        if self._literal_targets and isinstance(data, Hashable):
            if promoted := self._literal_targets.get((type(data), data)):
                return promoted
        return self._mm_arg_type(data)


def _collect_target_literals(target: Any) -> dict[tuple[type, Any], Any]:
    collected = {}
    _walk_target_literals(target, collected)
    return collected


def _walk_target_literals(t: Any, lookup: dict[tuple[type, Any], Any]) -> None:
    origin, args = normalized_origin_args(t)
    if origin is Literal:
        for v in args:
            key = literal_key(v)
            if key not in lookup:
                lookup[key] = Literal[v]
    elif is_union(t):
        for m in get_args(t):
            _walk_target_literals(m, lookup)


def unstructure(declared_type: Any, data: Any, extra: Any = None) -> Any:
    dispatcher = config._dispatcher.get()
    if dispatcher.active_unstructure:
        raise ReentranceError()
    try:
        cache = dispatcher.unstructure_cache
        dispatcher.active_unstructure = True
        if (site := cache.get(declared_type, None)) is None:
            root_ctx = CtxImpl.create(None, declared_type, "$", "$", None)
            site = UnstructureSite(root_ctx)
            cache[declared_type] = site
        site.extra = extra
        return site(data)
    finally:
        dispatcher.active_unstructure = False


_MAX_KEYMAP_CACHE_ENTRY = 16


@typing.no_type_check
def unstructure_default(ctx: CtxImpl, data: Any, keymap: dict[str, str] | None = None) -> Any:
    exe_holder = ctx._site.exe
    dtype = ctx._site.dtype(data)
    if exe_holder.default_exe is not None and exe_holder.default_dtype == dtype and exe_holder.keymap is keymap:
        return exe_holder.default_exe(ctx, data)
    cache = exe_holder.keymap_cache
    if cache is None:
        cache = exe_holder.keymap_cache = {}
    cache_key = (dtype, id(keymap))
    cached = cache.get(cache_key)
    if cached is None or cached[1] is not keymap:
        exe = config._dispatcher.get().dispatch["_unstructure_default"](ctx, data, keymap=keymap)
        if len(cache) >= _MAX_KEYMAP_CACHE_ENTRY:
            cache.clear()
        cache[cache_key] = (exe, keymap)
    else:
        exe = cached[0]
    exe_holder.default_exe = exe
    exe_holder.default_dtype = dtype
    exe_holder.keymap = keymap
    return exe(ctx, data)


@typing.no_type_check
def unstructure_by_type(ctx: CtxImpl, data: Any) -> Any:
    exe_holder = cast(HookExe, ctx._site.exe)  # type: ignore
    site = exe_holder.by_type_site
    if site is None:
        site = UnstructureSite(ctx._strip())
        exe_holder.by_type_site = site
    return site(data)


def _unstructure_site(ctx: Any) -> Site:
    return UnstructureSite(ctx)


def _unstructure_exe(ctx: Any, data: Any) -> Exe:
    dispatch = config._dispatcher.get().dispatch
    methods = []
    if hook := dispatch.get("unstructure_hook", None):
        methods = hook.dispatch(ctx.__orig_class__, hook.arg_type(1, data))
    match len(methods):
        case 0:
            _unstructure_default = dispatch["_unstructure_default"]
            return _unstructure_default(ctx, data, keymap=None)
        case 1:
            return HookExe(methods[0])
        case _:
            raise MultipleUnstructureHooks(ctx, data, methods)


@register
def _unstructure_default(
    ctx: CtxImpl[NoneType, Any, Any, Any], data: NoneType, *, keymap: dict[str, str] | None
) -> Exe:
    return none_exe


def none_exe(ctx: CtxImpl[NoneType, Any, Any, Any], data: None) -> None:
    return None


@register
def _unstructure_default(ctx: CtxImpl[int, Any, Any, Any], data: int, *, keymap: dict[str, str] | None) -> Exe:
    return int_exe


def int_exe(ctx: CtxImpl[int, Any, Any, Any], data: int) -> int:
    return int(data)


@register
def _unstructure_default(ctx: CtxImpl[bool, Any, Any, Any], data: bool, *, keymap: dict[str, str] | None) -> Exe:
    return bool_exe


@register
def _unstructure_default(ctx: CtxImpl[bool, Any, Any, Any], data: int, *, keymap: dict[str, str] | None) -> Exe:
    return bool_from_int_exe


def bool_exe(ctx: CtxImpl[bool, Any, Any, Any], data: bool) -> bool:
    return data


def bool_from_int_exe(ctx: CtxImpl[bool, Any, Any, Any], data: int) -> bool:
    return data != 0


@register
def _unstructure_default(ctx: CtxImpl[float, Any, Any, Any], data: float, *, keymap: dict[str, str] | None) -> Exe:
    return float_exe


def float_exe(ctx: CtxImpl[float, Any, Any, Any], data: float) -> float:
    return float(data)


@register
def _unstructure_default(ctx: CtxImpl[str, Any, Any, Any], data: str, *, keymap: dict[str, str] | None) -> Exe:
    return str_exe


def str_exe(ctx: CtxImpl[str, Any, Any, Any], data: str) -> str:
    return data


@register.ctx_subtypes
def _unstructure_default(ctx: CtxImpl[Enum, Any, Any, Any], data: Enum, *, keymap: dict[str, str] | None) -> Exe:
    return enum_exe


def enum_exe(ctx: CtxImpl[Enum, Any, Any, Any], data: Enum) -> Any:
    return data.value


@register.ctx_subtypes
def _unstructure_default(
    ctx: CtxImpl[Enum, Any, Any, tuple[Any, KeySeg[Any]]], data: Any, *, keymap: dict[str, str] | None
) -> Exe:
    return enum_key_exe


def enum_key_exe(ctx: CtxImpl[Enum, Any, Any, Any], data: Any) -> str:
    return str(data.value)


@register
def _unstructure_default(ctx: CtxImpl[Path, Any, Any, Any], data: Path, *, keymap: dict[str, str] | None) -> Exe:
    return path_exe


def path_exe(ctx: CtxImpl[Path, Any, Any, Any], data: Path) -> str:
    return str(data)


@register
def _unstructure_default(ctx: CtxImpl[UUID, Any, Any, Any], data: UUID, *, keymap: dict[str, str] | None) -> Exe:
    return uuid_exe


def uuid_exe(ctx: CtxImpl[UUID, Any, Any, Any], data: UUID) -> str:
    return str(data)


@register
def _unstructure_default(ctx: CtxImpl[Decimal, Any, Any, Any], data: Decimal, *, keymap: dict[str, str] | None) -> Exe:
    return decimal_exe


def decimal_exe(ctx: CtxImpl[Decimal, Any, Any, Any], data: Decimal) -> str:
    return str(data)


@register
def _unstructure_default(ctx: CtxImpl[bytes, Any, Any, Any], data: bytes, *, keymap: dict[str, str] | None) -> Exe:
    return bytes_exe


def bytes_exe(ctx: CtxImpl[bytes, Any, Any, Any], data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


@register
def _unstructure_default(ctx: CtxImpl[date, Any, Any, Any], data: date, *, keymap: dict[str, str] | None) -> Exe:
    return date_exe


def date_exe(ctx: CtxImpl[date, Any, Any, Any], data: date) -> str:
    return data.isoformat()


@register
def _unstructure_default(
    ctx: CtxImpl[datetime, Any, Any, Any], data: datetime, *, keymap: dict[str, str] | None
) -> Exe:
    return datetime_exe


def datetime_exe(ctx: CtxImpl[datetime, Any, Any, Any], data: datetime) -> str:
    return data.isoformat()


_primitive_types = int | float | bool | str | None


@register
def _unstructure_default(
    ctx: CtxImpl[Any, Any, Any, Any], data: _primitive_types, *, keymap: dict[str, str] | None
) -> Exe:
    return any_primitive_exe


def any_primitive_exe(ctx: CtxImpl[Any, Any, Any, Any], data: _primitive_types) -> _primitive_types:
    if ctx.structured_type is Any:
        return data
    raise NoUnstructureHook(ctx, data)


@register
def _unstructure_default(
    ctx: CtxImpl[Any, Any, Any, Any], data: Path | UUID | Decimal, *, keymap: dict[str, str] | None
) -> Exe:
    return any_str_convertible_exe


def any_str_convertible_exe(ctx: CtxImpl[Any, Any, Any, Any], data: Path | UUID | Decimal) -> str:
    if ctx.structured_type is Any:
        return str(data)
    raise NoUnstructureHook(ctx, data)


@register
def _unstructure_default(ctx: CtxImpl[Any, Any, Any, Any], data: bytes, *, keymap: dict[str, str] | None) -> Exe:
    return any_bytes_exe


def any_bytes_exe(ctx: CtxImpl[Any, Any, Any, Any], data: bytes) -> str:
    if ctx.structured_type is Any:
        return base64.b64encode(data).decode("ascii")
    raise NoUnstructureHook(ctx, data)


@register
def _unstructure_default(
    ctx: CtxImpl[Any, Any, Any, Any], data: date | datetime, *, keymap: dict[str, str] | None
) -> Exe:
    return any_date_exe


def any_date_exe(ctx: CtxImpl[Any, Any, Any, Any], data: date | datetime) -> str:
    if ctx.structured_type is Any:
        return data.isoformat()
    raise NoUnstructureHook(ctx, data)


@register
def _unstructure_default(ctx: CtxImpl[list, Any, Any, Any], data: list, *, keymap: dict[str, str] | None) -> Exe:
    return ListExe(ctx)


@register
def _unstructure_default(
    ctx: CtxImpl[Sequence, Any, Any, Any], data: Sequence, *, keymap: dict[str, str] | None
) -> Exe:
    return SequenceExe(ctx)


@register
def _unstructure_default(ctx: CtxImpl[Any, Any, Any, Any], data: list, *, keymap: dict[str, str] | None) -> Exe:
    return AnyListExe(ctx)


class ListExe:
    __slots__ = ("children", "item_type")

    children: list[Site]
    item_type: Any

    def __init__(self, ctx: CtxImpl):
        self.children = []
        self.item_type = get_type_param(ctx, 0)

    def __call__(self, ctx: CtxImpl, data: list) -> list:
        if len(self.children) < len(data):
            self.children.extend(
                [
                    _unstructure_site(
                        CtxImpl.create(
                            ctx,
                            self.item_type,
                            itemref_path(ctx.structured_path, i),
                            itemref_path(ctx.unstructured_path, i),
                            i,
                        )
                    )
                    for i in range(len(self.children), len(data))
                ]
            )
        return [
            site.exe(site.ctx, e) if (site.is_bypass_safe and type(e) is site.data_type) else site(e)
            for site, e in zip(self.children, data)
        ]


class SequenceExe:
    __slots__ = ("children", "item_type")

    children: list[Site]
    item_type: Any

    def __init__(self, ctx: CtxImpl):
        self.children = []
        self.item_type = get_type_param(ctx, 0)

    def __call__(self, ctx: CtxImpl, data: Sequence) -> list:
        if isinstance(data, str):
            raise NoUnstructureHook(ctx, data)
        if len(self.children) < len(data):
            self.children.extend(
                [
                    _unstructure_site(
                        CtxImpl.create(
                            ctx,
                            self.item_type,
                            itemref_path(ctx.structured_path, i),
                            itemref_path(ctx.unstructured_path, i),
                            i,
                        )
                    )
                    for i in range(len(self.children), len(data))
                ]
            )
        return [
            site.exe(site.ctx, e) if (site.is_bypass_safe and type(e) is site.data_type) else site(e)
            for site, e in zip(self.children, data)
        ]


class AnyListExe:
    __slots__ = ("children",)

    children: list[Site]

    def __init__(self, ctx: CtxImpl):
        self.children = []

    def __call__(self, ctx: CtxImpl, data: list) -> list:
        if ctx.structured_type is not Any:
            raise NoUnstructureHook(ctx, data)
        if len(self.children) < len(data):
            self.children.extend(
                [
                    _unstructure_site(
                        CtxImpl.create(
                            ctx,
                            Any,
                            itemref_path(ctx.structured_path, i),
                            itemref_path(ctx.unstructured_path, i),
                            i,
                        )
                    )
                    for i in range(len(self.children), len(data))
                ]
            )
        return [
            site.exe(site.ctx, e) if (site.is_bypass_safe and type(e) is site.data_type) else site(e)
            for site, e in zip(self.children, data)
        ]


@register
def _unstructure_default(ctx: CtxImpl[tuple, Any, Any, Any], data: tuple, *, keymap: dict[str, str] | None) -> Exe:
    type_params = get_args(ctx.structured_type)
    if get_origin(ctx.structured_type) is tuple and not type_params:
        return InhomogeneousTupleExe(ctx, ())
    if not type_params:
        return HomogeneousTupleExe(ctx, Any)
    if len(type_params) > 1 and type_params[1] == Ellipsis:
        return HomogeneousTupleExe(ctx, type_params[0])
    else:
        return InhomogeneousTupleExe(ctx, type_params)


@register
def _unstructure_default(ctx: CtxImpl[Any, Any, Any, Any], data: tuple, *, keymap: dict[str, str] | None) -> Exe:
    return AnyTupleExe(ctx)


class HomogeneousTupleExe:
    __slots__ = ("children", "item_type")

    children: list[Site]
    item_type: Any

    def __init__(self, ctx: CtxImpl, item_type: Any):
        self.children = []
        self.item_type = item_type

    def __call__(self, ctx: CtxImpl, data: tuple) -> list:
        if len(self.children) < len(data):
            self.children.extend(
                [
                    _unstructure_site(
                        CtxImpl.create(
                            ctx,
                            self.item_type,
                            itemref_path(ctx.structured_path, i),
                            itemref_path(ctx.unstructured_path, i),
                            i,
                        )
                    )
                    for i in range(len(self.children), len(data))
                ]
            )
        return [
            site.exe(site.ctx, e) if (site.is_bypass_safe and type(e) is site.data_type) else site(e)
            for site, e in zip(self.children, data)
        ]


class InhomogeneousTupleExe:
    __slots__ = ("children",)

    children: list[Site]

    def __init__(self, ctx: CtxImpl, type_params: tuple):
        self.children = [
            _unstructure_site(
                CtxImpl.create(
                    ctx,
                    t,
                    itemref_path(ctx.structured_path, i),
                    itemref_path(ctx.unstructured_path, i),
                    i,
                )
            )
            for i, t in enumerate(type_params)
        ]

    def __call__(self, ctx: CtxImpl, data: tuple) -> list:
        if len(data) != len(self.children):
            raise NoUnstructureHook(ctx, data)
        return [
            site.exe(site.ctx, e) if (site.is_bypass_safe and type(e) is site.data_type) else site(e)
            for site, e in zip(self.children, data)
        ]


class AnyTupleExe:
    __slots__ = ("children",)

    children: list[Site]

    def __init__(self, ctx: CtxImpl):
        self.children = []

    def __call__(self, ctx: CtxImpl, data: tuple) -> list:
        if ctx.structured_type is not Any:
            raise NoUnstructureHook(ctx, data)
        if len(self.children) < len(data):
            self.children.extend(
                [
                    _unstructure_site(
                        CtxImpl.create(
                            ctx,
                            Any,
                            itemref_path(ctx.structured_path, i),
                            itemref_path(ctx.unstructured_path, i),
                            i,
                        )
                    )
                    for i in range(len(self.children), len(data))
                ]
            )
        return [
            site.exe(site.ctx, e) if (site.is_bypass_safe and type(e) is site.data_type) else site(e)
            for site, e in zip(self.children, data)
        ]


@register
def _unstructure_default(ctx: CtxImpl[set, Any, Any, Any], data: set, *, keymap: dict[str, str] | None) -> Exe:
    return SetExe(ctx)


@register
def _unstructure_default(ctx: CtxImpl[Any, Any, Any, Any], data: set, *, keymap: dict[str, str] | None) -> Exe:
    return AnySetExe(ctx)


class SetExe:
    __slots__ = ("children", "item_type")

    children: list[Site]
    item_type: Any

    def __init__(self, ctx: CtxImpl):
        self.children = []
        self.item_type = get_type_param(ctx, 0)

    def __call__(self, ctx: CtxImpl, data: set) -> list:
        items = list(data)
        if len(self.children) < len(items):
            self.children.extend(
                [
                    _unstructure_site(
                        CtxImpl.create(
                            ctx,
                            self.item_type,
                            itemref_path(ctx.structured_path, None),
                            itemref_path(ctx.unstructured_path, i),
                            None,
                        )
                    )
                    for i in range(len(self.children), len(items))
                ]
            )
        return [
            site.exe(site.ctx, e) if (site.is_bypass_safe and type(e) is site.data_type) else site(e)
            for site, e in zip(self.children, items)
        ]


class AnySetExe:
    __slots__ = ("children",)

    children: list[Site]

    def __init__(self, ctx: CtxImpl):
        self.children = []

    def __call__(self, ctx: CtxImpl, data: set) -> list:
        if ctx.structured_type is not Any:
            raise NoUnstructureHook(ctx, data)
        items = list(data)
        if len(self.children) < len(items):
            self.children.extend(
                [
                    _unstructure_site(
                        CtxImpl.create(
                            ctx,
                            Any,
                            itemref_path(ctx.structured_path, None),
                            itemref_path(ctx.unstructured_path, i),
                            None,
                        )
                    )
                    for i in range(len(self.children), len(items))
                ]
            )
        return [
            site.exe(site.ctx, e) if (site.is_bypass_safe and type(e) is site.data_type) else site(e)
            for site, e in zip(self.children, items)
        ]


@register
def _unstructure_default(
    ctx: CtxImpl[frozenset, Any, Any, Any], data: frozenset, *, keymap: dict[str, str] | None
) -> Exe:
    return FrozenSetExe(ctx)


@register
def _unstructure_default(ctx: CtxImpl[Any, Any, Any, Any], data: frozenset, *, keymap: dict[str, str] | None) -> Exe:
    return AnyFrozenSetExe(ctx)


class FrozenSetExe:
    __slots__ = ("children", "item_type")

    children: list[Site]
    item_type: Any

    def __init__(self, ctx: CtxImpl):
        self.children = []
        self.item_type = get_type_param(ctx, 0)

    def __call__(self, ctx: CtxImpl, data: frozenset) -> list:
        items = list(data)
        if len(self.children) < len(items):
            self.children.extend(
                [
                    _unstructure_site(
                        CtxImpl.create(
                            ctx,
                            self.item_type,
                            itemref_path(ctx.structured_path, None),
                            itemref_path(ctx.unstructured_path, i),
                            None,
                        )
                    )
                    for i in range(len(self.children), len(items))
                ]
            )
        return [
            site.exe(site.ctx, e) if (site.is_bypass_safe and type(e) is site.data_type) else site(e)
            for site, e in zip(self.children, items)
        ]


class AnyFrozenSetExe:
    __slots__ = ("children",)

    children: list[Site]

    def __init__(self, ctx: CtxImpl):
        self.children = []

    def __call__(self, ctx: CtxImpl, data: frozenset) -> list:
        if ctx.structured_type is not Any:
            raise NoUnstructureHook(ctx, data)
        items = list(data)
        if len(self.children) < len(items):
            self.children.extend(
                [
                    _unstructure_site(
                        CtxImpl.create(
                            ctx,
                            Any,
                            itemref_path(ctx.structured_path, None),
                            itemref_path(ctx.unstructured_path, i),
                            None,
                        )
                    )
                    for i in range(len(self.children), len(items))
                ]
            )
        return [
            site.exe(site.ctx, e) if (site.is_bypass_safe and type(e) is site.data_type) else site(e)
            for site, e in zip(self.children, items)
        ]


@register
def _unstructure_default(ctx: CtxImpl[dict, Any, Any, Any], data: dict, *, keymap: dict[str, str] | None) -> Exe:
    return DictExe(ctx)


@register
def _unstructure_default(ctx: CtxImpl[Any, Any, Any, Any], data: dict, *, keymap: dict[str, str] | None) -> Exe:
    return AnyDictExe(ctx)


_DICT_CHILDREN_LIMIT = 1024


class DictExe:
    __slots__ = ("key_children", "val_children", "key_type", "value_type")

    key_children: dict[tuple[type, Any], Site]
    val_children: dict[tuple[tuple[type, Any], tuple[type, str]], Site]
    key_type: Any
    value_type: Any

    def __init__(self, ctx: CtxImpl):
        self.key_children = {}
        self.val_children = {}
        self.key_type = get_type_param(ctx, 0)
        self.value_type = get_type_param(ctx, 1)

    def __call__(self, ctx: CtxImpl, data: dict) -> dict[str, Any]:
        result = {}
        for k, v in data.items():
            key_cache_key = (type(k), k)
            key_site = self.key_children.get(key_cache_key)
            if key_site is None:
                key_site = _unstructure_key_site(self.key_type, k, ctx)
                if len(self.key_children) >= _DICT_CHILDREN_LIMIT:
                    self.key_children.clear()  # pragma: no cover
                self.key_children[key_cache_key] = key_site
            unstructured_key = key_site(k)
            if type(unstructured_key) is not str:
                raise ValidationError(
                    key_site.ctx,
                    k,
                    f"Dict key must unstructure to str, got {type(unstructured_key).__name__}: {repr(unstructured_key)}",
                )
            val_cache_key = (key_cache_key, (type(unstructured_key), unstructured_key))
            val_site = self.val_children.get(val_cache_key)
            if val_site is None:
                val_site = _unstructure_val_site(self.key_type, self.value_type, k, unstructured_key, ctx)
                if len(self.val_children) >= _DICT_CHILDREN_LIMIT:
                    self.val_children.clear()  # pragma: no cover
                self.val_children[val_cache_key] = val_site
            result[unstructured_key] = val_site(v)
        return result


class AnyDictExe:
    __slots__ = ("key_children", "val_children")

    key_children: dict[tuple[type, Any], Site]
    val_children: dict[tuple[tuple[type, Any], tuple[type, str]], Site]

    def __init__(self, ctx: CtxImpl):
        self.key_children = {}
        self.val_children = {}

    def __call__(self, ctx: CtxImpl, data: dict) -> dict[str, Any]:
        if ctx.structured_type is not Any:
            raise NoUnstructureHook(ctx, data)
        result = {}
        for k, v in data.items():
            key_cache_key = (type(k), k)
            key_site = self.key_children.get(key_cache_key)
            if key_site is None:
                key_site = _unstructure_key_site(Any, k, ctx)
                if len(self.key_children) >= _DICT_CHILDREN_LIMIT:
                    self.key_children.clear()  # pragma: no cover
                self.key_children[key_cache_key] = key_site
            unstructured_key = key_site(k)
            if type(unstructured_key) is not str:
                raise ValidationError(
                    key_site.ctx,
                    k,
                    f"Dict key must unstructure to str, got {type(unstructured_key).__name__}: {repr(unstructured_key)}",
                )
            val_cache_key = (key_cache_key, (type(unstructured_key), unstructured_key))
            val_site = self.val_children.get(val_cache_key)
            if val_site is None:
                val_site = _unstructure_val_site(Any, Any, k, unstructured_key, ctx)
                if len(self.val_children) >= _DICT_CHILDREN_LIMIT:
                    self.val_children.clear()  # pragma: no cover
                self.val_children[val_cache_key] = val_site
            result[unstructured_key] = val_site(v)
        return result


def _unstructure_key_site(key_type: Any, structured_key: Any, ctx: CtxImpl) -> Site:
    subctx = CtxImpl.create(
        ctx,
        key_type,
        f"{ctx.structured_path}[~{key_repr(key_type, structured_key)}]",
        f"{ctx.unstructured_path}[~?]",
        structured_key,
    )
    return _unstructure_site(subctx)


def _unstructure_val_site(
    key_type: Any, value_type: Any, structured_key: Any, unstructured_key: Any, ctx: CtxImpl
) -> Site:
    subctx = CtxImpl.create(
        ctx,
        value_type,
        f"{ctx.structured_path}[{key_repr(key_type, structured_key)}]",
        itemref_path(ctx.unstructured_path, unstructured_key),
        structured_key,
    )
    return _unstructure_site(subctx)


@register
def _unstructure_default(
    ctx: CtxImpl[int, Any, Any, tuple[Any, KeySeg[Any]]], data: int | str, *, keymap: dict[str, str] | None
) -> Exe:
    return int_key_exe


def int_key_exe(ctx: CtxImpl[int, Any, Any, Any], data: int) -> str:
    return str(data)


@register.ctx_subtypes
def _unstructure_default(
    ctx: CtxImpl[DataClassBase, Any, Any, Any], data: DataClassBase, *, keymap: dict[str, str] | None
) -> Exe:
    return DataClassExe(ctx, keymap)


@register
def _unstructure_default(
    ctx: CtxImpl[Any, Any, Any, Any], data: DataClassBase, *, keymap: dict[str, str] | None
) -> Exe:
    return AnyDataClassExe(ctx)


class DataClassExe:
    __slots__ = ("children", "dataclass_type")

    children: list[tuple[str, str, Site]]  # field_name, alias, site
    dataclass_type: Any

    def __init__(self, ctx: CtxImpl, keymap: dict[str, str] | None):
        self.dataclass_type = ctx.structured_type
        field_types = resolve_field_types(ctx.structured_type)
        self.children = [
            (
                f.name,
                alias := keymap[f.name] if keymap and f.name in keymap else f.name,
                _unstructure_site(
                    CtxImpl.create(
                        ctx,
                        t,
                        f"{ctx.structured_path}.{f.name}",
                        itemref_path(ctx.unstructured_path, alias),
                        f,
                    )
                ),
            )
            for f, t in field_types
        ]

    def __call__(self, ctx: CtxImpl, data: Any) -> dict[str, Any]:
        return {
            alias: (site.exe(site.ctx, v) if (site.is_bypass_safe and type(v) is site.data_type) else site(v))
            for name, alias, site in self.children
            for v in (getattr(data, name),)
        }


class AnyDataClassExe:
    __slots__ = ("children_cache",)

    children_cache: dict[type, list[tuple[str, Site]]]

    def __init__(self, ctx: CtxImpl):
        self.children_cache = {}

    def __call__(self, ctx: CtxImpl, data: Any) -> dict[str, Any]:
        if ctx.structured_type is not Any:
            raise NoUnstructureHook(ctx, data)
        if orig_cls := getattr(data, "__orig_class__", None):
            dataclass_type = orig_cls
        else:
            dataclass_type = type(data)
        children = self.children_cache.get(dataclass_type)
        if children is None:
            actual_ctx = ctx._replace_type(dataclass_type)
            field_types = [(f, Any) for f in fields(data)]
            children = [
                (
                    f.name,
                    _unstructure_site(
                        CtxImpl.create(
                            actual_ctx,
                            t,
                            f"{actual_ctx.structured_path}.{f.name}",
                            itemref_path(actual_ctx.unstructured_path, f.name),
                            f,
                        )
                    ),
                )
                for f, t in field_types
            ]
            self.children_cache[dataclass_type] = children
        return {name: site(getattr(data, name)) for name, site in children}


@register.ctx_subtypes
def _unstructure_default(
    ctx: CtxImpl[TypedDictBase, Any, Any, Any], data: dict, *, keymap: dict[str, str] | None
) -> Exe:
    return TypedDictExe(ctx, keymap)


class TypedDictExe:
    __slots__ = (
        "children",
        "typeddict_type",
        "declared_keys",
        "output_keys",
        "closed",
        "extra_items_type",
        "extra_children",
    )

    children: list[tuple[str, str, Site]]  # field_name, alias, site
    typeddict_type: Any
    declared_keys: frozenset[str]
    output_keys: frozenset[str]
    closed: bool
    extra_items_type: Any
    extra_children: dict[str, Site]

    def __init__(self, ctx: CtxImpl, keymap: dict[str, str] | None):
        self.typeddict_type = ctx.structured_type
        field_types = resolve_typeddict_field_types(ctx.structured_type)
        self.children = [
            (
                name,
                alias := keymap[name] if keymap and name in keymap else name,
                _unstructure_site(
                    CtxImpl.create(
                        ctx,
                        t,
                        f"{ctx.structured_path}.{format_field(name)}",
                        itemref_path(ctx.unstructured_path, alias),
                        name,
                    )
                ),
            )
            for name, t in field_types
        ]
        self.declared_keys = frozenset(name for name, _ in field_types)
        self.output_keys = frozenset(alias for _, alias, _ in self.children)
        self.closed, self.extra_items_type = get_typeddict_extras_policy(ctx.structured_type)
        self.extra_children = {}

    def __call__(self, ctx: CtxImpl, data: dict) -> dict:
        out = {
            alias: (site.exe(site.ctx, v) if (site.is_bypass_safe and type(v) is site.data_type) else site(v))
            for name, alias, site in self.children
            if name in data
            for v in (data[name],)
        }
        if not self.closed and self.extra_items_type is not None:
            for k in data.keys() - self.declared_keys:
                if type(k) is not str:
                    raise ValidationError(
                        ctx, data, f"TypedDict extra key must be str, got {type(k).__name__}: {repr(k)}"
                    )
                if k in self.output_keys:
                    raise ValidationError(ctx, data, f"TypedDict extra key conflicts with declared field: {repr(k)}")
                site = self.extra_children.get(k)
                if site is None:
                    site = _unstructure_site(
                        CtxImpl.create(
                            ctx,
                            self.extra_items_type,
                            typeddict_key_path(ctx.structured_path, k),
                            itemref_path(ctx.unstructured_path, k),
                            k,
                        )
                    )
                    self.extra_children[k] = site
                out[k] = site(data[k])
        return out


LiteralValueType = int | float | bool | str | bytes | Enum | NoneType


@register.ctx_subtypes
def _unstructure_default(
    ctx: CtxImpl[LiteralBase, Any, Any, Any], data: LiteralValueType, *, keymap: dict[str, str] | None
) -> Exe:
    if isinstance(data, bool):
        return bool_exe
    if isinstance(data, int):
        return int_exe
    if isinstance(data, float):
        return float_exe
    if isinstance(data, str):
        return str_exe
    if isinstance(data, Enum):
        return enum_exe
    if isinstance(data, bytes):
        return bytes_exe
    if data is None:
        return none_exe
    raise AssertionError("Bug: unreachable")  # pragma: no cover


@register.ctx_subtypes
def _unstructure_default(
    ctx: CtxImpl[LiteralBase, Any, Any, tuple[Any, KeySeg[Any]]],
    data: LiteralValueType,
    *,
    keymap: dict[str, str] | None,
) -> Exe:
    return literal_key_exe


def literal_key_exe(ctx: CtxImpl[LiteralBase, Any, Any, Any], data: LiteralValueType) -> Any:
    if literal_values_contain(get_args(ctx.structured_type), data):
        if isinstance(data, bool):
            return data
        if isinstance(data, int):
            return str(data)
        if isinstance(data, Enum):
            return str(data.value)
    if isinstance(data, bool):
        return data
    if isinstance(data, int):
        return int(data)
    if isinstance(data, float):
        return float(data)
    if isinstance(data, str):
        return data
    if isinstance(data, Enum):
        return data.value
    if isinstance(data, bytes):
        return base64.b64encode(data).decode("ascii")
    if data is None:
        return None
    raise AssertionError("Bug: unreachable")  # pragma: no cover


@register.ctx_subtypes
def _unstructure_default(ctx: CtxImpl[NewTypeBase, Any, Any, Any], data: Any, *, keymap: dict[str, str] | None) -> Exe:
    supertype = ctx.structured_type.__supertype__
    try:
        return _unstructure_default(ctx._replace_type(supertype), data, keymap=None)
    except NoMatchFound as e:
        raise NoUnstructureHook(ctx, data) from e


@register.ctx_subtypes
def _unstructure_default(ctx: CtxImpl[UnionBase, Any, Any, Any], data: Any, *, keymap: dict[str, str] | None) -> Exe:
    if keymap is not None:
        raise ValidationError(ctx, data, "keymap is not supported for union default conversion")
    dispatch = config._dispatcher.get().dispatch
    hook = dispatch.get("unstructure_hook")
    hook_dtype = hook.arg_type(1, data) if hook else Never
    default = dispatch["_unstructure_default"]
    default_dtype = default.arg_type(1, data)
    probed = probe_union_candidates(
        hook,
        default,
        get_args(ctx.structured_type),
        ctx,
        data,
        validate_literal_membership_for_hooks=True,
    )
    if probed is None:
        raise AmbiguousUnion(ctx, data, "A union member causes ambiguous dispatch with the data")
    probed_members = [c for c, _ in probed]
    if all(is_typeddict(get_origin(c) or c) for c in probed_members) and len(probed_members) > 1:
        discriminator = generate_decision_func(probed_members)
        if discriminator is not None:
            return TypedDictUnionExe(discriminator)
        else:
            raise AmbiguousUnion(ctx, data, "Union members cannot be discriminated by their fields or a Literal tag")
    probed = [
        (p, is_hook)
        for p, is_hook in probed
        if not is_dataclass(get_origin(p) or p) or is_subtype_covariant(hook_dtype if is_hook else default_dtype, p)  # type: ignore
    ]
    probed = select_union_candidate(probed, default_dtype)
    match len(probed):
        case 0:
            raise NoUnstructureHook(ctx, data)
        case 1:
            return UnionMemberExe(ctx, probed[0])
        case _:
            raise AmbiguousUnion(ctx, data, f"Multiple members of the union are compatible with the data: {probed}")


class UnionMemberExe:
    __slots__ = ("child",)

    def __init__(self, ctx: CtxImpl, concrete_type: Any):
        newctx = ctx._replace_type(concrete_type)
        self.child = _unstructure_site(newctx)

    def __call__(self, ctx: CtxImpl, data: Any) -> Any:
        return self.child(data)


class TypedDictUnionExe:
    __slots__ = ("discriminator", "children")

    discriminator: Any
    children: dict[Any, tuple[CtxImpl, Site]]

    def __init__(self, discriminator):
        self.discriminator = discriminator
        self.children = {}

    def __call__(self, ctx: CtxImpl, data: Any) -> Any:
        dcls = self.discriminator(data)
        if dcls is None:
            raise NoUnstructureHook(ctx, data, "The data is not compatible with any member of the union")
        newctx, site = self.children.get(dcls, (None, None))
        if newctx is None or site is None:
            newctx = ctx._replace_type(dcls)
            site = _unstructure_site(newctx)
            self.children[dcls] = (newctx, site)
        return site(data)
