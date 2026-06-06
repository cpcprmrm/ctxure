import functools
import inspect
from collections.abc import Callable, Hashable, ItemsView, Sequence
from dataclasses import Field, dataclass, field, is_dataclass
from types import GenericAlias
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Iterable,
    Literal,
    Never,
    NewType,
    Self,
    _GenericAlias,  # type: ignore
    cast,
    get_args,
    get_origin,
    get_type_hints,
)

from typing_extensions import TypeForm, is_typeddict

from ctxure._typeutil import (
    TYPE_ALIAS_TYPES,
    get_type_params,
    is_nominal_subclass,
    is_type_alias,
    is_union,
    literal_key,
    literal_values_contain_all,
    literal_values_equal,
    normalized_origin_args,
    resolve_base_args,
    resolve_type_alias,
)
from ctxure._util import format_typeform


class DataClassBase:
    if TYPE_CHECKING:
        __dataclass_fields__: ClassVar[dict[str, Field[Any]]]
    pass


class TypedDictBase: ...


class LiteralBase: ...


class NewTypeBase: ...


class UnionBase: ...


class DispatchError(TypeError): ...


class NoMatchFound(DispatchError):
    def __init__(self, arg_types: tuple[TypeForm, ...], message: str | None = None):
        self.arg_types = arg_types
        if message is None:
            message = f"No match found for {arg_types}"
        super().__init__(message)


class MultipleMatchesFound(DispatchError):
    def __init__(self, candidates: list["Method"], message: str | None = None):
        self.candidates = candidates
        if message is None:
            lines = ["Multiple matches found:"]
            for m in candidates:
                code = m.func.__code__
                sig_str = "(" + ", ".join(format_typeform(t) for t in m.signature) + ")"
                lines.append(f"  {sig_str} at {code.co_filename}:{code.co_firstlineno}")
            message = "\n".join(lines)
        super().__init__(message)


class _EmptyTupleArg: ...


def is_subtype_invariant(lhs: TypeForm, rhs: TypeForm) -> bool:
    # involving type alias

    if is_type_alias(lhs):
        lhs = resolve_type_alias(lhs)
    if is_type_alias(rhs):
        rhs = resolve_type_alias(rhs)

    # involving Any

    if rhs is Any:
        return True
    if lhs is Any:
        return False

    # involving Never

    if lhs is Never:
        return True
    if rhs is Never:
        return False

    l_origin, l_args = _get_origin_and_args(lhs)
    r_origin, r_args = _get_origin_and_args(rhs)

    # involving DataClassBase

    if rhs is DataClassBase:
        return is_dataclass(l_origin)

    # involving TypedDictBase

    if rhs is TypedDictBase:
        return is_typeddict(l_origin)

    # involving unions

    if is_union(lhs):
        if rhs is UnionBase:
            return True
        if rhs is NewTypeBase or rhs is LiteralBase:
            return False
        return all(is_subtype_invariant(l, rhs) for l in l_args)
    if is_union(rhs):
        if l_origin is Literal:
            return all(any(is_subtype_invariant(cast(TypeForm, Literal[v]), r) for r in r_args) for v in l_args)
        return any(is_subtype_invariant(lhs, r) for r in r_args)

    # involving tuples

    if (result := _is_subtype_tuple(lhs, rhs, l_origin, l_args, r_origin, r_args, _is_equal_invariant)) is not None:
        return result

    # involving Literals

    if l_origin is Literal:
        if r_origin is LiteralBase:
            return True
        if r_origin is Literal:
            return literal_values_contain_all(r_args, l_args)
        return all(is_subtype_invariant(type(v), rhs) for v in l_args)
    if r_origin is Literal:
        return False

    # involving NewTypes

    if (supertype := getattr(lhs, "__supertype__", None)) is not None:
        return r_origin is NewTypeBase or lhs == rhs or is_subtype_covariant(supertype, rhs)
    if type(rhs) is NewType:
        return False

    # Both are nongeneric classes

    if not l_args and not r_args:
        # Practical utility over strict Python subtype relation.
        if lhs is int and (rhs is float or rhs is complex):
            return True
        if lhs is bool and (rhs is float or rhs is complex):
            return True
        if lhs is float and rhs is complex:
            return True
        return is_nominal_subclass(cast(type, lhs), cast(type, rhs))

    # involving generic classes

    base_args = resolve_base_args(l_origin, r_origin, l_args)
    if base_args is None or len(base_args) != len(r_args):
        return False
    return all(_is_equal_invariant(l, r) for l, r in zip(base_args, r_args))


