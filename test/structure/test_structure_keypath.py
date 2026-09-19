import copy
import pickle
from collections import OrderedDict
from dataclasses import InitVar, dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Generic, NotRequired, Required, TypedDict, TypeVar

import pytest
from typing_extensions import TypedDict as ExtTypedDict

from ctxure import (
    Ctx,
    ExtraFields,
    KeyPath,
    MissingFields,
    NoStructureHook,
    ValidationError,
    ctxure_config,
    structure,
    structure_default,
)
from ctxure.structure import DataClassExe, DataClassPathExe, TypedDictExe, TypedDictPathExe


# KeyPath type


def test_keypath_keys_and_repr():
    kp = KeyPath("profile", "name")
    assert kp.keys == ("profile", "name")
    assert repr(kp) == "KeyPath('profile', 'name')"


def test_keypath_needs_no_escaping():
    assert KeyPath("user.name").keys == ("user.name",)
    assert KeyPath(".tag", "foo bar", "이름").keys == (".tag", "foo bar", "이름")


def test_keypath_rejects_empty():
    with pytest.raises(ValueError, match="at least one key"):
        KeyPath()


@pytest.mark.parametrize("bad", [0, None, ("a",), b"a"])
def test_keypath_rejects_non_str(bad):
    with pytest.raises(TypeError, match="KeyPath keys must be str"):
        KeyPath("a", bad)


def test_keypath_accepts_str_enum():
    class K(StrEnum):
        A = "a"

    kp = KeyPath(K.A, "b")
    assert kp.keys == ("a", "b")
    assert all(type(k) is str for k in kp.keys)
    assert kp == KeyPath("a", "b")


def test_keypath_subclass_equality():
    class MyKeyPath(KeyPath):
        __slots__ = ()

    assert MyKeyPath("a", "b") == KeyPath("a", "b")
    assert KeyPath("a", "b") == MyKeyPath("a", "b")


def test_keypath_equality_and_hash():
    assert KeyPath("a", "b") == KeyPath("a", "b")
    assert KeyPath("a", "b") != KeyPath("b", "a")
    assert KeyPath("a") != ("a",)
    assert KeyPath("a") != "a"
    assert hash(KeyPath("a", "b")) == hash(KeyPath("a", "b"))
    assert len({KeyPath("a", "b"), KeyPath("a", "b")}) == 1


def test_keypath_is_immutable():
    kp = KeyPath("a")
    with pytest.raises(AttributeError):
        kp.keys = ("b",)  # type: ignore[misc]
    with pytest.raises(AttributeError):
        del kp.keys
    with pytest.raises(AttributeError):
        kp.other = 1  # type: ignore[attr-defined]
    assert kp.keys == ("a",)


def test_keypath_pickle_and_copy():
    kp = KeyPath("a", "b")
    assert pickle.loads(pickle.dumps(kp)) == kp
    assert copy.copy(kp) == kp
    assert copy.deepcopy(kp) == kp


# Structure: dataclass


@dataclass
class User:
    id: int
    name: str
    balance: float


USER_KEYMAP = {"name": KeyPath("profile", "name"), "balance": KeyPath("bank", "balance")}


def _register_user(testregister, keymap=USER_KEYMAP):
    @testregister
    def structure_hook(ctx: Ctx[User], data: dict) -> User:
        return structure_default(ctx, data, keymap=keymap)


def test_structure_keypath_reads_nested_values(testregister):
    _register_user(testregister)
    data = {
        "id": 32,
        "profile": {"name": "Smith, J", "age": 45, "address": "123 Main St"},
        "bank": {"acct": "43229349", "balance": 1343.33},
    }
    with ctxure_config(dispatcher=testregister):
        # Keys inside intermediates that no field reads are not checked.
        assert structure(User, data) == User(32, "Smith, J", 1343.33)


def test_structure_keypath_reports_top_level_extras(testregister):
    _register_user(testregister)
    data = {"id": 1, "profile": {"name": "a"}, "bank": {"balance": 1.0}, "junk": 1, "more": 2}
    with ctxure_config(dispatcher=testregister):
        with pytest.raises(ExtraFields) as e:
            structure(User, data)
    assert e.value.extra == ["junk", "more"]
    assert e.value.data is data
    assert e.value.ctx.structured_path == "$"


