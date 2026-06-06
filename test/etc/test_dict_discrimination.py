from dataclasses import InitVar, dataclass, field
from enum import Enum, IntEnum
from typing import Annotated, Generic, Literal, TypeVar

from typing_extensions import NotRequired, Required, TypedDict

from ctxure._unionutil import Decision, NoMatch, Split, TagSplit, build_decision_tree, generate_decision_func


def test_dataclass_single_type():
    @dataclass
    class Foo:
        a: int

    tree = build_decision_tree([Foo])
    assert isinstance(tree, Split)
    assert isinstance(tree.positive, Decision)
    assert tree.positive.typ is Foo
    assert isinstance(tree.negative, NoMatch)

    decide = generate_decision_func([Foo])
    assert decide is not None
    assert decide({"a": 1}) is Foo
    assert decide({"b": 1}) is None


def test_dataclass_two_types_distinct_required_fields():
    @dataclass
    class Foo:
        a: int
        b: int

    @dataclass
    class Bar:
        a: int
        c: int

    decide = generate_decision_func([Foo, Bar])
    assert decide is not None
    assert decide({"a": 1, "b": 2}) is Foo
    assert decide({"a": 1, "c": 3}) is Bar


def test_dataclass_three_types_distinct_required_fields():
    @dataclass
    class Foo:
        a: int
        b: int

    @dataclass
    class Bar:
        a: int
        c: int

    @dataclass
    class Baz:
        a: int
        d: int

    decide = generate_decision_func([Foo, Bar, Baz])
    assert decide is not None
    assert decide({"a": 1, "b": 2}) is Foo
    assert decide({"a": 1, "c": 3}) is Bar
    assert decide({"a": 1, "d": 4}) is Baz


def test_dataclass_no_shared_fields():
    @dataclass
    class Foo:
        a: int

    @dataclass
    class Bar:
        b: int

    decide = generate_decision_func([Foo, Bar])
    assert decide is not None
    assert decide({"a": 1}) is Foo
    assert decide({"b": 2}) is Bar
    assert decide({"a": 1, "b": 2}) is None


def test_dataclass_identical_fields_returns_none():
    @dataclass
    class Foo:
        a: int

    @dataclass
    class Bar:
        a: int

    assert build_decision_tree([Foo, Bar]) is None
    assert generate_decision_func([Foo, Bar]) is None


def test_dataclass_optional_field_positive_signal():
    @dataclass
    class Foo:
        a: int
        b: int = 0

    @dataclass
    class Bar:
        a: int
        c: int

    decide = generate_decision_func([Foo, Bar])
    assert decide is not None
    assert decide({"a": 1, "b": 2}) is Foo
    assert decide({"a": 1, "c": 3}) is Bar


def test_dataclass_discriminator_uses_init_fields():
    @dataclass
    class Foo:
        tag: InitVar[Literal["foo"]]
        a: int

    @dataclass
    class Bar:
        b: int
        computed: int = field(init=False)

    decide = generate_decision_func([Foo, Bar])
    assert decide is not None
    assert decide({"tag": "foo", "a": 1}) is Foo
    assert decide({"b": 1}) is Bar
    assert decide({"computed": 1}) is None


def test_dataclass_both_optional_unique_fields():
    @dataclass
    class Foo:
        a: int
        b: int
        c: int = 0

    @dataclass
    class Bar:
        a: int
        d: int
        e: int = 0

    decide = generate_decision_func([Foo, Bar])
    assert decide is not None
    assert decide({"a": 1, "b": 2}) is Foo
    assert decide({"a": 1, "b": 2, "c": 3}) is Foo
    assert decide({"a": 1, "d": 4}) is Bar
    assert decide({"a": 1, "d": 4, "e": 5}) is Bar


def test_dataclass_only_optional_unique_fields_indistinguishable():
    @dataclass
    class Foo:
        a: int
        b: int = 0

    @dataclass
    class Bar:
        a: int
        c: int = 0

    assert generate_decision_func([Foo, Bar]) is None


def test_dataclass_optional_field_with_default_factory():
    @dataclass
    class Foo:
        a: int
        b: list = field(default_factory=list)

    @dataclass
    class Bar:
        a: int
        c: int

    decide = generate_decision_func([Foo, Bar])
    assert decide is not None
    assert decide({"a": 1, "b": []}) is Foo
    assert decide({"a": 1, "c": 3}) is Bar


