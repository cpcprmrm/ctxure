import sys
from collections import deque
from collections.abc import Hashable
from dataclasses import Field, InitVar, fields
from functools import lru_cache, reduce
from types import GenericAlias, UnionType
from typing import (
    Any,
    ClassVar,
    ForwardRef,
    Literal,
    NewType,
    TypeVar,
    Union,
    _GenericAlias,  # type: ignore
    get_args,
    get_origin,
    get_type_hints,
)

from typing_extensions import NoExtraItems, NotRequired, ReadOnly, Required, is_typeddict
from typing_extensions import TypeAliasType as _TypeAliasTypeExt

from ._typeinfo import _type_info

_MAX_ALIAS_DEPTH = 64

# On 3.11 only `typing_extensions.TypeAliasType` exists.
# On 3.12 and 3.13, `typing.TypeAliasType` exists.
# On 3.14+ they are unified.
if sys.version_info >= (3, 12):  # pragma: no cover
    from typing import TypeAliasType as _TypeAliasTypeStd

    TYPE_ALIAS_TYPES: tuple[type, ...] = (
        (_TypeAliasTypeExt,) if _TypeAliasTypeExt is _TypeAliasTypeStd else (_TypeAliasTypeExt, _TypeAliasTypeStd)
    )
else:  # pragma: no cover
    TYPE_ALIAS_TYPES = (_TypeAliasTypeExt,)


def get_mro(cls: type) -> tuple[type, ...]:
    info = _type_info.get(cls)
    return info.mro if info else getattr(cls, "__mro__", ())


def get_orig_bases(cls: type) -> tuple:
    info = _type_info.get(cls)
    return info.orig_bases if info else getattr(cls, "__orig_bases__", ())


def is_union(t: Any) -> bool:
    """
    On 3.11 ~ 3.13: int | str is UnionType, Union[int, str] is _GenericAlias.
    On 3.14+: both produce UnionType.
    """
    return isinstance(t, UnionType) or get_origin(t) is Union


def is_type(t: Any) -> bool:
    return (
        isinstance(t, type)
        or type(t) in (GenericAlias, _GenericAlias, NewType, *TYPE_ALIAS_TYPES)
        or isinstance(get_origin(t), TYPE_ALIAS_TYPES)
        or is_union(t)
        or get_origin(t) is Literal
        or is_typeddict(t)
    )


def is_type_alias(t: Any) -> bool:
    return isinstance(t, TYPE_ALIAS_TYPES) or isinstance(get_origin(t), TYPE_ALIAS_TYPES)


def literal_key(v: Any) -> tuple[type, Any]:
    return type(v), v


def literal_values_contain(values: tuple[Any, ...], v: Any) -> bool:
    if not isinstance(v, Hashable):
        return False
    return literal_key(v) in {literal_key(x) for x in values}


def literal_values_contain_all(values: tuple[Any, ...], candidates: tuple[Any, ...]) -> bool:
    keys = {literal_key(v) for v in values}
    return all(literal_key(v) in keys for v in candidates)


def literal_values_equal(left: tuple[Any, ...], right: tuple[Any, ...]) -> bool:
    return {literal_key(v) for v in left} == {literal_key(v) for v in right}


def _resolve_type_alias(t: Any) -> Any:
    if isinstance(t, TYPE_ALIAS_TYPES):
        return t.__value__
    origin = get_origin(t)
    value = origin.__value__
    params = origin.__type_params__
    return apply_typevar_substitution(value, dict(zip(params, get_args(t))))


def resolve_type_alias(t: Any) -> Any:
    for _ in range(_MAX_ALIAS_DEPTH):
        if not is_type_alias(t):
            return t
        t = _resolve_type_alias(t)
    raise TypeError(f"Cyclic or excessively deep type alias chain at {t}")


def normalize_type(t: Any) -> Any:
    return resolve_type_alias(t) if is_type_alias(t) else t


def normalized_origin_args(t: Any) -> tuple[Any, tuple[Any, ...]]:
    t = normalize_type(t)
    return get_origin(t), get_args(t)


def get_type_params(cls: type) -> tuple:
    """
    Returns the tuple of type variables associated with generic type `cls`.
    Checks _type_info registry first (for builtin/abc types), then falls back
    to class attributes (__parameters__ for legacy, __type_params__ for 3.12+).
    """
    info = _type_info.get(cls)
    if info:
        return info.parameters
    return getattr(cls, "__parameters__", ()) or getattr(cls, "__type_params__", ())