def test_structure_keypath_missing_at_each_depth(testregister):
    @dataclass
    class Deep:
        a: int
        b: int
        c: int

    keymap = {"b": KeyPath("x", "b"), "c": KeyPath("x", "y", "c")}

    @testregister
    def structure_hook(ctx: Ctx[Deep], data: dict) -> Deep:
        return structure_default(ctx, data, keymap=keymap)

    with ctxure_config(dispatcher=testregister):
        assert structure(Deep, {"a": 1, "x": {"b": 2, "y": {"c": 3}}}) == Deep(1, 2, 3)

        with pytest.raises(MissingFields) as e:
            structure(Deep, {"x": {"y": {}}})
        assert e.value.missing == ["a", "['x']['b']", "['x']['y']['c']"]

        data = {"a": 1}
        with pytest.raises(MissingFields) as e:
            structure(Deep, data)
        assert e.value.missing == ["['x']['b']", "['x']['y']['c']"]
        assert e.value.data is data

        with pytest.raises(MissingFields) as e:
            structure(Deep, {"a": 1, "x": {"b": 2}})
        assert e.value.missing == ["['x']['y']['c']"]


def test_structure_keypath_missing_uses_defaults(testregister):
    @dataclass
    class WithDefaults:
        a: int = 10
        b: list[int] = field(default_factory=lambda: [20])

    keymap = {"a": KeyPath("x", "a"), "b": KeyPath("x", "y", "b")}

    @testregister
    def structure_hook(ctx: Ctx[WithDefaults], data: dict) -> WithDefaults:
        return structure_default(ctx, data, keymap=keymap)

    with ctxure_config(dispatcher=testregister):
        assert structure(WithDefaults, {}) == WithDefaults(10, [20])
        assert structure(WithDefaults, {"x": {}}) == WithDefaults(10, [20])
        assert structure(WithDefaults, {"x": {"y": {"b": [1]}}}) == WithDefaults(10, [1])


@pytest.mark.parametrize("intermediate", [None, 1, "s", [1], ({"name": "a"},)])
def test_structure_keypath_non_dict_intermediate(testregister, intermediate):
    _register_user(testregister)
    data = {"id": 1, "profile": intermediate, "bank": {"balance": 1.0}}
    with ctxure_config(dispatcher=testregister):
        with pytest.raises(ValidationError) as e:
            structure(User, data)
    assert not isinstance(e.value, MissingFields)
    assert f"Expected a dict at ['profile'] to read ['profile']['name'], got {type(intermediate).__name__}" in str(
        e.value
    )
    assert e.value.ctx.structured_path == "$"
    assert e.value.data is data


def test_structure_keypath_non_dict_deeper_intermediate(testregister):
    @dataclass
    class Deep:
        c: int

    keymap = {"c": KeyPath("x", "y", "c")}

    @testregister
    def structure_hook(ctx: Ctx[Deep], data: dict) -> Deep:
        return structure_default(ctx, data, keymap=keymap)

    with ctxure_config(dispatcher=testregister):
        with pytest.raises(ValidationError, match=r"Expected a dict at \['x'\]\['y'\] to read"):
            structure(Deep, {"x": {"y": None}})


def test_structure_keypath_error_paths(testregister):
    _register_user(testregister)
    with ctxure_config(dispatcher=testregister):
        with pytest.raises(NoStructureHook) as e:
            structure(User, {"id": 1, "profile": {"name": 3}, "bank": {"balance": 1.0}})
    assert e.value.ctx.structured_path == "$.name"
    assert e.value.ctx.unstructured_path == "$['profile']['name']"
    assert e.value.ctx.structured_key.name == "name"
    assert e.value.ctx.parent is not None
    assert e.value.ctx.parent.structured_type is User


def test_structure_keypath_path_hooks_still_fire(testregister):
    _register_user(testregister)

    @testregister
    def structure_hook(ctx: Ctx[str, "$.name"], data: str) -> str:
        return data.upper()

    data = {"id": 1, "profile": {"name": "jack"}, "bank": {"balance": 1.0}}
    with ctxure_config(dispatcher=testregister):
        assert structure(User, data) == User(1, "JACK", 1.0)