def test_dataclass_parameterized_generic():
    T = TypeVar("T")

    @dataclass
    class Foo(Generic[T]):
        a: T

    @dataclass
    class Bar(Generic[T]):
        b: T

    decide = generate_decision_func([Foo[int], Bar[str]])
    assert decide is not None
    assert decide({"a": 1}) is Foo[int]
    assert decide({"b": "x"}) is Bar[str]

    decide = generate_decision_func([Foo[int], Foo[str]])
    assert decide is None


def test_dataclass_parameterized_generic_with_shared_field():
    T = TypeVar("T")

    @dataclass
    class Foo(Generic[T]):
        a: T
        b: int

    @dataclass
    class Bar(Generic[T]):
        a: T
        c: int

    decide = generate_decision_func([Foo[int], Bar[int]])
    assert decide is not None
    assert decide({"a": 1, "b": 2}) is Foo[int]
    assert decide({"a": 1, "c": 3}) is Bar[int]


def test_dataclass_subset_fields_required():
    @dataclass
    class Foo:
        a: int
        b: int

    @dataclass
    class Bar:
        a: int

    decide = generate_decision_func([Foo, Bar])
    assert decide is not None
    assert decide({"a": 1, "b": 2}) is Foo
    assert decide({"a": 1}) is Bar


def test_dataclass_inherited_fields_required():
    @dataclass
    class Foo:
        a: int

    @dataclass
    class Bar(Foo):
        b: int

    decide = generate_decision_func([Foo, Bar])
    assert decide is not None
    assert decide({"a": 1, "b": 2}) is Bar
    assert decide({"a": 1}) is Foo


def test_dataclass_disjoint_required_same_all_fields():
    @dataclass
    class Foo:
        a: int
        b: int = 0

    @dataclass
    class Bar:
        b: int
        a: int = 0

    # {"a": 1, "b": 2} satisfies both, cannot discriminate.
    assert generate_decision_func([Foo, Bar]) is None


def test_dataclass_subset_fields_all_optional_indistinguishable():
    @dataclass
    class Foo:
        a: int
        b: int = 0
        c: int = 0

    @dataclass
    class Bar:
        a: int
        b: int = 0

    # {"a": 1} and {"a": 1, "b": 2} are valid for both
    assert generate_decision_func([Foo, Bar]) is None


def test_dataclass_many_types():
    @dataclass
    class Foo:
        a: int

    @dataclass
    class Bar:
        b: int

    @dataclass
    class Baz:
        c: int

    @dataclass
    class Qux:
        d: int

    decide = generate_decision_func([Foo, Bar, Baz, Qux])
    assert decide is not None
    assert decide({"a": 1}) is Foo
    assert decide({"b": 2}) is Bar
    assert decide({"c": 3}) is Baz
    assert decide({"d": 4}) is Qux


def test_dataclass_garbage_input_no_matching_fields():
    @dataclass
    class Foo:
        a: int
        b: int

    @dataclass
    class Bar:
        a: int
        c: int

    decide = generate_decision_func([Foo, Bar])
    assert decide is not None
    assert decide({"a": 1, "b": 2}) is Foo
    assert decide({"a": 1, "c": 3}) is Bar
    # No matching fields at all
    assert decide({"x": 1}) is None
    assert decide({}) is None
    # Has discriminator field but missing shared required field
    assert decide({"b": 2}) is None
    assert decide({"c": 3}) is None


def test_dataclass_subset_fields_garbage_input():
    @dataclass
    class Foo:
        a: int

    @dataclass
    class Bar:
        a: int
        b: int

    decide = generate_decision_func([Foo, Bar])
    assert decide is not None
    assert decide({"a": 1, "b": 2}) is Bar
    assert decide({"a": 1}) is Foo
    # Missing 'a' — should not match Foo even though 'b' is absent
    assert decide({"x": 1}) is None
    assert decide({"b": 2}) is None
    assert decide({}) is None


def test_dataclass_three_types_garbage_input():
    @dataclass
    class Foo:
        a: int
        b: int

    @dataclass
    class Bar:
        a: int
        c: int

    @dataclass
    class Baz:
        a: int
        d: int

    decide = generate_decision_func([Foo, Bar, Baz])
    assert decide is not None
    assert decide({"a": 1, "b": 2}) is Foo
    assert decide({"a": 1, "c": 3}) is Bar
    assert decide({"a": 1, "d": 4}) is Baz
    # Has unique field but missing shared required 'a'
    assert decide({"b": 2}) is None
    assert decide({"c": 3}) is None
    assert decide({"d": 4}) is None
    assert decide({"x": 1}) is None