if sys.version_info >= (3, 14):  # pragma: no cover

    def _eval_forward_ref(ref: ForwardRef, glbls: dict, type_params: tuple) -> Any:
        from typing import evaluate_forward_ref

        return evaluate_forward_ref(ref, globals=glbls, type_params=type_params)

elif "type_params" in __import__("inspect").signature(ForwardRef._evaluate).parameters:  # pragma: no cover

    def _eval_forward_ref(ref: ForwardRef, glbls: dict, type_params: tuple) -> Any:
        return ref._evaluate(glbls, None, type_params, recursive_guard=frozenset())

else:  # pragma: no cover

    def _eval_forward_ref(ref: ForwardRef, glbls: dict, type_params: tuple) -> Any:
        return ref._evaluate(glbls, None, recursive_guard=frozenset())


@lru_cache(maxsize=256)
def eval_forward_ref(ref: ForwardRef, origin: type) -> Any:
    """
    Evaluate a forward reference using the namespace of the origin class.
    """
    glbls = sys.modules[origin.__module__].__dict__
    type_params = get_type_params(origin)
    return _eval_forward_ref(ref, glbls, type_params)


@lru_cache(maxsize=256)
def build_field_to_base_definer_map(origin: type) -> dict[str, type]:
    """
    Build a mapping from each field name of `origin` to the class that defines the field, considering inheritance.
    """
    field_to_class: dict[str, type] = {}
    for cls in origin.__mro__:
        if cls is object:
            break
        for field_name in cls.__annotations__:
            if field_name not in field_to_class:  # if not overridden
                field_to_class[field_name] = cls
    return field_to_class


def apply_typevar_substitution(t: Any, typevar_to_type: dict[TypeVar, Any]) -> Any:
    """
    Resolve the concrete type of `t` using the provided type variable to type mapping.
    This requires recursively resolving any nested TypeVars within `t`. For example,
    `t = Foo[T] | Bar[list[S]]` with `typevar_to_type = {T: int, S: str}` resolves to `Foo[int] | Bar[list[str]]`.
    """
    match t:
        case TypeVar():
            resolved = typevar_to_type.get(t)
            if resolved is None or resolved is t or isinstance(resolved, TypeVar):
                return Any
            return apply_typevar_substitution(resolved, typevar_to_type)
        case GenericAlias() | _GenericAlias():
            resolved = tuple(apply_typevar_substitution(a, typevar_to_type) for a in get_args(t))
            return get_origin(t)[*resolved]  # type: ignore[index]
        case UnionType():
            terms = list(apply_typevar_substitution(a, typevar_to_type) for a in get_args(t))
            return reduce(lambda x, y: x | y, terms)
        case type():
            return t
        case _:
            return t


def _resolve_base_typevar_substitution(origin: type, args: tuple) -> dict[type, dict[TypeVar, Any]]:
    """
    Returns a dict mapping each class in inheritance hierarchy to its resolved type parameters.
    For example, if `Derived(Base[list[T]], Generic[T])` and `origin` is `Derived` with `args` is `(int,)`,
    this returns `{Derived: {T: int}, Base: {T: list[int]}}`.
    """
    base_to_typevar_substitution: dict[type, dict[TypeVar, Any]] = {}

    params = get_type_params(origin)
    args = tuple(eval_forward_ref(a, origin) if isinstance(a, ForwardRef) else a for a in args)
    base_to_typevar_substitution[origin] = dict(zip(params, args))

    for cls in get_mro(origin):
        if cls is object:
            break

        orig_bases = get_orig_bases(cls)
        if not orig_bases:
            continue

        substitution = base_to_typevar_substitution.get(cls, {})

        for base in orig_bases:
            base_origin = get_origin(base)
            if base_origin is None:
                continue
            if base_origin in base_to_typevar_substitution:
                continue
            if not (base_params := get_type_params(base_origin)):
                continue
            base_args = tuple(eval_forward_ref(a, cls) if isinstance(a, ForwardRef) else a for a in get_args(base))
            resolved_base_args = tuple(apply_typevar_substitution(a, substitution) for a in base_args)
            base_to_typevar_substitution[base_origin] = dict(zip(base_params, resolved_base_args))

    return base_to_typevar_substitution


