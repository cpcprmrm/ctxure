import base64
import binascii
import typing
from abc import ABC, abstractmethod
from collections.abc import Callable, Collection, Hashable, Sequence
from dataclasses import MISSING, is_dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from enum import Enum
from pathlib import Path
from types import NoneType
from typing import Any, Literal, cast, get_args, get_origin
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
    normalize_type,
    normalized_origin_args,
    resolve_input_field_types,
    resolve_typeddict_field_types,
)
from ctxure._unionutil import generate_decision_func, probe_union_candidates, select_union_candidate
from ctxure._util import get_type_param, itemref_path, key_repr, typeddict_key_path
from ctxure.context import CtxImpl
from ctxure.error import (
    AmbiguousUnion,
    ExtraFields,
    MissingFields,
    MultipleStructureHooks,
    NoStructureHook,
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
)

register = config.register


class StructureSite(Site):
    _mm_arg_type: Callable[[int, Any], Any]
    _literal_targets: dict[tuple[type, Any], Any]

    def __init__(self, ctx: CtxImpl):
        super().__init__(ctx)
        dispatch = config._dispatcher.get().dispatch
        hook = dispatch.get("structure_hook")
        default = dispatch["_structure_default"]
        self._mm_arg_type = (hook or default).arg_type  # type: ignore
        self._literal_targets = _collect_target_literals(ctx.structured_type)
        self.is_literal_free = not self._literal_targets
        self.is_bypass_safe = (not hook or not hook.partial_dispatch(ctx.__orig_class__)) and self.is_literal_free
        if not self.is_bypass_safe and ctx.parent is not None:
            mark_not_bypass_safe(ctx.parent._site)  # type: ignore

    def dispatch(self, ctx: CtxImpl, data: Any) -> Exe:
        try:
            return _structure_exe(ctx, data)
        except NoMatchFound:
            raise NoStructureHook(ctx, data)

    def dtype(self, data: Any) -> Any:
        if self._literal_targets and isinstance(data, Hashable):
            if promoted := self._literal_targets.get((type(data), data)):
                return promoted
        return self._mm_arg_type(1, data)


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


def structure(target_type, data: Any, extra: Any = None) -> Any:
    dispatcher = config._dispatcher.get()
    if dispatcher.active_structure:
        raise ReentranceError()
    try:
        dispatcher.active_structure = True
        cache = dispatcher.structure_cache
        if (site := cache.get(target_type, None)) is None:
            root_ctx = CtxImpl.create(None, target_type, "$", "$", None)
            site = StructureSite(root_ctx)
            cache[target_type] = site
        site.extra = extra
        return site(data)
    finally:
        dispatcher.active_structure = False


_MAX_KEYMAP_CACHE_ENTRY = 16


@typing.no_type_check
def structure_default(ctx: CtxImpl, data: Any, keymap: dict[str, str] | None = None) -> Any:
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
        exe = config._dispatcher.get().dispatch["_structure_default"](ctx, data, keymap=keymap)
        if len(cache) >= _MAX_KEYMAP_CACHE_ENTRY:
            cache.clear()
        cache[cache_key] = (exe, keymap)
    else:
        exe = cached[0]
    exe_holder.default_exe = exe
    exe_holder.default_dtype = dtype
    exe_holder.keymap = keymap
    return exe(ctx, data)


def structure_by_type(ctx: CtxImpl, data: Any) -> Any:
    exe_holder = cast(HookExe, ctx._site.exe)  # type: ignore
    site = exe_holder.by_type_site
    if site is None:
        site = StructureSite(ctx._strip())
        exe_holder.by_type_site = site
    return site(data)


def _structure_site(ctx: Any) -> Site:
    return StructureSite(ctx)


def _structure_exe(ctx: Any, data: Any) -> Exe:
    dispatch = config._dispatcher.get().dispatch
    methods = []
    if hook := dispatch.get("structure_hook", None):
        methods = hook.dispatch(ctx.__orig_class__, hook.arg_type(1, data))
    match len(methods):
        case 0:
            _structure_default = dispatch["_structure_default"]
            return _structure_default(ctx, data, keymap=None)
        case 1:
            return HookExe(methods[0])
        case _:
            raise MultipleStructureHooks(ctx, data, methods)