def is_subtype_covariant(lhs: TypeForm, rhs: TypeForm) -> bool:
    # involving type alias

    if is_type_alias(lhs):
        lhs = resolve_type_alias(lhs)
    if is_type_alias(rhs):
        rhs = resolve_type_alias(rhs)

    # involving Any

    if rhs is Any:
        return True
    if lhs is Any:
        return False

    # involving Never

    if lhs is Never:
        return True
    if rhs is Never:
        return False

    l_origin, l_args = _get_origin_and_args(lhs)
    r_origin, r_args = _get_origin_and_args(rhs)

    # involving DataClassBase

    if rhs is DataClassBase:
        return is_dataclass(l_origin)

    # involving TypedDictBase

    if rhs is TypedDictBase:
        return is_typeddict(l_origin)

    # involving unions

    if is_union(lhs):
        if rhs is UnionBase:
            return True
        if rhs is NewTypeBase or rhs is LiteralBase:
            return False
        return all(is_subtype_covariant(l, rhs) for l in l_args)
    if is_union(rhs):
        if l_origin is Literal:
            return all(any(is_subtype_covariant(cast(TypeForm, Literal[v]), r) for r in r_args) for v in l_args)
        return any(is_subtype_covariant(lhs, r) for r in r_args)

    # involving tuples

    if (result := _is_subtype_tuple(lhs, rhs, l_origin, l_args, r_origin, r_args, is_subtype_covariant)) is not None:
        return result

    # involving Literals

    if l_origin is Literal:
        if r_origin is LiteralBase:
            return True
        if r_origin is Literal:
            return literal_values_contain_all(r_args, l_args)
        return all(is_subtype_covariant(type(l), rhs) for l in l_args)
    if r_origin is Literal:
        return False

    # involving NewTypes

    if (supertype := getattr(lhs, "__supertype__", None)) is not None:
        return r_origin is NewTypeBase or lhs == rhs or is_subtype_covariant(supertype, rhs)
    if type(rhs) is NewType:
        return False

    # Both are nongeneric classes

    if not l_args and not r_args:
        if lhs is LiteralBase and rhs not in (DataClassBase, TypedDictBase, NewTypeBase, UnionBase, LiteralBase):
            return True
        # Practical utility over strict Python subtype relation.
        if lhs is int and (rhs is float or rhs is complex):
            return True
        if lhs is bool and (rhs is float or rhs is complex):
            return True
        if lhs is float and rhs is complex:
            return True
        return is_nominal_subclass(cast(type, lhs), cast(type, rhs))

    # involving generic classes

    base_args = resolve_base_args(l_origin, r_origin, l_args)
    if base_args is None or len(base_args) != len(r_args):
        return False
    return all(is_subtype_covariant(l, r) for l, r in zip(base_args, r_args))


def _is_subtype_tuple(
    lhs: TypeForm,
    rhs: TypeForm,
    l_origin: type,
    l_args: tuple,
    r_origin: type,
    r_args: tuple,
    cmp: Callable[[TypeForm, TypeForm], bool],
) -> bool | None:
    if r_origin is tuple:
        if rhs is tuple:
            return l_origin is tuple
        if lhs is tuple:
            return False
        if len(r_args) == 2 and r_args[1] == Ellipsis:
            if l_origin is tuple:
                if l_args == (_EmptyTupleArg,):
                    return True
                if len(l_args) == 2 and l_args[1] == Ellipsis:
                    return cmp(l_args[0], r_args[0])
                if r_args[0] is Any:
                    return True
                return all(cmp(l, r_args[0]) for l in l_args)
            return False
        else:
            if l_origin is tuple:
                if l_args == (_EmptyTupleArg,):
                    return r_args == (_EmptyTupleArg,)
                if len(l_args) == 2 and l_args[1] == Ellipsis:
                    return False
                if len(l_args) == len(r_args):
                    return all(cmp(l, r) for l, r in zip(l_args, r_args))
            return False
    if l_origin is tuple:
        # tuple vs non-tuple base (e.g., Sequence[V])
        if not issubclass(tuple, r_origin):
            return False
        r_v = r_args[0] if r_args else Any
        if l_args == (_EmptyTupleArg,):
            return True
        if len(l_args) == 2 and l_args[1] is Ellipsis:
            return cmp(l_args[0], r_v)
        return all(cmp(u, r_v) for u in l_args)
    return None


