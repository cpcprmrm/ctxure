from collections.abc import Callable
from dataclasses import MISSING, dataclass
from typing import Any, Literal, Sequence, get_args, get_origin

from typing_extensions import is_typeddict

from ctxure._typeutil import (
    is_union,
    literal_values_contain,
    normalize_type,
    normalized_origin_args,
    resolve_input_field_types,
    resolve_typeddict_field_types,
)
from ctxure.context import CtxImpl
from ctxure.multidispatch import LiteralBase, Multimethod, NewTypeBase


@dataclass
class Decision:
    typ: Any


@dataclass
class NoMatch:
    pass


@dataclass
class Split:
    field: str
    positive: "Node"
    negative: "Node"


@dataclass
class TagSplit:
    field: str
    branches: "list[tuple[Any, Node]]"


Node = Split | TagSplit | Decision | NoMatch


@dataclass
class _DclsInfo:
    typ: Any
    all_fields: frozenset[str]
    required_fields: frozenset[str]
    tag_values: dict[str, Any]


_NO_MATCH = NoMatch()
_MISSING = object()


def generate_decision_func(clses: list[Any]) -> Callable[[dict], Any] | None:
    """
    `clses` should be dataclasses or TypedDicts.
    The generated function takes a dict and returns the type of the candidate that matches the fields in the dict, or None if no match is found.
    A candidate matches iff its required fields are present and no field declared by another candidate (but not by this one) is present in the input.
    Fields outside the union universe (declared by no candidate) are tolerated and left for the caller to validate.
    Fields declared as `Literal[<single_value>]` whose values are pairwise distinct across candidates are used as tagged-union discriminators (whether or not the field is required on the Python side; the dict must carry the tag to dispatch).
    """

    infos = _compute_infos(clses)
    tree = _build_from_infos(infos)
    if tree is None:
        return None

    universe = frozenset().union(*(info.all_fields for info in infos))

    type_map = {f"_t{i}": dc for i, dc in enumerate(clses)}
    excl_map = {f"_e{i}": frozenset(universe - info.all_fields) for i, info in enumerate(infos)}
    typ_to_idx = {id(dc): i for i, dc in enumerate(clses)}

    lines: list[str] = []
    extra_globals: dict[str, Any] = {}
    counter = [0]

    def fresh() -> int:
        counter[0] += 1
        return counter[0]

    def emit(node: Node, indent: int):
        prefix = "    " * indent
        if isinstance(node, NoMatch):
            lines.append(f"{prefix}return None")
        elif isinstance(node, Decision):
            i = typ_to_idx[id(node.typ)]
            if excl_map[f"_e{i}"]:
                lines.append(f"{prefix}if data.keys().isdisjoint(_e{i}):")
                lines.append(f"{prefix}    return _t{i}")
                lines.append(f"{prefix}return None")
            else:
                lines.append(f"{prefix}return _t{i}")
        elif isinstance(node, TagSplit):
            n = fresh()
            var = f"_v{n}"
            type_var = f"_ty{n}"
            lines.append(f"{prefix}{var} = data.get({node.field!r}, _MISSING)")
            lines.append(f"{prefix}if {var} is not _MISSING:")
            lines.append(f"{prefix}    {type_var} = type({var})")
            first = True
            for v, sub in node.branches:
                bn = fresh()
                lit_name = f"_lit{bn}"
                type_name = f"_T{bn}"
                extra_globals[lit_name] = v
                extra_globals[type_name] = type(v)
                kw = "if" if first else "elif"
                lines.append(f"{prefix}    {kw} {type_var} is {type_name} and {var} == {lit_name}:")
                emit(sub, indent + 2)
                first = False
            lines.append(f"{prefix}return None")
        else:
            lines.append(f"{prefix}if {node.field!r} in data:")
            emit(node.positive, indent + 1)
            lines.append(f"{prefix}else:")
            emit(node.negative, indent + 1)

    lines.append("def decide(data):")
    emit(tree, 1)

    code = "\n".join(lines)
    globs = {**type_map, **excl_map, **extra_globals, "_MISSING": _MISSING}
    exec(code, globs)
    return globs["decide"]


def _compute_infos(clses: list[Any]) -> list[_DclsInfo]:
    infos = []
    for dc in clses:
        origin = get_origin(dc) or dc
        if is_typeddict(origin):
            entries = resolve_typeddict_field_types(dc)
            all_f = frozenset(name for name, _ in entries)
            req_f = frozenset(getattr(origin, "__required_keys__", all_f))
            hint_by_name: dict[str, Any] = dict(entries)
        else:
            entries_dc = resolve_input_field_types(dc)
            all_f = frozenset(f.name for f, _ in entries_dc)
            req_f = frozenset(f.name for f, _ in entries_dc if f.default is MISSING and f.default_factory is MISSING)
            hint_by_name = {f.name: t for f, t in entries_dc}
        tag_values: dict[str, Any] = {}
        for name, t in hint_by_name.items():
            origin, args = normalized_origin_args(t)
            if origin is Literal:
                if len(args) == 1:
                    tag_values[name] = args[0]
        infos.append(_DclsInfo(dc, all_f, req_f, tag_values))
    return infos


def build_decision_tree(clses: list[Any]) -> Node | None:
    """
    If it is impossible to discriminate all candidates, this returns None.
    """

    return _build_from_infos(_compute_infos(clses))


def _build_from_infos(infos: list[_DclsInfo]) -> Node | None:
    all_field_names: set[str] = set()
    for info in infos:
        all_field_names |= info.all_fields
    return _split(all_field_names, infos)