@register
def _structure_default(ctx: CtxImpl[Any, Any, Any, Any], data: Any, *, keymap: dict[str, str] | None) -> Exe:
    if ctx.structured_type is Any:
        return any_exe
    raise NoStructureHook(ctx, data)


def any_exe(ctx: CtxImpl[Any, Any, Any, Any], data: Any) -> Any:
    return data


@register
def _structure_default(ctx: CtxImpl[NoneType, Any, Any, Any], data: NoneType, *, keymap: dict[str, str] | None) -> Exe:
    return none_exe


def none_exe(ctx: CtxImpl[NoneType, Any, Any, Any], data: None) -> None:
    return None


@register
def _structure_default(ctx: CtxImpl[int, Any, Any, Any], data: int, *, keymap: dict[str, str] | None) -> Exe:
    return int_exe


def int_exe(ctx: CtxImpl[int, Any, Any, Any], data: int) -> int:
    return int(data)


@register
def _structure_default(ctx: CtxImpl[bool, Any, Any, Any], data: int, *, keymap: dict[str, str] | None) -> Exe:
    return bool_exe


def bool_exe(ctx: CtxImpl[bool, Any, Any, Any], data: int) -> bool:
    return data != 0


@register
def _structure_default(ctx: CtxImpl[float, Any, Any, Any], data: float, *, keymap: dict[str, str] | None) -> Exe:
    return float_exe


def float_exe(ctx: CtxImpl[float, Any, Any, Any], data: float) -> float:
    return float(data)


@register
def _structure_default(ctx: CtxImpl[str, Any, Any, Any], data: str, *, keymap: dict[str, str] | None) -> Exe:
    return str_exe


def str_exe(ctx: CtxImpl[str, Any, Any, Any], data: str) -> str:
    return data


@register.ctx_subtypes
def _structure_default(ctx: CtxImpl[Enum, Any, Any, Any], data: Any, *, keymap: dict[str, str] | None) -> Exe:
    return enum_exe


def enum_exe(ctx: CtxImpl[Enum, Any, Any, Any], data: Any) -> Enum:
    try:
        return ctx.structured_type(data)
    except ValueError:
        raise ValidationError(ctx, data, f"{repr(data)} is not a valid value of {ctx.structured_type}")


@register
def _structure_default(ctx: CtxImpl[Path, Any, Any, Any], data: str, *, keymap: dict[str, str] | None) -> Exe:
    return path_exe


def path_exe(ctx: CtxImpl[Path, Any, Any, Any], data: str) -> Path:
    return Path(data)


@register
def _structure_default(ctx: CtxImpl[UUID, Any, Any, Any], data: str, *, keymap: dict[str, str] | None) -> Exe:
    return uuid_exe


def uuid_exe(ctx: CtxImpl[UUID, Any, Any, Any], data: str) -> UUID:
    try:
        return UUID(data)
    except ValueError:
        raise ValidationError(ctx, data, f"Cannot parse {repr(data)} as {ctx.structured_type}")


@register
def _structure_default(ctx: CtxImpl[Decimal, Any, Any, Any], data: str, *, keymap: dict[str, str] | None) -> Exe:
    return decimal_exe


def decimal_exe(ctx: CtxImpl[Decimal, Any, Any, Any], data: str) -> Decimal:
    try:
        return Decimal(data)
    except InvalidOperation:
        raise ValidationError(ctx, data, f"Cannot parse {repr(data)} as {ctx.structured_type}")


@register
def _structure_default(ctx: CtxImpl[bytes, Any, Any, Any], data: str, *, keymap: dict[str, str] | None) -> Exe:
    return bytes_exe