def _is_equal_invariant(lhs: TypeForm, rhs: TypeForm) -> bool:
    if rhs is Any:
        return True
    if lhs == rhs:
        return True
    if lhs is Never:
        return True
    l_origin, l_args = _get_origin_and_args(lhs)
    r_origin, r_args = _get_origin_and_args(rhs)
    if l_origin is Literal and r_origin is Literal:
        return literal_values_equal(l_args, r_args)
    if l_origin != r_origin:
        if (l_origin is Literal and is_union(rhs)) or (r_origin is Literal and is_union(lhs)):
            return is_subtype_invariant(lhs, rhs) and is_subtype_invariant(rhs, lhs)
        return False
    if l_origin is tuple and not r_args:
        return True
    if len(l_args) != len(r_args):
        return False
    return all(_is_equal_invariant(a, b) for a, b in zip(l_args, r_args))


def _get_origin_and_args(t: Any) -> tuple[type, tuple[TypeForm, ...]]:
    if is_type_alias(t):
        t = resolve_type_alias(t)
    if o := get_origin(t):
        args = get_args(t)
        if o is tuple and args == ():
            # Empty tuple: tuple[()]
            return o, (_EmptyTupleArg,)
        else:
            # Parameterized generic, Literal, union
            return o, args
    else:
        args = (Any,) * len(get_type_params(t))
        if args:
            # Bare generic or (possibly parameterized) tuple
            return (t, args)
        else:
            # Non-generic or NewType
            return (t, ())


def _equiv(left: TypeForm, right: TypeForm) -> bool:
    return (left == right) or (is_subtype_covariant(left, right) and is_subtype_covariant(right, left))


def _cannot_set_orig_class(cls: type) -> bool:
    params = getattr(cls, "__dataclass_params__", None)
    if params is not None and params.frozen:
        return True
    # If cls itself doesn't define __slots__, instances always have __dict__.
    # Parent classes' __slots__ (e.g. Generic.__slots__ = ()) don't restrict this.
    if "__slots__" not in cls.__dict__:
        return False
    # cls defines __slots__; check if __orig_class__ or __dict__ appears anywhere in MRO slots.
    for c in cls.__mro__:
        slots = getattr(c, "__slots__", None)
        if slots is not None:
            if "__orig_class__" in slots or "__dict__" in slots:
                return False
    return True


@dataclass(frozen=True)
class Method:
    signature: tuple[TypeForm, ...]
    func: Callable
    covariant_args: frozenset[int] = frozenset()

    @classmethod
    def from_func(cls, func: Callable, covariant_args: Iterable[int]) -> "Method":
        sig = inspect.signature(func)
        params = [
            p
            for p in sig.parameters.values()
            if p.kind
            in {
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            }
        ]
        hints = get_type_hints(func, include_extras=True)
        signature = []
        for i, p in enumerate(params):
            if p.default != inspect.Parameter.empty:
                raise TypeError("Default values are not allowed.")
            hint = hints.get(p.name, object)
            cls._validate_dispatchable_hint(hint, p.name)
            signature.append(hint)
        return cls(
            signature=tuple(signature),
            func=func,
            covariant_args=frozenset(covariant_args),
        )

    @classmethod
    def _validate_dispatchable_hint(cls, hint: TypeForm, param_name: str) -> None:
        resolved_hint = resolve_type_alias(hint)
        if is_union(resolved_hint):
            for member in get_args(resolved_hint):
                cls._validate_dispatchable_hint(member, param_name)
            return
        if hasattr(resolved_hint, "__supertype__"):
            raise TypeError(
                "NewTypes are not allowed as a top-level hint for multidispatch. "
                f"Instances of {hint} do not carry runtime type information."
            )
        if is_typeddict(resolved_hint):
            raise TypeError(
                "TypedDicts are not allowed as a top-level hint for multidispatch. "
                f"Instances of {hint} are plain dicts at runtime and do not carry TypedDict type information."
            )

        origin = get_origin(resolved_hint)

        if origin is None:
            return
        if origin is type:
            return
        if origin is Literal:
            return
        if not hasattr(origin, "__orig_bases__"):
            if not (
                all(a is Any for a in get_args(resolved_hint))
                or (origin is tuple and get_args(resolved_hint) == (Any, Ellipsis))
            ):
                raise TypeError(
                    f"Parameterized builtin type {hint} is not allowed as a top-level hint for multidispatch. "
                    f"Instances of {hint} do not carry runtime type parameter information. "
                    f"Use the bare type {origin.__name__} instead."
                )
        else:
            args_ = get_args(resolved_hint)
            if args_ and not all(a is Any for a in args_):
                if _cannot_set_orig_class(origin):
                    raise TypeError(
                        f"Parameterized type {hint} is not allowed as a top-level hint for multidispatch. "
                        f"{origin.__name__} is a frozen or slotted type whose instances cannot carry "
                        f"__orig_class__, so the hook will never fire. "
                        f"Use the bare or Any-parameterized form instead."
                    )

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)