def is_nominal_subclass(origin: type, base: type) -> bool:
    """
    Check if `origin` is a nominal subclass of `base`.

    Wraps `issubclass` with TypedDict-aware handling: TypedDict classes raise
    `TypeError` on `issubclass`, and their inheritance from other TypedDicts is
    recorded only in `__orig_bases__` (not `__mro__`). For TypedDict pairs, we
    recursively walk `__orig_bases__` instead. `object` is treated as the
    universal top for any TypedDict. `dict` is not reached via this walk,
    enforcing the "TypedDict is not a subtype of dict" rule.
    """
    if is_typeddict(origin) or is_typeddict(base):
        return _typeddict_reaches(origin, base)
    return issubclass(origin, base)


def _typeddict_reaches(origin: type, base: type) -> bool:
    if base is object:
        return True
    if origin is base:
        return True
    for parent in getattr(origin, "__orig_bases__", ()):
        parent_origin = get_origin(parent) or parent
        if isinstance(parent_origin, type) and _typeddict_reaches(parent_origin, base):
            return True
    return False


@lru_cache(maxsize=256)
def resolve_base_args(origin: type, base: type, args: tuple) -> tuple | None:
    """
    Resolve type args of `origin` as seen from `base`'s perspective.
    Returns a tuple of resolved args (like `get_args`), or None if `origin` is not a subclass of `base`.
    For example, if `origin[U, V]` extends `base[V, list[U]]`, and `args` is `(int, str)`,
    `_resolve_base_args(origin, args, base)` is (str, list[int])`.
    """
    substitution = _resolve_base_typevar_substitution(origin, args).get(base)
    if substitution is None:
        if not is_nominal_subclass(origin, base):
            return None
        base_params = get_type_params(base)
        return tuple(Any for _ in base_params)
    else:
        base_params = get_type_params(base)
        return tuple(substitution.get(p, Any) for p in base_params)


def _resolve_generic_field_types(origin: type, args: tuple) -> list[tuple[Field, Any]]:
    """
    Resolve field types for a generic class. For example, with:

    ```
        T = TypeVar("T")

        class Base(Generic[T]):
            foo: T

        class Derived(Base[list[T]], Generic[T]):
            bar: T
    ```

    When resolving `Derived[int]`,
        - `bar`'s type should be resolved as `int`, which is `Derived`'s own fields with `T = int`.
        - `foo`'s type should be resolved as `list[int]`, which is `Base`'s fields with `T = list[int]`.

    So, The result is `[(foo, list[int]), (bar, int)]`.

    In this example, TypeVar `T` is shared between `Base` and `Derived`, but has different concrete types.
    So we process each class in the inheritance hierarchy separately to handle shared TypeVars correctly.

    If PEP695 syntax was used, `Base` and `Derived` have different TypeVars. Anyway, the same logic applies.
    """
    # {base : (type_var : type}}
    base_to_typevar_substitution = _resolve_base_typevar_substitution(origin, args)
    # {field_name : base}
    field_to_definer = build_field_to_base_definer_map(origin)
    # {field_name : hint} where hint can be a TypeVar.
    # Pass PEP 695 type params as localns so get_type_hints can resolve string annotations
    # like "list[T]" where T is a __type_params__ member, not a module-level TypeVar.
    type_param_ns = {
        tp.__name__: tp for cls in getattr(origin, "__mro__", ()) for tp in getattr(cls, "__type_params__", ())
    }
    field_to_hint = get_type_hints(origin, localns=type_param_ns or None)

    result = []

    for field in fields(origin):
        definer_base = field_to_definer.get(field.name, origin)
        typevar_to_type = base_to_typevar_substitution.get(definer_base, {})
        field_hint = field_to_hint[field.name]
        resolved_type = apply_typevar_substitution(field_hint, typevar_to_type)
        result.append((field, resolved_type))

    return result


def _dataclass_type_param_ns(origin: type) -> dict[str, Any]:
    return {tp.__name__: tp for cls in getattr(origin, "__mro__", ()) for tp in getattr(cls, "__type_params__", ())}


def _dataclass_field_hint_type(hint: Any) -> Any:
    if isinstance(hint, InitVar):
        return hint.type
    return hint