def bytes_exe(ctx: CtxImpl[bytes, Any, Any, Any], data: str) -> bytes:
    try:
        return base64.b64decode(data, validate=True)
    except binascii.Error:
        raise ValidationError(ctx, data, f"Cannot decode {repr(data)} as base64")


@register
def _structure_default(ctx: CtxImpl[date, Any, Any, Any], data: str, *, keymap: dict[str, str] | None) -> Exe:
    return date_exe


def date_exe(ctx: CtxImpl[date, Any, Any, Any], data: str) -> date:
    try:
        return date.fromisoformat(data)
    except ValueError:
        raise ValidationError(ctx, data, f"Cannot parse {repr(data)} as {ctx.structured_type}")


@register
def _structure_default(ctx: CtxImpl[datetime, Any, Any, Any], data: str, *, keymap: dict[str, str] | None) -> Exe:
    return datetime_exe


def datetime_exe(ctx: CtxImpl[datetime, Any, Any, Any], data: str) -> datetime:
    try:
        return datetime.fromisoformat(data)
    except ValueError:
        raise ValidationError(ctx, data, f"Cannot parse {repr(data)} as {ctx.structured_type}")


class SingleParamCollectionExe(ABC):
    __slots__ = ("children", "item_type", "is_target_indexed", "is_source_indexed")

    children: list[Site]
    item_type: Any
    is_target_indexed: bool
    is_source_indexed: bool

    def __init__(self, ctx: CtxImpl, is_data_indexed: bool):
        self.children = []
        self.item_type = get_type_param(ctx, 0)
        target_orig = get_origin(ctx.structured_type) or ctx.structured_type
        self.is_target_indexed = issubclass(target_orig, Sequence)
        self.is_source_indexed = is_data_indexed

    def __call__(self, ctx: CtxImpl, data: Collection) -> Any:
        if len(self.children) < len(data):
            self.children.extend(
                [
                    _structure_site(
                        CtxImpl.create(
                            ctx,
                            self.item_type,
                            itemref_path(ctx.structured_path, i, self.is_target_indexed),
                            itemref_path(ctx.unstructured_path, i, self.is_source_indexed),
                            i if self.is_target_indexed else None,
                        )
                    )
                    for i in range(len(self.children), len(data))
                ]
            )
        return self.build(data)

    @abstractmethod
    def build(self, data: Any) -> Any:  # pragma: no cover
        pass


UnaryTypeCollection = list | tuple | set | frozenset


@register
def _structure_default(
    ctx: CtxImpl[list, Any, Any, Any], data: UnaryTypeCollection, *, keymap: dict[str, str] | None
) -> Exe:
    return _structure_default_list(ctx, data)


@register
def _structure_default(
    ctx: CtxImpl[Sequence, Any, Any, Any], data: UnaryTypeCollection, *, keymap: dict[str, str] | None
) -> Exe:
    return _structure_default_list(ctx, data)


@register
def _structure_default(
    ctx: CtxImpl[Collection, Any, Any, Any], data: UnaryTypeCollection, *, keymap: dict[str, str] | None
) -> Exe:
    return _structure_default_list(ctx, data)


def _structure_default_list(ctx: CtxImpl, data: UnaryTypeCollection) -> Exe:
    return ListExe(ctx, isinstance(data, Sequence))


class ListExe(SingleParamCollectionExe):
    def build(self, data: Collection) -> list:
        return [
            site.exe(site.ctx, e) if (site.is_bypass_safe and type(e) is site.data_type) else site(e)
            for site, e in zip(self.children, data)
        ]


@register
def _structure_default(
    ctx: CtxImpl[tuple, Any, Any, Any], data: UnaryTypeCollection, *, keymap: dict[str, str] | None
) -> Exe:
    type_params = get_args(ctx.structured_type)
    if get_origin(ctx.structured_type) is tuple and not type_params:
        return InhomogeneousTupleExe(ctx, isinstance(data, Sequence))
    if not type_params:
        return HomogeneousTupleExe(ctx, isinstance(data, Sequence))
    if len(type_params) > 1 and type_params[1] == Ellipsis:
        return HomogeneousTupleExe(ctx, isinstance(data, Sequence))
    else:
        return InhomogeneousTupleExe(ctx, isinstance(data, Sequence))