def test_structure_keypath_nested_structured_value(testregister):
    @dataclass
    class Meta:
        id: int
        ts: str

    @dataclass
    class Event:
        meta: Meta
        kind: str

    keymap = {"meta": KeyPath("envelope", "meta"), "kind": KeyPath("envelope", "kind")}

    @testregister
    def structure_hook(ctx: Ctx[Event], data: dict) -> Event:
        return structure_default(ctx, data, keymap=keymap)

    data = {"envelope": {"meta": {"id": 1, "ts": "now"}, "kind": "click"}}
    with ctxure_config(dispatcher=testregister):
        assert structure(Event, data) == Event(Meta(1, "now"), "click")

        # The nested dataclass keeps its own extras policy.
        with pytest.raises(ExtraFields) as e:
            structure(Event, {"envelope": {"meta": {"id": 1, "ts": "now", "x": 0}, "kind": "click"}})
        assert e.value.ctx.structured_path == "$.meta"
        assert e.value.ctx.unstructured_path == "$['envelope']['meta']"


def test_structure_keypath_constructor_type_error(testregister):
    @dataclass
    class Strict:
        a: int

        def __post_init__(self) -> None:
            raise TypeError("rejected")

    keymap = {"a": KeyPath("x", "a")}

    @testregister
    def structure_hook(ctx: Ctx[Strict], data: dict) -> Strict:
        return structure_default(ctx, data, keymap=keymap)

    data = {"x": {"a": 1}}
    with ctxure_config(dispatcher=testregister):
        with pytest.raises(NoStructureHook) as e:
            structure(Strict, data)
    assert e.value.ctx.structured_type is Strict
    assert e.value.data is data
    assert isinstance(e.value.__cause__, TypeError)


def test_structure_keypath_overlapping_reads(testregister):
    @dataclass
    class Req:
        meta: dict[str, int]
        request_id: int

    keymap = {"request_id": KeyPath("meta", "id")}

    @testregister
    def structure_hook(ctx: Ctx[Req], data: dict) -> Req:
        return structure_default(ctx, data, keymap=keymap)

    with ctxure_config(dispatcher=testregister):
        assert structure(Req, {"meta": {"id": 5, "n": 1}}) == Req({"id": 5, "n": 1}, 5)


def test_structure_keypath_mixed_with_plain_aliases(testregister):
    @dataclass
    class Mixed:
        a: int
        b: int
        c: int

    keymap = {"b": "B", "c": KeyPath("x", "c")}

    @testregister
    def structure_hook(ctx: Ctx[Mixed], data: dict) -> Mixed:
        return structure_default(ctx, data, keymap=keymap)

    with ctxure_config(dispatcher=testregister):
        assert structure(Mixed, {"a": 1, "B": 2, "x": {"c": 3}}) == Mixed(1, 2, 3)

        with pytest.raises(MissingFields) as e:
            structure(Mixed, {"a": 1})
        assert e.value.missing == ["B", "['x']['c']"]

        with pytest.raises(ExtraFields) as e:
            structure(Mixed, {"a": 1, "B": 2, "b": 0, "x": {"c": 3}})
        assert e.value.extra == ["b"]


def test_structure_keymap_duplicate_aliases_report_extras(testregister):
    # Two fields reading one key used to hide a single stray key (the fast Exe's
    # `len(args) < len(data)` shortcut). Duplicates now go to the path Exe.
    @dataclass
    class A:
        a: int
        b: int

    keymap = {"a": "x", "b": "x"}

    @testregister
    def structure_hook(ctx: Ctx[A], data: dict) -> A:
        return structure_default(ctx, data, keymap=keymap)

    with ctxure_config(dispatcher=testregister):
        assert structure(A, {"x": 1}) == A(1, 1)

        with pytest.raises(ExtraFields) as e:
            structure(A, {"x": 1, "stray": 2})
        assert e.value.extra == ["stray"]

        with pytest.raises(MissingFields) as e:
            structure(A, {})
        assert e.value.missing == ["x", "x"]

    exe_holder = testregister.structure_cache.get(A).exe
    assert type(exe_holder.default_exe) is DataClassPathExe


def test_structure_keymap_alias_equal_to_other_field_name(testregister):
    @dataclass
    class C:
        a: int
        b: int

    keymap = {"a": "b"}

    @testregister
    def structure_hook(ctx: Ctx[C], data: dict) -> C:
        return structure_default(ctx, data, keymap=keymap)

    with ctxure_config(dispatcher=testregister):
        with pytest.raises(ExtraFields) as e:
            structure(C, {"b": 1, "stray": 2})
        assert e.value.extra == ["stray"]