def test_dataclass_chain_subset_garbage_input():
    @dataclass
    class Foo:
        a: int

    @dataclass
    class Bar:
        a: int
        b: int

    @dataclass
    class Baz:
        a: int
        b: int
        c: int

    decide = generate_decision_func([Foo, Bar, Baz])
    assert decide is not None
    assert decide({"a": 1, "b": 2, "c": 3}) is Baz
    assert decide({"a": 1, "b": 2}) is Bar
    assert decide({"a": 1}) is Foo
    # Missing required fields
    assert decide({"b": 2, "c": 3}) is None
    assert decide({"c": 3}) is None
    assert decide({}) is None


def test_dataclass_foreign_keys_tolerated():
    @dataclass
    class Foo:
        a: int

    @dataclass
    class Bar:
        b: int

    decide = generate_decision_func([Foo, Bar])
    assert decide is not None
    assert decide({"a": 1, "x": 99}) is Foo
    assert decide({"b": 2, "x": 99}) is Bar


def test_dataclass_sibling_field_rejects_in_overlapping_case():
    @dataclass
    class Foo:
        a: int
        b: int

    @dataclass
    class Bar:
        a: int
        c: int

    decide = generate_decision_func([Foo, Bar])
    assert decide is not None
    assert decide({"a": 1, "b": 2, "c": 3}) is None


def test_single_typeddict():
    class Foo(TypedDict):
        a: int
        b: int

    decide = generate_decision_func([Foo])
    assert decide is not None
    assert decide({"a": 1, "b": 2}) is Foo
    assert decide({"x": 1}) is None


def test_two_typeddicts_distinct_fields():
    class Foo(TypedDict):
        a: int
        b: int

    class Bar(TypedDict):
        a: int
        c: int

    decide = generate_decision_func([Foo, Bar])
    assert decide is not None
    assert decide({"a": 1, "b": 2}) is Foo
    assert decide({"a": 1, "c": 3}) is Bar


def test_identical_typeddicts_returns_none():
    class X(TypedDict):
        a: int

    class Y(TypedDict):
        a: int

    assert build_decision_tree([X, Y]) is None
    assert generate_decision_func([X, Y]) is None


def test_typeddict_with_not_required():
    class A(TypedDict):
        a: int
        b: NotRequired[int]

    class B(TypedDict):
        a: int
        c: int

    decide = generate_decision_func([A, B])
    assert decide is not None
    assert decide({"a": 1, "b": 2}) is A
    assert decide({"a": 1, "c": 3}) is B


def test_typeddict_total_false():
    class A(TypedDict, total=False):
        a: int
        b: Required[int]

    class B(TypedDict):
        a: int
        c: int

    decide = generate_decision_func([A, B])
    assert decide is not None
    assert decide({"b": 2}) is A
    assert decide({"a": 1, "c": 3}) is B


def test_typeddict_all_not_required_indistinguishable():
    class A(TypedDict):
        a: int
        b: NotRequired[int]

    class B(TypedDict):
        a: int
        c: NotRequired[int]

    assert generate_decision_func([A, B]) is None


def test_typeddict_subset_fields():
    class A(TypedDict):
        a: int

    class B(TypedDict):
        a: int
        b: int

    decide = generate_decision_func([A, B])
    assert decide is not None
    assert decide({"a": 1, "b": 2}) is B
    assert decide({"a": 1}) is A


def test_three_typeddicts():
    class A(TypedDict):
        a: int

    class B(TypedDict):
        b: int

    class C(TypedDict):
        c: int

    decide = generate_decision_func([A, B, C])
    assert decide is not None
    assert decide({"a": 1}) is A
    assert decide({"b": 2}) is B
    assert decide({"c": 3}) is C


def test_typeddict_foreign_keys_tolerated():
    class Foo(TypedDict):
        a: int
        b: int

    class Bar(TypedDict):
        a: int
        c: int

    decide = generate_decision_func([Foo, Bar])
    assert decide is not None
    assert decide({"a": 1, "b": 2, "x": 99}) is Foo
    assert decide({"a": 1, "c": 3, "x": 99}) is Bar