class HomogeneousTupleExe(SingleParamCollectionExe):
    def build(self, data: Collection) -> tuple:
        return tuple(
            site.exe(site.ctx, e) if (site.is_bypass_safe and type(e) is site.data_type) else site(e)
            for site, e in zip(self.children, data)
        )


class InhomogeneousTupleExe:
    __slots__ = ("children",)

    children: list[Site]

    def __init__(self, ctx: CtxImpl[tuple, Any, Any, Any], is_data_indexed: bool):
        elem_types = get_args(ctx.structured_type)
        self.children = [
            _structure_site(
                CtxImpl.create(
                    ctx,
                    t,
                    itemref_path(ctx.structured_path, i),
                    itemref_path(ctx.unstructured_path, i, is_data_indexed),
                    i,
                )
            )
            for i, t in enumerate(elem_types)
        ]

    def __call__(self, ctx: CtxImpl[tuple, Any, Any, Any], data: Collection) -> tuple:
        if len(data) != len(self.children):
            raise NoStructureHook(ctx, data)
        return tuple(
            site.exe(site.ctx, e) if (site.is_bypass_safe and type(e) is site.data_type) else site(e)
            for site, e in zip(self.children, data)
        )


@register
def _structure_default(
    ctx: CtxImpl[set, Any, Any, Any], data: UnaryTypeCollection, *, keymap: dict[str, str] | None
) -> Exe:
    return SetExe(ctx, isinstance(data, Sequence))


class SetExe(SingleParamCollectionExe):
    def build(self, data: Collection) -> set:
        return {
            site.exe(site.ctx, e) if (site.is_bypass_safe and type(e) is site.data_type) else site(e)
            for site, e in zip(self.children, data)
        }


@register
def _structure_default(
    ctx: CtxImpl[frozenset, Any, Any, Any], data: UnaryTypeCollection, *, keymap: dict[str, str] | None
) -> Exe:
    return FrozenSetExe(ctx, isinstance(data, Sequence))


class FrozenSetExe(SingleParamCollectionExe):
    def build(self, data: Collection) -> frozenset:
        return frozenset(
            site.exe(site.ctx, e) if (site.is_bypass_safe and type(e) is site.data_type) else site(e)
            for site, e in zip(self.children, data)
        )


@register
def _structure_default(ctx: CtxImpl[dict, Any, Any, Any], data: dict, *, keymap: dict[str, str] | None) -> Exe:
    return DictExe(ctx)


_DICT_CHILDREN_LIMIT = 1024


class DictExe:
    __slots__ = ("key_children", "val_children", "key_type", "value_type")

    key_children: dict[tuple[type, Any], Site]
    val_children: dict[tuple[tuple[type, Any], tuple[type, Any]], Site]
    key_type: Any
    value_type: Any

    def __init__(self, ctx: CtxImpl):
        self.key_children = {}
        self.val_children = {}
        self.key_type = get_type_param(ctx, 0)
        self.value_type = get_type_param(ctx, 1)

    def __call__(self, ctx: CtxImpl, data: dict) -> Any:
        result = {}
        for k, v in data.items():
            key_cache_key = (type(k), k)
            key_site = self.key_children.get(key_cache_key)
            if key_site is None:
                key_site = self._structure_key(self.key_type, k, ctx)
                if len(self.key_children) >= _DICT_CHILDREN_LIMIT:
                    self.key_children.clear()  # pragma: no cover
                self.key_children[key_cache_key] = key_site
            structured_key = key_site(k)
            val_cache_key = (key_cache_key, (type(structured_key), structured_key))
            val_site = self.val_children.get(val_cache_key)
            if val_site is None:
                val_site = self._structure_val(self.key_type, self.value_type, structured_key, k, ctx)
                if len(self.val_children) >= _DICT_CHILDREN_LIMIT:
                    self.val_children.clear()  # pragma: no cover
                self.val_children[val_cache_key] = val_site
            structured_val = val_site(v)
            result[structured_key] = structured_val
        return result

    def _structure_key(self, key_type: Any, unstructured_key: Any, ctx: CtxImpl[dict, Any, Any, Any]) -> Site:
        subctx = CtxImpl.create(
            ctx,
            key_type,
            f"{ctx.structured_path}[~?]",
            f"{ctx.unstructured_path}[~{repr(unstructured_key)}]"
            if unstructured_key is not None
            else f"{ctx.unstructured_path}[~?]",
            None,
        )
        return _structure_site(subctx)

    def _structure_val(
        self,
        key_type: Any,
        value_type: Any,
        structured_key: Any,
        unstructured_key: Any,
        ctx: CtxImpl[dict, Any, Any, Any],
    ) -> Site:
        subctx = CtxImpl.create(
            ctx,
            value_type,
            f"{ctx.structured_path}[{key_repr(key_type, structured_key)}]",
            itemref_path(ctx.unstructured_path, unstructured_key),
            structured_key,
        )
        return _structure_site(subctx)