def test_structure_single_key_keypath_is_plain_alias(testregister):
    @dataclass
    class A:
        a: int
        b: int

    keymap = {"b": KeyPath("B")}

    @testregister
    def structure_hook(ctx: Ctx[A], data: dict) -> A:
        return structure_default(ctx, data, keymap=keymap)

    with ctxure_config(dispatcher=testregister):
        assert structure(A, {"a": 1, "B": 2}) == A(1, 2)
        with pytest.raises(MissingFields) as e:
            structure(A, {"a": 1})
        assert e.value.missing == ["B"]

    exe_holder = testregister.structure_cache.get(A).exe
    assert type(exe_holder.default_exe) is DataClassExe


def test_structure_keymap_ignores_entries_for_other_types(testregister):
    # One keymap constant shared by several types: a multi-key path for a field
    # this type does not have neither applies nor selects the path Exe.
    @dataclass
    class A:
        a: int

    keymap = {"a": "A", "other": KeyPath("x", "y")}

    @testregister
    def structure_hook(ctx: Ctx[A], data: dict) -> A:
        return structure_default(ctx, data, keymap=keymap)

    with ctxure_config(dispatcher=testregister):
        assert structure(A, {"A": 1}) == A(1)

    exe_holder = testregister.structure_cache.get(A).exe
    assert type(exe_holder.default_exe) is DataClassExe


@pytest.mark.parametrize("bad", [("x", "b"), 0, None, ["x"]])
def test_structure_keymap_rejects_invalid_values(testregister, bad):
    @dataclass
    class A:
        a: int
        b: int

    keymap = {"b": bad}

    @testregister
    def structure_hook(ctx: Ctx[A], data: dict) -> A:
        return structure_default(ctx, data, keymap=keymap)

    with ctxure_config(dispatcher=testregister):
        with pytest.raises(ValidationError, match="keymap value for 'b' must be str or KeyPath"):
            structure(A, {"a": 1, "x": {"b": 2}})


def test_structure_keymap_accepts_any_mapping(testregister):
    keymap = MappingProxyType({"name": KeyPath("profile", "name"), "balance": KeyPath("bank", "balance")})
    _register_user(testregister, keymap)
    with ctxure_config(dispatcher=testregister):
        assert structure(User, {"id": 1, "profile": {"name": "a"}, "bank": {"balance": 1.0}}) == User(1, "a", 1.0)


# Structure: TypedDict


class Account(TypedDict):
    id: int
    name: str
    nickname: NotRequired[str]


ACCOUNT_KEYMAP = {"name": KeyPath("profile", "name"), "nickname": KeyPath("profile", "nick")}


def _register_account(testregister, td: Any = Account):
    @testregister
    def structure_hook(ctx: Ctx[td], data: dict) -> Any:
        return structure_default(ctx, data, keymap=ACCOUNT_KEYMAP)


def test_structure_keypath_typeddict(testregister):
    _register_account(testregister)
    with ctxure_config(dispatcher=testregister):
        assert structure(Account, {"id": 1, "profile": {"name": "a", "nick": "b", "age": 3}}) == {
            "id": 1,
            "name": "a",
            "nickname": "b",
        }
        # NotRequired and missing: the key is absent.
        assert structure(Account, {"id": 1, "profile": {"name": "a"}}) == {"id": 1, "name": "a"}
        # A lax TypedDict drops top-level extras, as without KeyPath.
        assert structure(Account, {"id": 1, "profile": {"name": "a"}, "junk": 0}) == {"id": 1, "name": "a"}

        with pytest.raises(MissingFields) as e:
            structure(Account, {"profile": {}})
        assert e.value.missing == ["id", "['profile']['name']"]

        with pytest.raises(ValidationError, match=r"Expected a dict at \['profile'\]"):
            structure(Account, {"id": 1, "profile": None})

        with pytest.raises(NoStructureHook) as e:
            structure(Account, {"id": 1, "profile": {"name": 3}})
        assert e.value.ctx.structured_path == "$.name"
        assert e.value.ctx.unstructured_path == "$['profile']['name']"
        assert e.value.ctx.structured_key == "name"
        assert e.value.ctx.parent is not None
        assert e.value.ctx.parent.structured_type is Account

    exe_holder = testregister.structure_cache.get(Account).exe
    assert type(exe_holder.default_exe) is TypedDictPathExe