def _resolve_generic_input_field_types(origin: type, args: tuple) -> list[tuple[Field, Any]]:
    base_to_typevar_substitution = _resolve_base_typevar_substitution(origin, args)
    field_to_definer = build_field_to_base_definer_map(origin)
    type_param_ns = _dataclass_type_param_ns(origin)
    field_to_hint = get_type_hints(origin, localns=type_param_ns or None)

    result = []

    for field in origin.__dataclass_fields__.values():
        field_hint = field_to_hint[field.name]
        if get_origin(field_hint) is ClassVar:
            continue
        if not field.init:
            continue
        definer_base = field_to_definer.get(field.name, origin)
        typevar_to_type = base_to_typevar_substitution.get(definer_base, {})
        field_hint = _dataclass_field_hint_type(field_hint)
        resolved_type = apply_typevar_substitution(field_hint, typevar_to_type)
        result.append((field, resolved_type))

    return result


def _resolve_nongeneric_field_types(target: type) -> list[tuple[Field, Any]]:
    """
    Resolve field types for a non-generic class.
    """
    hints = get_type_hints(target)
    return [(f, hints[f.name]) for f in fields(target)]


def _resolve_nongeneric_input_field_types(target: type) -> list[tuple[Field, Any]]:
    hints = get_type_hints(target)
    return [
        (f, _dataclass_field_hint_type(hints[f.name]))
        for f in target.__dataclass_fields__.values()
        if f.init and get_origin(hints[f.name]) is not ClassVar
    ]


@lru_cache(maxsize=256)
def resolve_field_types(dcls: Any) -> list[tuple[Field, Any]]:
    # Parameterized (e.g., Foo[int])
    if isinstance(dcls, _GenericAlias):
        return _resolve_generic_field_types(get_origin(dcls), get_args(dcls))

    # Generic type but not parametrized (e.g., Foo)
    if get_type_params(dcls) or any(get_origin(base) is not None for base in getattr(dcls, "__orig_bases__", ())):
        return _resolve_generic_field_types(dcls, ())

    # Plain non-generic type
    return _resolve_nongeneric_field_types(dcls)


@lru_cache(maxsize=256)
def resolve_input_field_types(dcls: Any) -> list[tuple[Field, Any]]:
    # Parameterized (e.g., Foo[int])
    if isinstance(dcls, _GenericAlias):
        return _resolve_generic_input_field_types(get_origin(dcls), get_args(dcls))

    # Generic type but not parametrized (e.g., Foo)
    if get_type_params(dcls) or any(get_origin(base) is not None for base in getattr(dcls, "__orig_bases__", ())):
        return _resolve_generic_input_field_types(dcls, ())

    # Plain non-generic type
    return _resolve_nongeneric_input_field_types(dcls)


def _build_typeddict_field_to_base_definer_map(origin: type) -> dict[str, type]:
    """
    TypedDict analog of build_field_to_base_definer_map.

    Unlike dataclasses (where each class's `__annotations__` contains only its own fields),
    TypedDict subclasses have all inherited field annotations copied into their own `__annotations__`.
    So walking leaf-to-root always attributes fields to the leaf, which is wrong.

    Instead, we collect the TypedDict chain via `__orig_bases__` and walk from root to leaf
    so the first (deepest-ancestor) declaration of each field wins,
    which identifies the true definer for TypeVar substitution purposes.
    """
    chain: list[type] = []

    def collect(cls: type) -> None:
        chain.append(cls)
        for base in getattr(cls, "__orig_bases__", ()):
            base_origin = get_origin(base) or base
            if isinstance(base_origin, type) and is_typeddict(base_origin):
                collect(base_origin)

    collect(origin)

    field_to_class: dict[str, type] = {}
    for cls in reversed(chain):
        for field_name in getattr(cls, "__annotations__", {}):
            if field_name not in field_to_class:
                field_to_class[field_name] = cls
    return field_to_class


def _resolve_typeddict_base_typevar_substitution(origin: type, args: tuple) -> dict[type, dict[TypeVar, Any]]:
    """
    TypedDict-specific base TypeVar resolver.
    TypedDict parents are stored in `__orig_bases__` but omitted from `__mro__`,
    """
    base_to_typevar_substitution: dict[type, dict[TypeVar, Any]] = {}

    params = get_type_params(origin)
    args = tuple(eval_forward_ref(a, origin) if isinstance(a, ForwardRef) else a for a in args)
    base_to_typevar_substitution[origin] = dict(zip(params, args))

    seen: set[type] = set()
    to_visit: deque[type] = deque([origin])
    while to_visit:
        cls = to_visit.popleft()
        if cls in seen:
            continue
        seen.add(cls)

        substitution = base_to_typevar_substitution.get(cls, {})
        for base in get_orig_bases(cls):
            base_origin = get_origin(base)
            if base_origin is None or not isinstance(base_origin, type):
                continue
            if is_typeddict(base_origin):
                to_visit.append(base_origin)
            if base_origin in base_to_typevar_substitution:
                continue
            if not (base_params := get_type_params(base_origin)):
                continue
            base_args = tuple(eval_forward_ref(a, cls) if isinstance(a, ForwardRef) else a for a in get_args(base))
            resolved_base_args = tuple(apply_typevar_substitution(a, substitution) for a in base_args)
            base_to_typevar_substitution[base_origin] = dict(zip(base_params, resolved_base_args))

    return base_to_typevar_substitution