def _split(fields: set[str], candidates: list[_DclsInfo]) -> Node | None:
    seen = set()
    unique = []
    for c in candidates:
        if id(c) not in seen:
            seen.add(id(c))
            unique.append(c)
    candidates = unique

    if len(candidates) == 1:
        info = candidates[0]
        unchecked_required = info.required_fields & fields
        return _validate_required(info, unchecked_required)

    tagged = _try_tag_split(fields, candidates)
    if tagged is not None:
        return tagged

    if not fields:
        return None

    best = None
    best_score = None

    for n in sorted(fields):
        positive = [c for c in candidates if n in c.all_fields]
        negative = [c for c in candidates if n not in c.required_fields]

        if len(positive) == len(candidates) and len(negative) == len(candidates):
            continue

        if not positive or not negative:
            continue

        priority = 1
        if len(positive) > 1 and all(n in c.tag_values for c in positive):
            tag_vals = [c.tag_values[n] for c in positive]
            keys = [(type(v), v) for v in tag_vals]
            if len(set(keys)) == len(keys):
                priority = 0

        score = (priority, max(len(positive), len(negative)))
        if best_score is None or score < best_score:
            best = (n, positive, negative)
            best_score = score

    if best is None:
        return None

    field_name, positive, negative = best
    remaining = fields - {field_name}

    positive_result = _split(remaining, positive)
    negative_result = _split(remaining, negative)
    if positive_result is None or negative_result is None:
        return None

    return Split(field_name, positive_result, negative_result)


def _try_tag_split(fields: set[str], candidates: list[_DclsInfo]) -> TagSplit | None:
    common = set(candidates[0].tag_values)
    for c in candidates[1:]:
        common &= set(c.tag_values)
        if not common:
            return None

    for f in sorted(common):
        values = [c.tag_values[f] for c in candidates]
        typed_keys = [(type(v), v) for v in values]
        if len(set(typed_keys)) != len(typed_keys):
            continue
        remaining = fields - {f}
        branches: list[tuple[Any, Node]] = []
        for c, v in zip(candidates, values):
            # Single-candidate _split always returns Split | Decision via _validate_required.
            sub = _split(remaining, [c])
            assert sub is not None
            branches.append((v, sub))
        return TagSplit(f, branches)
    return None


def _validate_required(info: _DclsInfo, unchecked: frozenset[str]) -> Split | Decision:
    """
    Build a linear chain of splits that checks each remaining required field is present.
    """

    if not unchecked:
        return Decision(info.typ)

    field = next(iter(unchecked))
    remaining = unchecked - {field}
    return Split(
        field,
        positive=_validate_required(info, remaining),
        negative=_NO_MATCH,
    )


def select_union_candidate(probed: list[tuple[Any, bool]], dtype: Any) -> list[Any]:
    hook_matches = [c for c, is_hook in probed if is_hook]
    if hook_matches:
        return hook_matches

    all_candidates = [c for c, _ in probed]

    identity_matches = [c for c in all_candidates if c == dtype]
    if identity_matches:
        return identity_matches

    return all_candidates


def probe_union_candidates(
    hook: Multimethod | None,
    default: Multimethod,
    candidates: Sequence,
    ctx: CtxImpl,
    data: Any,
    *,
    validate_literal_membership_for_hooks: bool = False,
) -> list | None:
    matches = []
    default_dtype = default.arg_type(1, data)
    for c in candidates:
        c = normalize_type(c)
        if is_union(c):
            sub_matches = probe_union_candidates(
                hook,
                default,
                get_args(c),
                ctx,
                data,
                validate_literal_membership_for_hooks=validate_literal_membership_for_hooks,
            )
            if sub_matches is None:
                return None
            matches.extend(sub_matches)
            continue
        new_ctx = ctx._replace_type(c)
        new_ctx_type = new_ctx.__orig_class__  # type: ignore
        is_hook = True
        if hook is not None:
            dispatched = hook.dispatch(new_ctx_type, hook.arg_type(1, data))
            match len(dispatched):
                case 0:
                    method = None
                case 1:
                    method = dispatched[0]
                    # Hooks without target type should not participate in probing.
                    if get_args(method.signature[0])[0] is Any:
                        method = None
                    elif validate_literal_membership_for_hooks:
                        origin, args = normalized_origin_args(c)
                        if origin is Literal and not literal_values_contain(args, data):
                            method = None
                case _:
                    return None
        else:
            method = None
        if method is None:
            is_hook = False
            dispatched = default.dispatch(new_ctx_type, default_dtype)
            match len(dispatched):
                case 0:
                    method = None
                case 1:
                    # NewType and Literal cannot be probed purely by existence of handlers.
                    handler_target = get_args(dispatched[0].signature[0])[0]
                    if handler_target is NewTypeBase:
                        supertype_ctx_type = ctx._replace_type(c.__supertype__).__orig_class__
                        dispatched = default.dispatch(supertype_ctx_type, default_dtype)
                        match len(dispatched):
                            case 0:
                                method = None
                            case 1:
                                method = dispatched[0]
                            case _:  # pragma: no cover
                                raise AssertionError("Bug: unreachable")
                    elif handler_target is LiteralBase:
                        if literal_values_contain(get_args(c), data):
                            method = dispatched[0]
                        else:
                            method = None
                    else:
                        method = dispatched[0]
                case _:  # pragma: no cover
                    raise AssertionError("Bug: unreachable")
        if method is None:
            continue
        else:
            matches.append((c, is_hook))
    seen: dict[Any, bool] = {}
    for c, is_hook in matches:
        if c not in seen or (is_hook and not seen[c]):
            seen[c] = is_hook
    return list(seen.items())