@dataclass
class Node:
    hint: TypeForm
    method: Method | None
    children: list["Node"] = field(default_factory=list)
    covariant: bool = False

    def copy(self) -> "Node":
        return Node(
            hint=self.hint, method=self.method, children=[c.copy() for c in self.children], covariant=self.covariant
        )


class DispatchTree:
    children: list[Node]
    nullary: Node | None

    def __init__(self):
        self.children = []
        self.nullary = None

    def add(self, method: Method) -> None:
        if method.signature == ():
            self.nullary = Node(Never, method)
        else:
            DispatchTree._add(0, self.children, method)

    @staticmethod
    def _add(level: int, nodes: list[Node], method: Method) -> None:
        current_hint = method.signature[level]
        is_covariant = level in method.covariant_args
        for n in nodes:
            if _equiv(n.hint, current_hint):
                if n.covariant != is_covariant:
                    fixed = "covariant" if n.covariant else "invariant"
                    incoming = "covariant" if is_covariant else "invariant"
                    raise TypeError(
                        f"Variance conflict at position {level} for hint {current_hint}: "
                        f"fixed as {fixed} by the first registration, "
                        f"but the new method declares it as {incoming}. "
                        f"Variance is fixed per (position, type) pair by the first registration."
                    )
                if level + 1 == len(method.signature):
                    n.method = method
                else:
                    DispatchTree._add(level + 1, n.children, method)
                return
        new_node = Node(current_hint, None, [], covariant=is_covariant)
        DispatchTree._add_node(nodes, new_node)
        if level + 1 == len(method.signature):
            new_node.method = method
        else:
            DispatchTree._add(level + 1, new_node.children, method)

    @staticmethod
    def _add_node(nodes: list[Node], new_node: Node) -> None:
        upper_bound = len(nodes)
        lower_bound = 0
        for i, n in enumerate(nodes):
            if DispatchTree._compare_hints(n, new_node) < 0:
                lower_bound = max(lower_bound, i + 1)
            elif DispatchTree._compare_hints(n, new_node) > 0:
                upper_bound = min(upper_bound, i)
        if lower_bound > upper_bound:
            raise TypeError("Types are not consistently ordered")  # pragma: no cover
        nodes.insert(lower_bound, new_node)

    @staticmethod
    def _compare_hints(left: Node, right: Node) -> int:
        if is_subtype_covariant(left.hint, right.hint):
            return -1
        if is_subtype_covariant(right.hint, left.hint):
            return 1
        return 0

    def match(self, types: Sequence[TypeForm]) -> list[Node]:
        if len(types) == 0:
            return [self.nullary] if self.nullary else []
        return DispatchTree._match(0, self.children, types)

    @staticmethod
    def _match(level: int, nodes: list[Node], arg_types: Sequence[TypeForm]) -> list[Node]:
        atype = arg_types[level]
        matches = []
        for n in nodes:
            if n.covariant:
                if not is_subtype_covariant(atype, n.hint):
                    continue
            else:
                if not is_subtype_invariant(atype, n.hint):
                    continue
            for i in range(len(matches)):
                m = matches[i]
                if is_subtype_covariant(m.hint, n.hint):
                    if is_subtype_covariant(n.hint, m.hint):
                        matches.append(n)
                    break
                if is_subtype_covariant(n.hint, m.hint):
                    matches[i] = n
                    break
            else:
                matches.append(n)
        if not matches:
            return []
        if level + 1 == len(arg_types):
            return matches
        next_nodes = [nn for n in matches for nn in n.children]
        return DispatchTree._match(level + 1, next_nodes, arg_types)

    def copy(self) -> "DispatchTree":
        tree = DispatchTree()
        tree.nullary = self.nullary
        tree.children = [n.copy() for n in self.children]
        return tree