def _resolve_generic_typeddict_field_types(origin: type, args: tuple) -> list[tuple[str, Any]]:
    """
    TypedDict analog of _resolve_generic_field_types.
    Returns (field_name, resolved_type) pairs since TypedDict has no `dataclasses.Field` objects.
    """
    base_to_typevar_substitution = _resolve_typeddict_base_typevar_substitution(origin, args)
    field_to_definer = _build_typeddict_field_to_base_definer_map(origin)
    type_param_ns = {
        tp.__name__: tp for cls in getattr(origin, "__mro__", ()) for tp in getattr(cls, "__type_params__", ())
    }
    field_to_hint = get_type_hints(origin, localns=type_param_ns or None)

    result = []
    for name, hint in field_to_hint.items():
        definer_base = field_to_definer.get(name, origin)
        typevar_to_type = base_to_typevar_substitution.get(definer_base, {})
        resolved_type = apply_typevar_substitution(hint, typevar_to_type)
        result.append((name, resolved_type))
    return result


def _resolve_nongeneric_typeddict_field_types(target: type) -> list[tuple[str, Any]]:
    return list(get_type_hints(target).items())


@lru_cache(maxsize=256)
def resolve_typeddict_field_types(td: Any) -> list[tuple[str, Any]]:
    """
    Resolve field types for a TypedDict. Returns a list of (field_name, resolved_type)
    pairs in declaration order (inherited fields from parent TypedDicts included).
    """
    # Parameterized (e.g., MyTD[int])
    if isinstance(td, _GenericAlias):
        return _resolve_generic_typeddict_field_types(get_origin(td), get_args(td))

    # Generic TypedDict but not parameterized (e.g., MyTD)
    if get_type_params(td) or any(get_origin(base) is not None for base in getattr(td, "__orig_bases__", ())):
        return _resolve_generic_typeddict_field_types(td, ())

    # Plain non-generic TypedDict
    return _resolve_nongeneric_typeddict_field_types(td)


def get_typeddict_extras_policy(td: Any) -> tuple[bool, Any]:
    """
    Walk the TypedDict chain (leaf to root, via `__orig_bases__`) for the nearest ancestor
    that explicitly declares PEP 728 `closed` or `extra_items`.
    Returns `(is_closed, extra_items_type)`; `extra_items_type is None` means no typed extras are configured.
    typing_extensions stores these flags only on the declaring class (no automatic inheritance at runtime),
    so we walk the chain ourselves.
    """
    td_cls = get_origin(td) or td
    args = get_args(td)
    substitutions = _resolve_typeddict_base_typevar_substitution(td_cls, args)
    seen: set[type] = set()
    stack: list[type] = [td_cls]
    while stack:
        cur = stack.pop(0)
        if cur in seen or not is_typeddict(cur):
            continue
        seen.add(cur)
        closed = getattr(cur, "__closed__", None)
        extra = getattr(cur, "__extra_items__", NoExtraItems)
        if closed is not None or extra is not NoExtraItems:
            if extra is NoExtraItems:
                return closed is True, None
            extra = normalize_type(extra)
            extra = _strip_typeddict_item_qualifiers(extra)
            extra = apply_typevar_substitution(extra, substitutions.get(cur, {}))
            extra = _strip_typeddict_item_qualifiers(normalize_type(extra))
            return closed is True, extra
        for base in getattr(cur, "__orig_bases__", ()):
            base_origin = get_origin(base) or base
            if isinstance(base_origin, type):
                stack.append(base_origin)
    return False, None


def _strip_typeddict_item_qualifiers(t: Any) -> Any:
    while get_origin(t) in (ReadOnly, Required, NotRequired):
        args = get_args(t)
        if len(args) != 1:
            break
        t = args[0]
    return t