def test_typeddict_garbage_input():
    class Foo(TypedDict):
        a: int
        b: int

    class Bar(TypedDict):
        a: int
        c: int

    decide = generate_decision_func([Foo, Bar])
    assert decide is not None
    assert decide({"x": 1}) is None
    assert decide({}) is None
    assert decide({"b": 2}) is None
    assert decide({"c": 3}) is None


def test_mixed_dataclass_and_typeddict():
    @dataclass
    class DC:
        a: int
        b: int

    class TD(TypedDict):
        a: int
        c: int

    decide = generate_decision_func([DC, TD])
    assert decide is not None
    assert decide({"a": 1, "b": 2}) is DC
    assert decide({"a": 1, "c": 3}) is TD


def test_mixed_three_types():
    @dataclass
    class DC1:
        x: int

    @dataclass
    class DC2:
        y: int

    class TD(TypedDict):
        z: int

    decide = generate_decision_func([DC1, DC2, TD])
    assert decide is not None
    assert decide({"x": 1}) is DC1
    assert decide({"y": 2}) is DC2
    assert decide({"z": 3}) is TD


def test_mixed_with_optional_fields():
    @dataclass
    class DC:
        a: int
        b: int = 0

    class TD(TypedDict):
        a: int
        c: NotRequired[int]
        d: int

    decide = generate_decision_func([DC, TD])
    assert decide is not None
    assert decide({"a": 1, "b": 2}) is DC
    assert decide({"a": 1, "d": 4}) is TD


def test_generic_typeddict():
    T = TypeVar("T")

    class GenTD(TypedDict, Generic[T]):
        a: T
        b: int

    class Other(TypedDict):
        a: int
        c: int

    decide = generate_decision_func([GenTD[int], Other])
    assert decide is not None
    assert decide({"a": 1, "b": 2}) is GenTD[int]
    assert decide({"a": 1, "c": 3}) is Other


def test_typeddict_inheritance():
    class Base(TypedDict):
        a: int

    class Child(Base):
        b: int

    decide = generate_decision_func([Base, Child])
    assert decide is not None
    assert decide({"a": 1, "b": 2}) is Child
    assert decide({"a": 1}) is Base


def test_typeddict_total_false_no_required():
    class A(TypedDict, total=False):
        a: int
        b: int

    class B(TypedDict):
        c: int

    decide = generate_decision_func([A, B])
    assert decide is not None
    assert decide({"a": 1}) is A
    assert decide({"c": 3}) is B
    # {} is valid for A since all fields are optional
    assert decide({}) is A


def test_mixed_identical_fields_returns_none():
    @dataclass
    class DC:
        a: int

    class TD(TypedDict):
        a: int

    assert generate_decision_func([DC, TD]) is None


def test_mixed_garbage_input():
    @dataclass
    class DC:
        a: int
        b: int

    class TD(TypedDict):
        a: int
        c: int

    decide = generate_decision_func([DC, TD])
    assert decide is not None
    assert decide({"x": 1}) is None
    assert decide({}) is None
    assert decide({"b": 2}) is None
    assert decide({"c": 3}) is None


def test_tagged_union_strings():
    @dataclass
    class A:
        tag: Literal["a"]
        x: int

    @dataclass
    class B:
        tag: Literal["b"]
        y: int

    tree = build_decision_tree([A, B])
    assert isinstance(tree, TagSplit)
    assert tree.field == "tag"
    assert [v for v, _ in tree.branches] == ["a", "b"]

    decide = generate_decision_func([A, B])
    assert decide is not None
    assert decide({"tag": "a", "x": 1}) is A
    assert decide({"tag": "b", "y": 2}) is B
    assert decide({"tag": "c", "x": 1}) is None
    assert decide({"x": 1}) is None
    assert decide({"tag": "a"}) is None
    assert decide({"tag": "b", "y": 2, "x": 1}) is None


def test_tagged_union_three_way():
    @dataclass
    class A:
        kind: Literal["a"]

    @dataclass
    class B:
        kind: Literal["b"]

    @dataclass
    class C:
        kind: Literal["c"]

    decide = generate_decision_func([A, B, C])
    assert decide is not None
    assert decide({"kind": "a"}) is A
    assert decide({"kind": "b"}) is B
    assert decide({"kind": "c"}) is C
    assert decide({"kind": "d"}) is None
    assert decide({}) is None


def test_tagged_union_int_values():
    @dataclass
    class A:
        kind: Literal[1]

    @dataclass
    class B:
        kind: Literal[2]

    decide = generate_decision_func([A, B])
    assert decide is not None
    assert decide({"kind": 1}) is A
    assert decide({"kind": 2}) is B
    assert decide({"kind": 3}) is None