def test_structure_keypath_closed_typeddict(testregister):
    class ClosedAccount(ExtTypedDict, closed=True):  # type: ignore[call-arg]
        id: int
        name: str
        nickname: NotRequired[str]

    _register_account(testregister, ClosedAccount)
    with ctxure_config(dispatcher=testregister):
        # Keys inside intermediates are not checked, even when closed.
        assert structure(ClosedAccount, {"id": 1, "profile": {"name": "a", "age": 3}}) == {"id": 1, "name": "a"}

        with pytest.raises(ExtraFields) as e:
            structure(ClosedAccount, {"id": 1, "profile": {"name": "a"}, "junk": 0})
        assert e.value.extra == ["junk"]


def test_structure_keypath_typeddict_extra_items(testregister):
    class OpenAccount(ExtTypedDict, extra_items=int):  # type: ignore[call-arg]
        id: int
        name: str

    _register_account(testregister, OpenAccount)
    with ctxure_config(dispatcher=testregister):
        # The path head `profile` is consumed, so it is not collected as an extra item.
        assert structure(OpenAccount, {"id": 1, "profile": {"name": "a", "age": 3}, "score": 7}) == {
            "id": 1,
            "name": "a",
            "score": 7,
        }


def test_structure_single_key_keypath_typeddict_uses_fast_exe(testregister):
    class T(TypedDict):
        a: int

    keymap = {"a": KeyPath("A")}

    @testregister
    def structure_hook(ctx: Ctx[T], data: dict) -> T:
        return structure_default(ctx, data, keymap=keymap)

    with ctxure_config(dispatcher=testregister):
        assert structure(T, {"A": 1}) == {"a": 1}

    exe_holder = testregister.structure_cache.get(T).exe
    assert type(exe_holder.default_exe) is TypedDictExe


# Edge cases


def test_structure_keypath_str_enum_keys(testregister):
    class K(StrEnum):
        PROFILE = "profile"

    @dataclass
    class A:
        name: str

    keymap = {"name": KeyPath(K.PROFILE, "name")}

    @testregister
    def structure_hook(ctx: Ctx[A], data: dict) -> A:
        return structure_default(ctx, data, keymap=keymap)

    with ctxure_config(dispatcher=testregister):
        assert structure(A, {"profile": {"name": "a"}}) == A("a")

        with pytest.raises(MissingFields) as e:
            structure(A, {"profile": {}})
        assert e.value.missing == ["['profile']['name']"]

        with pytest.raises(NoStructureHook) as e:
            structure(A, {"profile": {"name": 1}})
        assert e.value.ctx.unstructured_path == "$['profile']['name']"


def test_structure_keypath_generic_dataclass(testregister):
    T = TypeVar("T")

    @dataclass
    class Box(Generic[T]):
        value: T
        label: str

    keymap = {"value": KeyPath("payload", "value")}

    @testregister
    def structure_hook(ctx: Ctx[Box[int]], data: dict) -> Box[int]:
        return structure_default(ctx, data, keymap=keymap)

    with ctxure_config(dispatcher=testregister):
        assert structure(Box[int], {"payload": {"value": 1}, "label": "x"}) == Box(1, "x")

        with pytest.raises(NoStructureHook) as e:
            structure(Box[int], {"payload": {"value": "1"}, "label": "x"})
        assert e.value.ctx.structured_type is int
        assert e.value.ctx.unstructured_path == "$['payload']['value']"


def test_structure_keypath_initvar_and_init_false(testregister):
    @dataclass
    class Scaled:
        raw: InitVar[int]
        scaled: int = field(init=False)

        def __post_init__(self, raw: int) -> None:
            self.scaled = raw * 10

    keymap = {"raw": KeyPath("input", "raw")}

    @testregister
    def structure_hook(ctx: Ctx[Scaled], data: dict) -> Scaled:
        return structure_default(ctx, data, keymap=keymap)

    with ctxure_config(dispatcher=testregister):
        assert structure(Scaled, {"input": {"raw": 3}}).scaled == 30

        # An init=False field is not an input, as without KeyPath.
        with pytest.raises(ExtraFields) as e:
            structure(Scaled, {"input": {"raw": 3}, "scaled": 0})
        assert e.value.extra == ["scaled"]