@register
def _structure_default(
    ctx: CtxImpl[int, Any, Any, tuple[Any, KeySeg[Any]]], data: int | str, *, keymap: dict[str, str] | None
) -> Exe:
    return int_key_exe


def int_key_exe(ctx: CtxImpl[int, Any, Any, tuple[Any, KeySeg[Any]]], data: int | str) -> int:
    try:
        return int(data)
    except ValueError:
        raise ValidationError(ctx, data, f"Cannot parse {repr(data)} as int")


@register.ctx_subtypes
def _structure_default(ctx: CtxImpl[DataClassBase, Any, Any, Any], data: dict, *, keymap: dict[str, str] | None) -> Exe:
    origin = get_origin(ctx.structured_type) or ctx.structured_type
    if not origin.__dataclass_params__.init:
        raise NoStructureHook(ctx, data)
    return DataClassExe(ctx, keymap)


class DataClassExe:
    __slots__ = ("children", "dataclass_type", "missing_sentinel")

    children: list[tuple[str, str, bool, Site]]  # field_name, alias, is_required, site
    dataclass_type: Any
    missing_sentinel: object

    def __init__(self, ctx: CtxImpl[DataClassBase, Any, Any, Any], keymap: dict[str, str] | None):
        self.dataclass_type = ctx.structured_type
        self.missing_sentinel = object()
        field_types = resolve_input_field_types(ctx.structured_type)
        self.children = [
            (
                f.name,
                alias := keymap[f.name] if keymap and f.name in keymap else f.name,
                f.default is MISSING and f.default_factory is MISSING,
                _structure_site(
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

    def __call__(self, ctx: CtxImpl[DataClassBase, Any, Any, Any], data: dict) -> Any:
        try:
            args = {
                f: (site.exe(site.ctx, v) if (site.is_bypass_safe and type(v) is site.data_type) else site(v))
                for f, alias, is_required, site in self.children
                if is_required or data.get(alias, self.missing_sentinel) is not self.missing_sentinel
                for v in (data[alias],)
            }
            if len(args) < len(data):
                extra_keys = data.keys() - {alias for _, alias, _, _ in self.children}
                if extra_keys:
                    raise ExtraFields(ctx, data, list(extra_keys))
            try:
                return self.dataclass_type(**args)
            except TypeError as e:
                raise NoStructureHook(ctx, data) from e
        except KeyError as e:
            missing_keys = [alias for _, alias, is_required, _ in self.children if is_required and alias not in data]
            if not (missing_keys and e.args and e.args[0] in set(missing_keys)):
                # The exception is from somewhere else, not a missing key
                raise  # pragma: no cover
            raise MissingFields(ctx, data, missing_keys)


@register.ctx_subtypes
def _structure_default(ctx: CtxImpl[TypedDictBase, Any, Any, Any], data: dict, *, keymap: dict[str, str] | None) -> Exe:
    return TypedDictExe(ctx, keymap)


class TypedDictExe:
    __slots__ = (
        "children",
        "missing_sentinel",
        "declared_keys",
        "field_names",
        "closed",
        "extra_items_type",
        "extra_children",
    )

    children: list[tuple[str, str, bool, Site]]  # field_name, alias, required, site
    missing_sentinel: object
    declared_keys: frozenset[str]
    field_names: frozenset[str]
    closed: bool
    extra_items_type: Any
    extra_children: dict[str, Site]

    def __init__(self, ctx: CtxImpl[TypedDictBase, Any, Any, Any], keymap: dict[str, str] | None):
        self.missing_sentinel = object()
        field_types = resolve_typeddict_field_types(ctx.structured_type)
        td_cls = get_origin(ctx.structured_type) or ctx.structured_type
        required = getattr(td_cls, "__required_keys__", frozenset())
        self.children = [
            (
                name,
                alias := keymap[name] if keymap and name in keymap else name,
                name in required,
                _structure_site(
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
        self.declared_keys = frozenset(alias for _, alias, _, _ in self.children)
        self.field_names = frozenset(name for name, _, _, _ in self.children)
        self.closed, self.extra_items_type = get_typeddict_extras_policy(ctx.structured_type)
        self.extra_children = {}

    def __call__(self, ctx: CtxImpl[TypedDictBase, Any, Any, Any], data: dict) -> Any:
        try:
            out = {
                f: (site.exe(site.ctx, v) if (site.is_bypass_safe and type(v) is site.data_type) else site(v))
                for f, alias, is_required, site in self.children
                if is_required or data.get(alias, self.missing_sentinel) is not self.missing_sentinel
                for v in (data[alias],)
            }
        except KeyError as e:
            missing_keys = [alias for _, alias, is_required, _ in self.children if is_required and alias not in data]
            if not (missing_keys and e.args and e.args[0] in set(missing_keys)):
                # The exception is from somewhere else, not a missing key
                raise  # pragma: no cover
            raise MissingFields(ctx, data, missing_keys)
        if self.closed:
            extras = data.keys() - self.declared_keys
            if extras:
                raise ExtraFields(ctx, data, list(extras))
        elif self.extra_items_type is not None:
            for k in data.keys() - self.declared_keys:
                if type(k) is not str:
                    raise ValidationError(
                        ctx, data, f"TypedDict extra key must be str, got {type(k).__name__}: {repr(k)}"
                    )
                if k in self.field_names:
                    raise ValidationError(ctx, data, f"TypedDict extra key conflicts with declared field: {repr(k)}")
                site = self.extra_children.get(k)
                if site is None:
                    site = _structure_site(
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


@register.ctx_subtypes
def _structure_default(ctx: CtxImpl[LiteralBase, Any, Any, Any], data: Any, *, keymap: dict[str, str] | None) -> Exe:
    args = get_args(ctx.structured_type)
    if literal_values_contain(args, data) and len(args) > 1:
        return UnionMemberExe(ctx, Literal[data])
    return literal_exe


@register.ctx_subtypes
def _structure_default(
    ctx: CtxImpl[LiteralBase, Any, Any, tuple[Any, KeySeg[Any]]], data: Any, *, keymap: dict[str, str] | None
) -> Exe:
    return literal_key_exe


def literal_exe(ctx: CtxImpl[LiteralBase, Any, Any, Any], data: Any) -> Any:
    if literal_values_contain(get_args(ctx.structured_type), data):
        return data
    err = f"Expected one of {', '.join(repr(a) for a in get_args(ctx.structured_type))}, got {repr(data)}"
    raise ValidationError(ctx, data, err)


def literal_key_exe(ctx: CtxImpl[LiteralBase, Any, Any, Any], data: Any) -> Any:
    if literal_values_contain(get_args(ctx.structured_type), data):
        return data
    if not isinstance(data, bool):
        for v in get_args(ctx.structured_type):
            if isinstance(v, bool):
                continue
            if isinstance(v, int):
                try:
                    converted = int(data)
                except (TypeError, ValueError):
                    continue
                if literal_values_contain(get_args(ctx.structured_type), converted):
                    return converted
            elif isinstance(v, Enum):
                try:
                    converted = type(v)(data)
                except (TypeError, ValueError):
                    continue
                if literal_values_contain(get_args(ctx.structured_type), converted):
                    return converted
    return literal_exe(ctx, data)


@register.ctx_subtypes
def _structure_default(ctx: CtxImpl[NewTypeBase, Any, Any, Any], data: Any, *, keymap: dict[str, str] | None) -> Exe:
    supertype = ctx.structured_type.__supertype__
    try:
        return _structure_default(ctx._replace_type(supertype), data, keymap=None)
    except NoMatchFound as e:
        raise NoStructureHook(ctx, data) from e


@register.ctx_subtypes
def _structure_default(ctx: CtxImpl[UnionBase, Any, Any, Any], data: Any, *, keymap: dict[str, str] | None) -> Exe:
    if keymap is not None:
        raise ValidationError(ctx, data, "keymap is not supported for union default conversion")
    dispatch = config._dispatcher.get().dispatch
    all_members = tuple(normalize_type(m) for m in get_args(ctx.structured_type))
    for m in all_members:
        origin, args = normalized_origin_args(m)
        if origin is Literal and literal_values_contain(args, data):
            return UnionMemberExe(ctx, Literal[data])
    non_literal_members = tuple(m for m in all_members if normalized_origin_args(m)[0] is not Literal)
    default = dispatch["_structure_default"]
    probed_raw = probe_union_candidates(
        dispatch.get("structure_hook"),
        default,
        non_literal_members,
        ctx,
        data,
    )
    if probed_raw is None:
        raise AmbiguousUnion(ctx, data, "A union member causes ambiguous dispatch with the data")
    probed_all = [c for c, _ in probed_raw]
    if probed_all and issubclass(type(data), dict) and all(_is_dataclass_or_typeddict(c) for c in probed_all):
        discriminator = generate_decision_func(probed_all)
        if discriminator is not None:
            return DataClassTypedDictUnionExe(discriminator)
        else:
            raise AmbiguousUnion(ctx, data, "Union members cannot be discriminated by their fields or a Literal tag")
    probed = select_union_candidate(probed_raw, default.arg_type(1, data))
    match len(probed):
        case 0:
            raise NoStructureHook(ctx, data)
        case 1:
            return UnionMemberExe(ctx, probed[0])
        case _:
            raise AmbiguousUnion(ctx, data, f"Multiple members of the union are compatible with the data: {probed}")


def _is_dataclass_or_typeddict(c: Any) -> bool:
    return is_dataclass(get_origin(c) or c) or is_typeddict(get_origin(c) or c)


class UnionMemberExe:
    __slots__ = ("child",)

    def __init__(self, ctx: CtxImpl, concrete_type: Any):
        newctx = ctx._replace_type(concrete_type)
        self.child = _structure_site(newctx)

    def __call__(self, ctx: CtxImpl, data: Any) -> Any:
        return self.child(data)


class DataClassTypedDictUnionExe:
    __slots__ = ("discriminator", "children")

    discriminator: Callable
    children: dict[Any, tuple[CtxImpl, Site]]

    def __init__(self, discriminator: Callable):
        self.discriminator = discriminator
        self.children = {}

    def __call__(self, ctx: CtxImpl[UnionBase, Any, Any, Any], data: dict) -> Any:
        dcls = self.discriminator(data)
        if dcls is None:
            raise NoStructureHook(ctx, data, "The data is not compatible with any member of the union")
        newctx, site = self.children.get(dcls, (None, None))
        if newctx is None or site is None:
            newctx = ctx._replace_type(dcls)
            site = _structure_site(newctx)
            self.children[dcls] = (newctx, site)
        return site(data)