def test_tagged_union_bool_int_distinct():
    @dataclass
    class A:
        kind: Literal[True]
        x: int

    @dataclass
    class B:
        kind: Literal[1]
        y: int

    tree = build_decision_tree([A, B])
    assert isinstance(tree, TagSplit)

    decide = generate_decision_func([A, B])
    assert decide is not None
    assert decide({"kind": True, "x": 10}) is A
    assert decide({"kind": 1, "y": 20}) is B
    assert decide({"kind": False, "x": 10}) is None
    assert decide({"kind": 0, "y": 20}) is None
    assert decide({"kind": "1"}) is None


def test_tagged_union_false_zero_distinct():
    @dataclass
    class A:
        kind: Literal[False]

    @dataclass
    class B:
        kind: Literal[0]

    decide = generate_decision_func([A, B])
    assert decide is not None
    assert decide({"kind": False}) is A
    assert decide({"kind": 0}) is B
    assert decide({"kind": True}) is None
    assert decide({"kind": 1}) is None


def test_tagged_union_none_value():
    @dataclass
    class A:
        kind: Literal[None]
        x: int

    @dataclass
    class B:
        kind: Literal["b"]
        y: int

    decide = generate_decision_func([A, B])
    assert decide is not None
    assert decide({"kind": None, "x": 1}) is A
    assert decide({"kind": "b", "y": 2}) is B
    assert decide({"x": 1}) is None
    assert decide({"kind": 0, "x": 1}) is None
    assert decide({"kind": False, "x": 1}) is None


def test_tagged_union_enum_values():
    class Color(Enum):
        RED = "red"
        BLUE = "blue"

    @dataclass
    class A:
        kind: Literal[Color.RED]
        x: int

    @dataclass
    class B:
        kind: Literal[Color.BLUE]
        y: int

    decide = generate_decision_func([A, B])
    assert decide is not None
    assert decide({"kind": Color.RED, "x": 1}) is A
    assert decide({"kind": Color.BLUE, "y": 2}) is B
    assert decide({"kind": "red", "x": 1}) is None


def test_tagged_union_intenum_vs_int_strict_type():
    class Code(IntEnum):
        A = 1
        B = 2

    @dataclass
    class A:
        kind: Literal[Code.A]
        x: int

    @dataclass
    class B:
        kind: Literal[1]
        y: int

    tree = build_decision_tree([A, B])
    assert isinstance(tree, TagSplit)

    decide = generate_decision_func([A, B])
    assert decide is not None
    assert decide({"kind": Code.A, "x": 1}) is A
    assert decide({"kind": 1, "y": 2}) is B


def test_tagged_literal_with_default_is_a_tag():
    @dataclass
    class A:
        kind: Literal["a"] = "a"

    @dataclass
    class B:
        kind: Literal["b"] = "b"

    tree = build_decision_tree([A, B])
    assert isinstance(tree, TagSplit)

    decide = generate_decision_func([A, B])
    assert decide is not None
    assert decide({"kind": "a"}) is A
    assert decide({"kind": "b"}) is B
    assert decide({"kind": "c"}) is None
    assert decide({}) is None


def test_tagged_typeddict_notrequired_literal_is_a_tag():
    class A(TypedDict):
        kind: NotRequired[Literal["a"]]
        x: int

    class B(TypedDict):
        kind: NotRequired[Literal["b"]]
        y: int

    tree = build_decision_tree([A, B])
    assert isinstance(tree, TagSplit)

    decide = generate_decision_func([A, B])
    assert decide is not None
    assert decide({"kind": "a", "x": 1}) is A
    assert decide({"kind": "b", "y": 2}) is B
    assert decide({"x": 1}) is None
    assert decide({"y": 2}) is None


def test_tag_value_collision_falls_back_to_presence():
    @dataclass
    class A:
        kind: Literal["x"]
        a: int

    @dataclass
    class B:
        kind: Literal["x"]
        b: int

    tree = build_decision_tree([A, B])
    assert not isinstance(tree, TagSplit)

    decide = generate_decision_func([A, B])
    assert decide is not None
    assert decide({"kind": "x", "a": 1}) is A
    assert decide({"kind": "x", "b": 2}) is B
    assert decide({"kind": "x", "a": 1, "b": 2}) is None


