from dataclasses import Field as DclsField
from typing import TYPE_CHECKING, Any, Generic, Optional, TypeVar, get_args, get_origin

from ctxure._location import parse_path
from ctxure._typeutil import is_type, is_type_alias, resolve_type_alias

if TYPE_CHECKING:
    from ctxure._exetree import Site


_T = TypeVar("_T")

_R = TypeVar("_R")

_O = TypeVar("_O")

_P = TypeVar("_P")


class CtxImpl(Generic[_T, _R, _O, _P]):
    """
    _T: Structured type
    _R: Root type (top-level structured type of the conversion entry)
    _O: Owner type (parent's structured type), or None for the root ctx
    _P: Path. tuple[tuple[PathSeg, ...], PathSeg]
    """

    __slots__ = (
        "__orig_class__",
        "parent",
        "structured_type",
        "structured_key",
        "structured_path",
        "unstructured_path",
        "_site",
    )

    parent: Optional["CtxImpl"]
    structured_type: Any
    structured_path: str
    unstructured_path: str
    structured_key: Any
    _site: Optional["Site"]

    @classmethod
    def getcls(
        cls,
        structured_type: Any,
        root_type: Any,
        structured_owner_type: Any,
        structured_path: str | None,
    ) -> type:
        return cls[  # type: ignore[type-arg]
            structured_type,
            root_type,
            structured_owner_type,
            _parse_param(structured_path) if structured_path else Any,
        ]

    @classmethod
    def create(
        cls,
        parent: Optional["CtxImpl"],
        structured_type: Any,
        structured_path: str,
        unstructured_path: str,
        structured_key: Any,
        _site: Optional["Site"] = None,
    ) -> "CtxImpl":
        if is_type_alias(structured_type):
            structured_type = resolve_type_alias(structured_type)
        if parent is None:
            t_root_type = structured_type
            t_owner_type = None
        else:
            parent_args = get_args(parent.__orig_class__)
            t_owner_type = parent_args[0]
            t_root_type = parent_args[1]
        # Root type is `Any` in the middle of `(un)structure_by_type`.
        # In this case, path type parameter also should be Any.
        # However, the field `structured_path` should be preserved.
        t_structured_path = structured_path if t_root_type is not Any else None
        orig_class = cls.getcls(structured_type, t_root_type, t_owner_type, t_structured_path)
        return cls._build(
            orig_class,
            parent,
            structured_type,
            structured_path,
            unstructured_path,
            structured_key,
            _site,
        )

    @classmethod
    def _build(
        cls,
        orig_class: type,
        parent: Optional["CtxImpl"],
        structured_type: Any,
        structured_path: str,
        unstructured_path: str,
        structured_key: Any,
        _site: Optional["Site"],
    ) -> "CtxImpl":
        obj = cls.__new__(cls)
        obj.__orig_class__ = orig_class  # type: ignore[assignment]
        obj.parent = parent
        obj.structured_type = structured_type
        obj.structured_path = structured_path
        obj.unstructured_path = unstructured_path
        obj.structured_key = structured_key
        obj._site = _site
        return obj

    def __init__(
        self,
        parent: Optional["CtxImpl"],
        structured_type: Any,
        structured_path: str,
        unstructured_path: str,
        structured_key: Any,
        _site: Optional["Site"] = None,
    ):
        self.parent = parent
        self.structured_type = structured_type
        self.structured_path = structured_path
        self.structured_key = structured_key
        self.unstructured_path = unstructured_path
        self._site = _site

    def _replace_type(self, typ: Any) -> "CtxImpl":
        # Preserve current root and owner; only the structured type changes.
        # Bypassing create() because create() would re-derive root from `typ` when this is the root ctx.
        if is_type_alias(typ):
            typ = resolve_type_alias(typ)
        args = get_args(self.__orig_class__)
        t_root_type = args[1]
        t_owner_type = args[2]
        t_structured_path = None if args[3] is Any else self.structured_path
        orig_class = self.__class__.getcls(typ, t_root_type, t_owner_type, t_structured_path)
        return self.__class__._build(
            orig_class,
            self.parent,
            typ,
            self.structured_path,
            self.unstructured_path,
            self.structured_key,
            self._site,
        )

    def _strip(self) -> "CtxImpl":
        # Drop every contextual axis except target type from type parameters.
        # However, preserve inspectable information.
        cls = CtxImpl.getcls(self.structured_type, Any, Any, "?")
        return cls(
            self.parent,
            self.structured_type,
            self.structured_path,
            self.unstructured_path,
            self.structured_key,
            self._site,
        )

    @property
    def field(self) -> DclsField:
        return self.structured_key

    @property
    def index(self) -> int:
        return self.structured_key

    def __eq__(self, other):
        """
        This method is used only for testing — the ctxure runtime does not use equality.
        Structural equality: compares all fields except `_site` and also compares the parameterized type.
        `_site` is considered orthogonal to ctx identity; check it explicitly when needed.
        """

        if type(other) is not CtxImpl:
            return NotImplemented
        return all(
            [
                self.parent == other.parent,
                self.structured_type == other.structured_type,
                self.structured_path == other.structured_path,
                self.structured_key == other.structured_key,
                self.unstructured_path == other.unstructured_path,
                self.__orig_class__ == other.__orig_class__,
            ]
        )

    def __repr__(self) -> str:  # pragma: no cover # Only for test failures.
        args = get_args(self.__orig_class__)
        names = ("DeclaredType", "RootType", "OwnerType", "Path")
        type_params = ", ".join(f"{n}={_fmt_type(a)}" for n, a in zip(names, args))
        return (
            f"CtxImpl[{type_params}]("
            f"structured_type={self.structured_type}, "
            f"structured_path={self.structured_path!r}, "
            f"unstructured_path={self.unstructured_path!r}, "
            f"structured_key={self.structured_key!r}, "
            f"parent={self.parent!r})"
        )