def test_structure_keypath_typeddict_inheritance_and_totality(testregister):
    class Base(TypedDict, total=False):
        a: Required[int]
        b: int

    class Child(Base):
        c: int
        d: NotRequired[int]

    keymap = {"a": KeyPath("x", "a"), "b": KeyPath("x", "b"), "c": KeyPath("y", "c"), "d": KeyPath("y", "d")}

    @testregister
    def structure_hook(ctx: Ctx[Child], data: dict) -> Child:
        return structure_default(ctx, data, keymap=keymap)

    with ctxure_config(dispatcher=testregister):
        assert structure(Child, {"x": {"a": 1, "b": 2}, "y": {"c": 3, "d": 4}}) == {"a": 1, "b": 2, "c": 3, "d": 4}
        assert structure(Child, {"x": {"a": 1}, "y": {"c": 3}}) == {"a": 1, "c": 3}

        with pytest.raises(MissingFields) as e:
            structure(Child, {"x": {"b": 2}, "y": {"d": 4}})
        assert e.value.missing == ["['x']['a']", "['y']['c']"]


def test_structure_keypath_dict_subclass_intermediate(testregister):
    _register_user(testregister)
    data = OrderedDict(id=1, profile=OrderedDict(name="a"), bank=OrderedDict(balance=1.0))
    with ctxure_config(dispatcher=testregister):
        assert structure(User, data) == User(1, "a", 1.0)


def test_structure_keymap_duplicate_aliases_typeddict(testregister):
    class T(TypedDict):
        a: int
        b: int

    keymap = {"a": "x", "b": "x"}

    @testregister
    def structure_hook(ctx: Ctx[T], data: dict) -> T:
        return structure_default(ctx, data, keymap=keymap)

    with ctxure_config(dispatcher=testregister):
        assert structure(T, {"x": 1, "stray": 2}) == {"a": 1, "b": 1}

        with pytest.raises(MissingFields) as e:
            structure(T, {})
        assert e.value.missing == ["x", "x"]

    exe_holder = testregister.structure_cache.get(T).exe
    assert type(exe_holder.default_exe) is TypedDictPathExe


def test_structure_keypath_typeddict_extra_key_conflicts_with_field(testregister):
    class OpenAccount(ExtTypedDict, extra_items=int):  # type: ignore[call-arg]
        id: int
        name: str

    _register_account(testregister, OpenAccount)
    with ctxure_config(dispatcher=testregister):
        # `name` is read from ['profile']['name'], so a top-level `name` is an extra key
        # that collides with the declared field.
        data = {"id": 1, "profile": {"name": "a"}, "name": 5}
        with pytest.raises(ValidationError, match="TypedDict extra key conflicts with declared field: 'name'") as e:
            structure(OpenAccount, data)
        assert e.value.data is data


def test_structure_empty_keymap(testregister):
    @dataclass
    class A:
        a: int

    keymap: dict[str, str | KeyPath] = {}

    @testregister
    def structure_hook(ctx: Ctx[A], data: dict) -> A:
        return structure_default(ctx, data, keymap=keymap)

    with ctxure_config(dispatcher=testregister):
        assert structure(A, {"a": 1}) == A(1)

    exe_holder = testregister.structure_cache.get(A).exe
    assert type(exe_holder.default_exe) is DataClassExe


def test_structure_keypath_error_order(testregister):
    # Fields are read in declaration order and the first failure is reported.
    # A missing required field reports every missing required field; lookups for
    # optional fields are not checked then.
    @dataclass
    class M:
        a: int
        b: int = 0

    keymap = {"a": KeyPath("p", "a"), "b": KeyPath("q", "b")}

    @testregister
    def structure_hook(ctx: Ctx[M], data: dict) -> M:
        return structure_default(ctx, data, keymap=keymap)

    with ctxure_config(dispatcher=testregister):
        with pytest.raises(MissingFields) as e:
            structure(M, {"q": 1})
        assert e.value.missing == ["['p']['a']"]

        with pytest.raises(ValidationError, match=r"Expected a dict at \['q'\]"):
            structure(M, {"p": {"a": 1}, "q": 1})

    @dataclass
    class N:
        a: int
        b: int

    @testregister
    def structure_hook(ctx: Ctx[N], data: dict) -> N:
        return structure_default(ctx, data, keymap=keymap)

    with ctxure_config(dispatcher=testregister):
        # With both required, collecting the missing fields reaches `b`'s bad intermediate.
        with pytest.raises(ValidationError, match=r"Expected a dict at \['q'\]") as e:
            structure(N, {"q": 1})
        assert not isinstance(e.value, MissingFields)