def test_tagged_typeddict():
    class A(TypedDict):
        kind: Literal["a"]
        x: int

    class B(TypedDict):
        kind: Literal["b"]
        y: int

    decide = generate_decision_func([A, B])
    assert decide is not None
    assert decide({"kind": "a", "x": 1}) is A
    assert decide({"kind": "b", "y": 2}) is B
    assert decide({"kind": "c", "x": 1}) is None


def test_tagged_mixed_dataclass_and_typeddict():
    @dataclass
    class A:
        kind: Literal["a"]
        x: int

    class B(TypedDict):
        kind: Literal["b"]
        y: int

    decide = generate_decision_func([A, B])
    assert decide is not None
    assert decide({"kind": "a", "x": 1}) is A
    assert decide({"kind": "b", "y": 2}) is B


def test_partial_tag_falls_back_to_presence_then_tag():
    @dataclass
    class A:
        tag: Literal["a"]
        x: int

    @dataclass
    class B:
        tag: Literal["b"]
        x: int

    @dataclass
    class C:
        y: int

    tree = build_decision_tree([A, B, C])
    assert tree is not None
    assert not isinstance(tree, TagSplit)

    decide = generate_decision_func([A, B, C])
    assert decide is not None
    assert decide({"tag": "a", "x": 1}) is A
    assert decide({"tag": "b", "x": 1}) is B
    assert decide({"y": 1}) is C
    assert decide({"tag": "c", "x": 1}) is None
    assert decide({"tag": "a"}) is None


def test_tagged_union_annotated_literal():
    @dataclass
    class A:
        kind: Annotated[Literal["a"], "meta"]
        x: int

    @dataclass
    class B:
        kind: Annotated[Literal["b"], "meta"]
        y: int

    tree = build_decision_tree([A, B])
    assert isinstance(tree, TagSplit)

    decide = generate_decision_func([A, B])
    assert decide is not None
    assert decide({"kind": "a", "x": 1}) is A
    assert decide({"kind": "b", "y": 2}) is B


def test_tagged_generic_dataclass():
    T = TypeVar("T")

    @dataclass
    class Wrap(Generic[T]):
        kind: Literal["wrap"]
        value: T

    @dataclass
    class Other:
        kind: Literal["other"]
        y: int

    decide = generate_decision_func([Wrap[int], Other])
    assert decide is not None
    assert decide({"kind": "wrap", "value": 1}) is Wrap[int]
    assert decide({"kind": "other", "y": 2}) is Other


def test_tagged_union_multi_value_literal_not_used_as_tag():
    @dataclass
    class A:
        kind: Literal["a", "b"]
        x: int

    @dataclass
    class B:
        kind: Literal["c"]
        y: int

    tree = build_decision_tree([A, B])
    assert not isinstance(tree, TagSplit)

    decide = generate_decision_func([A, B])
    assert decide is not None
    assert decide({"kind": "a", "x": 1}) is A
    assert decide({"kind": "c", "y": 2}) is B


def test_tagged_union_foreign_field_rejected():
    @dataclass
    class A:
        tag: Literal["a"]
        x: int

    @dataclass
    class B:
        tag: Literal["b"]
        y: int

    decide = generate_decision_func([A, B])
    assert decide is not None
    assert decide({"tag": "a", "x": 1, "y": 2}) is None
    assert decide({"tag": "b", "y": 2, "x": 1}) is None
    assert decide({"tag": "a", "x": 1, "z": 99}) is A


def test_tagged_union_extra_required_field_missing():
    @dataclass
    class A:
        tag: Literal["a"]
        x: int
        y: int

    @dataclass
    class B:
        tag: Literal["b"]
        z: int

    decide = generate_decision_func([A, B])
    assert decide is not None
    assert decide({"tag": "a", "x": 1, "y": 2}) is A
    assert decide({"tag": "a", "x": 1}) is None
    assert decide({"tag": "a", "y": 2}) is None
    assert decide({"tag": "b", "z": 3}) is B


def test_two_tag_fields_first_alphabetical_used():
    @dataclass
    class A:
        kind: Literal["a"]
        type_: Literal["x"]

    @dataclass
    class B:
        kind: Literal["b"]
        type_: Literal["y"]

    tree = build_decision_tree([A, B])
    assert isinstance(tree, TagSplit)
    assert tree.field == "kind"

    decide = generate_decision_func([A, B])
    assert decide is not None
    assert decide({"kind": "a", "type_": "x"}) is A
    assert decide({"kind": "b", "type_": "y"}) is B