def get_data(ctx: CtxImpl) -> Any:
    return ctx._site.data  # type: ignore


def get_extra(ctx: CtxImpl) -> Any:
    return ctx._site.root.extra  # type:ignore


def get_root(ctx: CtxImpl) -> CtxImpl:
    return ctx._site.root.ctx  # type: ignore


def get_parent(ctx: CtxImpl) -> CtxImpl | None:
    return ctx.parent


class Of(Generic[TypeVar("T")]): ...


class Under(Generic[TypeVar("T")]): ...


# `Ctx` is a user-facing type-level factory producing `CtxImpl` type and never instantiated.
# Here `Ctx` extends `CtxImpl` just to trick type checkers.
# Technically there is no reason to extend `CtxImpl`.
class Ctx(CtxImpl):
    def __class_getitem__(cls, param) -> type[CtxImpl]:
        structured_type = Any
        root = Any
        owner = Any
        path = Any

        if not isinstance(param, tuple):
            param = (param,)
        if len(param) > 4:
            raise TypeError("Too many parameters for Ctx")

        for p in param:
            if get_origin(p) is Of:
                if owner is not Any:
                    raise TypeError("Multiple `Of` constraints are not allowed")
                owner = get_args(p)[0]
                continue
            if get_origin(p) is Under:
                if root is not Any:
                    raise TypeError("Multiple `Under` constraints are not allowed")
                root = get_args(p)[0]
                continue
            if is_type(p) or p is Any:
                if structured_type is not Any:
                    raise TypeError("Multiple type constraints are not allowed")
                structured_type = p
                continue
            if isinstance(p, str):
                if path is not Any:
                    raise TypeError("Multiple location expressions are not allowed")
                path = _parse_param(p)
                continue
            raise TypeError(f"Invalid type parameter: {p}")

        if owner is not Any and path is not Any and get_args(path)[0] is not Any:
            raise TypeError("`Of` cannot be combined with a rooted path expression")

        return CtxImpl[structured_type, root, owner, path]


def _fmt_type(t: Any) -> str:  # pragma: no cover
    if t is Any:
        return "Any"
    if isinstance(t, type):
        return t.__qualname__
    return repr(t)


def _parse_param(param: str) -> Any:
    if param.isidentifier():
        raise TypeError(f"Forward references as strings are not supported; pass the type directly instead of '{param}'")
    else:
        pathsegs = parse_path(param)
        if pathsegs is Any:
            return Any
        if isinstance(pathsegs, tuple):
            return tuple[tuple[*pathsegs[:-1]], pathsegs[-1]]
        else:
            return tuple[Any, pathsegs]