class Multimethod:
    name: str
    tree: DispatchTree
    cache: dict[tuple[TypeForm, ...], Method]
    literal_interest: list[dict[tuple[type, Any], TypeForm] | None]

    def __init__(self, name: str, func: Callable | None = None):
        self.name = name
        self.tree = DispatchTree()
        self.cache: dict[tuple[TypeForm, ...], Method] = {}
        self.literal_interest: list[dict[tuple[type, Any], TypeForm] | None] = []
        if func:
            functools.update_wrapper(self, func)

    def register(self, func: Callable, covariant_args=frozenset()) -> Self:
        method = Method.from_func(func, covariant_args)
        self.cache.clear()
        self.tree.add(method)
        self._update_literal_interest(method)
        return self

    def _update_literal_interest(self, method: Method) -> None:
        for i, hint in enumerate(method.signature):
            values = list(_collect_top_level_literals(hint))
            if not values:
                continue
            if len(self.literal_interest) <= i:
                while len(self.literal_interest) < i:
                    self.literal_interest.append(None)
                self.literal_interest.append({})
            slot = self.literal_interest[i]
            if slot is None:
                slot = self.literal_interest[i] = {}
            for v in values:
                key = literal_key(v)
                if key not in slot:
                    slot[key] = cast(TypeForm, Literal[v])
            # Dirty micro-optimization: about 10% speed up for Literal-free cases.
            self.arg_type = self._arg_type_with_literal

    def dispatch(self, *arg_types) -> list[Method]:
        return [m.method for m in self.tree.match(arg_types) if m.method]

    def partial_dispatch(self, *arg_types) -> list[Method]:
        nodes = self.tree.match(arg_types)
        methods = []
        Multimethod._collect_method(nodes, methods)
        return methods

    @staticmethod
    def _collect_method(nodes: list[Node], acc: list[Method]) -> None:
        for n in nodes:
            if n.method is not None:
                acc.append(n.method)
            Multimethod._collect_method(n.children, acc)

    def arg_type(self, pos: int, arg: Any) -> TypeForm:
        atype = type(arg)
        if atype is str or atype is int or atype is float:  # Shortcut for frequent cases
            return atype
        if (
            (atype is GenericAlias)
            or (atype is _GenericAlias)
            or (atype is NewType)
            or (atype in TYPE_ALIAS_TYPES)
            or issubclass(atype, type)
        ):
            return type[arg]
        if orig_cls := getattr(arg, "__orig_class__", None):
            return orig_cls
        return atype

    def _arg_type_with_literal(self, pos: int, arg: Any) -> TypeForm:
        if (
            pos < len(self.literal_interest)
            and (slot := self.literal_interest[pos]) is not None
            and isinstance(arg, Hashable)
            and (lit_type := slot.get((type(arg), arg))) is not None
        ):
            return lit_type
        atype = type(arg)
        if atype is str or atype is int or atype is float:  # Shortcut for frequent cases
            return atype
        if (
            (atype is GenericAlias)
            or (atype is _GenericAlias)
            or (atype is NewType)
            or (atype in TYPE_ALIAS_TYPES)
            or issubclass(atype, type)
        ):
            return type[arg]
        if orig_cls := getattr(arg, "__orig_class__", None):
            return orig_cls
        return atype

    def __call__(self, *args, **kwargs):
        types = tuple(self.arg_type(i, a) for i, a in enumerate(args))
        if (method := self.cache.get(types)) is None:
            matched = [m.method for m in self.tree.match(types) if m.method]
            match len(matched):
                case 0:
                    raise NoMatchFound(types)
                case 1:
                    method = matched[0]
                    self.cache[types] = method
                case _:
                    raise MultipleMatchesFound(matched)
        return method(*args, **kwargs)  # type: ignore

    def copy(self) -> "Multimethod":
        mm = Multimethod(self.name)
        mm.tree = self.tree.copy()
        mm.literal_interest = [dict(s) if s is not None else None for s in self.literal_interest]
        if any(s is not None for s in mm.literal_interest):
            mm.arg_type = mm._arg_type_with_literal
        return mm


def _collect_top_level_literals(hint: TypeForm) -> Iterable[Any]:
    if is_union(hint):
        for member in get_args(hint):
            yield from _collect_top_level_literals(member)
        return
    origin, args = normalized_origin_args(hint)
    if origin is Literal:
        yield from args


class Dispatch:
    multimethods: dict[str, Multimethod]

    def __init__(self):
        self.multimethods = {}

    def covariant(self, *indices: int) -> Callable[..., Multimethod]:
        def decorator(func: Callable[..., Any]) -> Multimethod:
            return self(func, frozenset(indices))

        return decorator

    def __call__(self, func: Callable[..., Any], covariant_args: Iterable[int] = frozenset()) -> Multimethod:
        name = func.__name__
        if not (mm := self.get(name)):
            mm = Multimethod(name, func)
            self.multimethods[name] = mm
        mm.register(func, frozenset(covariant_args))
        return mm

    def __getitem__(self, key: str) -> Multimethod:
        return self.multimethods[key]

    def get(self, key: str, default=None) -> Multimethod | None:
        return self.multimethods.get(key, default)

    def items(self) -> ItemsView[str, Multimethod]:
        return self.multimethods.items()

    def copy(self) -> Self:
        dsp = type(self)()
        for k, v in self.items():
            dsp.multimethods[k] = v.copy()
        return dsp


dispatch = Dispatch()