def test_tagged_identical_fields_three_way():
    @dataclass
    class A:
        kind: Literal["a"]
        common1: int
        common2: str

    @dataclass
    class B:
        kind: Literal["b"]
        common1: int
        common2: str

    @dataclass
    class C:
        kind: Literal["c"]
        common1: int
        common2: str

    decide = generate_decision_func([A, B, C])
    assert decide is not None
    assert decide({"kind": "a", "common1": 1, "common2": "x"}) is A
    assert decide({"kind": "b", "common1": 1, "common2": "x"}) is B
    assert decide({"kind": "c", "common1": 1, "common2": "x"}) is C
    assert decide({"kind": "d", "common1": 1, "common2": "x"}) is None
    assert decide({"kind": "a", "common1": 1}) is None
    assert decide({"kind": "a", "common2": "x"}) is None


def test_tagged_identical_fields_with_optional():
    @dataclass
    class A:
        kind: Literal["a"]
        x: int
        y: int = 0

    @dataclass
    class B:
        kind: Literal["b"]
        x: int
        y: int = 0

    decide = generate_decision_func([A, B])
    assert decide is not None
    assert decide({"kind": "a", "x": 1}) is A
    assert decide({"kind": "a", "x": 1, "y": 2}) is A
    assert decide({"kind": "b", "x": 1}) is B
    assert decide({"kind": "b", "x": 1, "y": 2}) is B


def test_tagsplit_nested_inside_split():
    @dataclass
    class A:
        tag: Literal["a"]
        x: int

    @dataclass
    class B:
        tag: Literal["b"]
        x: int

    @dataclass
    class C:
        y: int

    tree = build_decision_tree([A, B, C])
    assert isinstance(tree, Split)

    def find_tagsplit(node):
        if isinstance(node, TagSplit):
            return node
        if isinstance(node, Split):
            return find_tagsplit(node.positive) or find_tagsplit(node.negative)
        return None

    ts = find_tagsplit(tree)
    assert ts is not None
    assert ts.field == "tag"
    assert sorted(v for v, _ in ts.branches) == ["a", "b"]

    decide = generate_decision_func([A, B, C])
    assert decide is not None
    assert decide({"tag": "a", "x": 1}) is A
    assert decide({"tag": "b", "x": 1}) is B
    assert decide({"y": 1}) is C
    assert decide({"tag": "c", "x": 1}) is None
    assert decide({"tag": "a"}) is None


def test_two_disjoint_tag_families():
    @dataclass
    class A:
        tag: Literal["a"]
        x: int

    @dataclass
    class B:
        tag: Literal["b"]
        y: int

    @dataclass
    class C:
        discriminator: Literal["c"]
        z: int

    @dataclass
    class D:
        discriminator: Literal["d"]
        w: int

    decide = generate_decision_func([A, B, C, D])
    assert decide is not None
    assert decide({"tag": "a", "x": 1}) is A
    assert decide({"tag": "b", "y": 2}) is B
    assert decide({"discriminator": "c", "z": 3}) is C
    assert decide({"discriminator": "d", "w": 4}) is D
    assert decide({"tag": "z", "x": 1}) is None
    assert decide({"discriminator": "z", "z": 3}) is None
    assert decide({}) is None
    assert decide({"tag": "a", "discriminator": "c"}) is None
    assert decide({"tag": "a", "x": 1, "z": 99}) is None


def test_presence_split_prefers_tag_promotable_field():
    @dataclass
    class TextMessage:
        type: Literal["text"]
        content: str

    @dataclass
    class ImageMessage:
        type: Literal["image"]
        url: str

    @dataclass
    class Error:
        code: int
        message: str

    tree = build_decision_tree([TextMessage, ImageMessage, Error])
    assert isinstance(tree, Split)
    assert tree.field == "type"
    assert isinstance(tree.positive, TagSplit)
    assert tree.positive.field == "type"

    decide = generate_decision_func([TextMessage, ImageMessage, Error])
    assert decide is not None
    assert decide({"type": "text", "content": "hi"}) is TextMessage
    assert decide({"type": "image", "url": "http://x"}) is ImageMessage
    assert decide({"code": 500, "message": "boom"}) is Error
    assert decide({"type": "video", "content": "x"}) is None
    assert decide({"type": "text", "url": "http://x"}) is None
