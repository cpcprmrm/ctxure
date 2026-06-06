from dataclasses import dataclass
from typing import Any, Generic, Literal, NewType, TypeVar, get_args

import pytest

from ctxure import (
    Ctx,
    LocationParseError,
    Of,
    Under,
    ctxure_config,
    get_data,
    get_extra,
    get_parent,
    get_root,
    structure,
)
from ctxure._location import FieldSeg, Identifier, ItemSeg, KeySeg, RootSeg
from ctxure.context import CtxImpl
from ctxure.multidispatch import is_subtype_invariant  # type: ignore


def test_ctx_properties():
    ctx = CtxImpl[int, Any, Any, tuple[Any, ItemSeg[Literal[1]]]](None, int, "$[0]", "$[2]", 1)
    assert ctx.parent is None
    assert ctx.structured_key == 1
    assert ctx.field == 1
    assert ctx.index == 1
    assert ctx.structured_path == "$[0]"
    assert ctx.unstructured_path == "$[2]"


def test_ctx_with_type():
    T = TypeVar("T")

    Int = NewType("Int", int)

    @dataclass
    class Foo: ...

    @dataclass
    class Bar(Generic[T]): ...

    assert Ctx[Any] == CtxImpl[Any, Any, Any, Any]
    assert Ctx[int] == CtxImpl[int, Any, Any, Any]
    assert Ctx[str] == CtxImpl[str, Any, Any, Any]
    assert Ctx[int | str] == CtxImpl[int | str, Any, Any, Any]
    assert Ctx[list] == CtxImpl[list, Any, Any, Any]
    assert Ctx[list[Any]] == CtxImpl[list[Any], Any, Any, Any]
    assert Ctx[list[int]] == CtxImpl[list[int], Any, Any, Any]
    assert Ctx[Literal[1, 2]] == CtxImpl[Literal[1, 2], Any, Any, Any]
    assert Ctx[Int] == CtxImpl[Int, Any, Any, Any]
    assert Ctx[Foo] == CtxImpl[Foo, Any, Any, Any]
    assert Ctx[Bar] == CtxImpl[Bar, Any, Any, Any]
    assert Ctx[Bar[Any]] == CtxImpl[Bar[Any], Any, Any, Any]
    assert Ctx[Bar[int]] == CtxImpl[Bar[int], Any, Any, Any]


def test_ctx_with_location():
    assert Ctx["?"] == CtxImpl[Any, Any, Any, Any]

    assert Ctx["$"] == CtxImpl[Any, Any, Any, tuple[tuple[()], RootSeg]]
    assert Ctx["$[0]"] == CtxImpl[Any, Any, Any, tuple[tuple[RootSeg], ItemSeg[Literal[0]]]]

    assert Ctx[".foo"] == CtxImpl[Any, Any, Any, tuple[Any, FieldSeg[Identifier[Literal["foo"]]]]]
    assert Ctx[".?"] == CtxImpl[Any, Any, Any, tuple[Any, FieldSeg[Any]]]

    assert Ctx["[0]"] == CtxImpl[Any, Any, Any, tuple[Any, ItemSeg[Literal[0]]]]
    assert Ctx["[?]"] == CtxImpl[Any, Any, Any, tuple[Any, ItemSeg[Any]]]

    assert Ctx["[~0]"] == CtxImpl[Any, Any, Any, tuple[Any, KeySeg[Literal[0]]]]
    assert Ctx["[~?]"] == CtxImpl[Any, Any, Any, tuple[Any, KeySeg[Any]]]

    with pytest.raises(LocationParseError):
        Ctx["$<1>"]


def test_ctx_with_type_and_location():
    assert Ctx[int, "$"] == CtxImpl[int, Any, Any, tuple[tuple[()], RootSeg]]
    assert Ctx["$", int] == CtxImpl[int, Any, Any, tuple[tuple[()], RootSeg]]

    assert Ctx[str, ".foo"] == CtxImpl[str, Any, Any, tuple[Any, FieldSeg[Identifier[Literal["foo"]]]]]
    assert Ctx[".foo", str] == CtxImpl[str, Any, Any, tuple[Any, FieldSeg[Identifier[Literal["foo"]]]]]

    assert Ctx[int, "[1]"] == CtxImpl[int, Any, Any, tuple[Any, ItemSeg[Literal[1]]]]
    assert Ctx["[1]", int] == CtxImpl[int, Any, Any, tuple[Any, ItemSeg[Literal[1]]]]

    assert Ctx[object, "[~1]"] == CtxImpl[object, Any, Any, tuple[Any, KeySeg[Literal[1]]]]
    assert Ctx["[~1]", object] == CtxImpl[object, Any, Any, tuple[Any, KeySeg[Literal[1]]]]

    assert Ctx[Any, "$"] == CtxImpl[Any, Any, Any, tuple[tuple[()], RootSeg]]
    assert Ctx["$", Any] == CtxImpl[Any, Any, Any, tuple[tuple[()], RootSeg]]


def test_ctx_with_owner():
    @dataclass
    class Foo(Generic[TypeVar("T")]): ...

    assert Ctx[Of[Foo]] == CtxImpl[Any, Any, Foo, Any]
    assert Ctx[Of[Foo[int]]] == CtxImpl[Any, Any, Foo[int], Any]
    assert Ctx[Of[list]] == CtxImpl[Any, Any, list, Any]


def test_ctx_with_type_and_owner():
    @dataclass
    class Foo(Generic[TypeVar("T")]): ...

    assert Ctx[int, Of[Foo]] == CtxImpl[int, Any, Foo, Any]
    assert Ctx[Of[Foo], int] == CtxImpl[int, Any, Foo, Any]
    assert Ctx[str, Of[Foo[int]]] == CtxImpl[str, Any, Foo[int], Any]
    assert Ctx[Of[list], int] == CtxImpl[int, Any, list, Any]
    assert Ctx[Any, Of[Foo]] == CtxImpl[Any, Any, Foo, Any]
    assert Ctx[Of[Foo], Any] == CtxImpl[Any, Any, Foo, Any]


def test_ctx_with_owner_and_location():
    @dataclass
    class Foo(Generic[TypeVar("T")]): ...

    assert Ctx[Of[Foo], ".foo"] == CtxImpl[Any, Any, Foo, tuple[Any, FieldSeg[Identifier[Literal["foo"]]]]]
    assert Ctx[".foo", Of[Foo]] == CtxImpl[Any, Any, Foo, tuple[Any, FieldSeg[Identifier[Literal["foo"]]]]]

    assert Ctx[Of[Foo[int]], ".foo"] == CtxImpl[Any, Any, Foo[int], tuple[Any, FieldSeg[Identifier[Literal["foo"]]]]]
    assert Ctx[".foo", Of[Foo[int]]] == CtxImpl[Any, Any, Foo[int], tuple[Any, FieldSeg[Identifier[Literal["foo"]]]]]

    assert Ctx[Of[list], "[1]"] == CtxImpl[Any, Any, list, tuple[Any, ItemSeg[Literal[1]]]]
    assert Ctx["[1]", Of[list]] == CtxImpl[Any, Any, list, tuple[Any, ItemSeg[Literal[1]]]]

    assert Ctx[Of[dict[int, str]], "[~1]"] == CtxImpl[Any, Any, dict[int, str], tuple[Any, KeySeg[Literal[1]]]]
    assert Ctx["[~1]", Of[dict[int, str]]] == CtxImpl[Any, Any, dict[int, str], tuple[Any, KeySeg[Literal[1]]]]


def test_ctx_with_type_owner_and_location():
    @dataclass
    class Foo(Generic[TypeVar("T")]): ...

    assert Ctx[int, Of[Foo], ".foo"] == CtxImpl[int, Any, Foo, tuple[Any, FieldSeg[Identifier[Literal["foo"]]]]]
    assert Ctx[int, ".foo", Of[Foo]] == CtxImpl[int, Any, Foo, tuple[Any, FieldSeg[Identifier[Literal["foo"]]]]]

    assert (
        Ctx[Of[Foo[int]], str, ".foo"] == CtxImpl[str, Any, Foo[int], tuple[Any, FieldSeg[Identifier[Literal["foo"]]]]]
    )
    assert (
        Ctx[".foo", str, Of[Foo[int]]] == CtxImpl[str, Any, Foo[int], tuple[Any, FieldSeg[Identifier[Literal["foo"]]]]]
    )

    assert Ctx[Of[list], "[1]", object] == CtxImpl[object, Any, list, tuple[Any, ItemSeg[Literal[1]]]]
    assert Ctx["[1]", Of[list], object] == CtxImpl[object, Any, list, tuple[Any, ItemSeg[Literal[1]]]]

    assert Ctx[int, Of[dict[int, str]], "[~1]"] == CtxImpl[int, Any, dict[int, str], tuple[Any, KeySeg[Literal[1]]]]
    assert Ctx[int, "[~1]", Of[dict[int, str]]] == CtxImpl[int, Any, dict[int, str], tuple[Any, KeySeg[Literal[1]]]]


def test_ctx_with_root():
    @dataclass
    class Foo(Generic[TypeVar("T")]): ...

    assert Ctx[Under[Foo]] == CtxImpl[Any, Foo, Any, Any]
    assert Ctx[Under[Foo[int]]] == CtxImpl[Any, Foo[int], Any, Any]
    assert Ctx[Under[list]] == CtxImpl[Any, list, Any, Any]


def test_ctx_with_type_and_root():
    @dataclass
    class Foo(Generic[TypeVar("T")]): ...

    assert Ctx[int, Under[Foo]] == CtxImpl[int, Foo, Any, Any]
    assert Ctx[Under[Foo], int] == CtxImpl[int, Foo, Any, Any]


def test_ctx_with_root_owner_and_location():
    @dataclass
    class Foo(Generic[TypeVar("T")]): ...

    @dataclass
    class Bar: ...

    # Under composes with Of and rootless paths
    assert Ctx[int, Under[Foo], Of[Bar], ".x"] == CtxImpl[int, Foo, Bar, tuple[Any, FieldSeg[Identifier[Literal["x"]]]]]
    # Under composes with a rooted path (path pins position; Under pins root type — orthogonal)
    assert (
        Ctx[int, Under[Foo], "$.x"] == CtxImpl[int, Foo, Any, tuple[tuple[RootSeg], FieldSeg[Identifier[Literal["x"]]]]]
    )


def test_ctx_with_root_invalid():
    @dataclass
    class Foo: ...

    with pytest.raises(TypeError, match="Multiple `Under` constraints"):
        Ctx[Under[Foo], Under[int]]


def test_field_ctx_subtype_relation():
    @dataclass
    class Foo(Generic[TypeVar("T")]): ...

    @dataclass
    class Bar: ...

    assert is_subtype_invariant(
        CtxImpl[int, Foo, Foo, tuple[Any, FieldSeg[Identifier[Literal["foo"]]]]], CtxImpl[int, Any, Any, Any]
    )
    assert is_subtype_invariant(
        CtxImpl[Any, Foo, Foo, tuple[Any, FieldSeg[Identifier[Literal["foo"]]]]], CtxImpl[Any, Any, Any, Any]
    )
    # A typical context type created in structure/unstructure
    ctx = CtxImpl[int, Foo[int], Foo[int], tuple[tuple[RootSeg], FieldSeg[Identifier[Literal["foo"]]]]]
    assert is_subtype_invariant(ctx, Ctx[".foo"])
    assert is_subtype_invariant(ctx, Ctx[".?"])
    assert is_subtype_invariant(ctx, Ctx["$.foo"])
    assert is_subtype_invariant(ctx, Ctx[".foo", Of[Foo[int]]])
    assert is_subtype_invariant(ctx, Ctx[".?", Of[Foo[int]]])
    assert is_subtype_invariant(ctx, Ctx[".foo", Of[Foo[Any]]])
    assert is_subtype_invariant(ctx, Ctx[".?", Of[Foo[Any]]])
    assert is_subtype_invariant(ctx, Ctx[".foo", Of[Foo]])
    assert is_subtype_invariant(ctx, Ctx[".?", Of[Foo]])
    assert is_subtype_invariant(ctx, Ctx[int])
    assert is_subtype_invariant(ctx, Ctx[int, ".foo"])
    assert is_subtype_invariant(ctx, Ctx[int, ".?"])
    assert is_subtype_invariant(ctx, Ctx[int, "$.foo"])
    assert is_subtype_invariant(ctx, Ctx[int, ".foo", Of[Foo]])
    assert is_subtype_invariant(ctx, Ctx[int, ".?", Of[Foo]])
    assert not is_subtype_invariant(ctx, Ctx[".foo", Of[Foo[str]]])
    assert not is_subtype_invariant(ctx, Ctx[".?", Of[Foo[str]]])
    assert not is_subtype_invariant(ctx, Ctx[".foo", Of[Bar]])
    assert not is_subtype_invariant(ctx, Ctx[".?", Of[Bar]])
    assert not is_subtype_invariant(ctx, Ctx["[~'foo']"])
    assert not is_subtype_invariant(ctx, Ctx["$['foo']"])
    assert not is_subtype_invariant(ctx, Ctx["$[~'foo']"])
    assert not is_subtype_invariant(ctx, Ctx["$.foo.foo"])
    assert not is_subtype_invariant(ctx, Ctx["[?]"])
    assert not is_subtype_invariant(ctx, Ctx["[~?]"])
    assert not is_subtype_invariant(ctx, Ctx[str])
    assert not is_subtype_invariant(ctx, Ctx[str, "$.foo"])
    assert not is_subtype_invariant(ctx, Ctx[str, ".?"])
    assert not is_subtype_invariant(ctx, Ctx[str, "[~?]"])


def test_item_ctx_subtype_relation():
    assert is_subtype_invariant(
        CtxImpl[int, list, list, tuple[Any, ItemSeg[Identifier[1]]]], CtxImpl[int, Any, Any, Any]
    )
    assert is_subtype_invariant(
        CtxImpl[Any, list, list, tuple[Any, ItemSeg[Identifier[1]]]], CtxImpl[Any, Any, Any, Any]
    )
    # A typical context type created in structure/unstructure
    ctx = CtxImpl[int, list[int], list[int], tuple[tuple[RootSeg], ItemSeg[Literal["foo"]]]]
    assert is_subtype_invariant(ctx, Ctx["['foo']"])
    assert is_subtype_invariant(ctx, Ctx["[?]"])
    assert is_subtype_invariant(ctx, Ctx["$['foo']"])
    assert is_subtype_invariant(ctx, Ctx["$[?]"])
    assert is_subtype_invariant(ctx, Ctx["['foo']", Of[list[int]]])
    assert is_subtype_invariant(ctx, Ctx["[?]", Of[list[int]]])
    assert is_subtype_invariant(ctx, Ctx["['foo']", Of[list[Any]]])
    assert is_subtype_invariant(ctx, Ctx["[?]", Of[list[Any]]])
    assert is_subtype_invariant(ctx, Ctx["['foo']", Of[list]])
    assert is_subtype_invariant(ctx, Ctx["[?]", Of[list]])
    assert is_subtype_invariant(ctx, Ctx[int])
    assert is_subtype_invariant(ctx, Ctx[int, "['foo']"])
    assert is_subtype_invariant(ctx, Ctx[int, "[?]"])
    assert is_subtype_invariant(ctx, Ctx[int, "$['foo']"])
    assert is_subtype_invariant(ctx, Ctx[int, "$[?]"])
    assert not is_subtype_invariant(ctx, Ctx["['foo']", Of[list[str]]])
    assert not is_subtype_invariant(ctx, Ctx["[?]", Of[list[str]]])
    assert not is_subtype_invariant(ctx, Ctx["['foo']", Of[tuple[int]]])
    assert not is_subtype_invariant(ctx, Ctx["[?]", Of[tuple[int]]])
    assert not is_subtype_invariant(ctx, Ctx["[~'foo']"])
    assert not is_subtype_invariant(ctx, Ctx["[~?]"])
    assert not is_subtype_invariant(ctx, Ctx[".?"])
    assert not is_subtype_invariant(ctx, Ctx["$['bar']"])
    assert not is_subtype_invariant(ctx, Ctx["$[0]"])
    assert not is_subtype_invariant(ctx, Ctx["$[~'foo']"])
    assert not is_subtype_invariant(ctx, Ctx[str])
    assert not is_subtype_invariant(ctx, Ctx[str, "['foo']"])
    assert not is_subtype_invariant(ctx, Ctx[str, "[?]"])
    assert not is_subtype_invariant(ctx, Ctx[str, "$['foo']"])
    assert not is_subtype_invariant(ctx, Ctx[str, "$[?]"])


def test_key_ctx_subtype_relation():
    assert is_subtype_invariant(
        CtxImpl[int, dict, dict, tuple[Any, KeySeg[Identifier[1]]]], CtxImpl[int, Any, Any, Any]
    )
    assert is_subtype_invariant(
        CtxImpl[Any, dict, dict, tuple[Any, KeySeg[Identifier[1]]]], CtxImpl[Any, Any, Any, Any]
    )
    # A typical context type created in structure/unstructure
    ctx = CtxImpl[int, dict[str, int], dict[str, int], tuple[tuple[RootSeg], KeySeg[Literal["foo"]]]]
    assert is_subtype_invariant(ctx, Ctx["[~'foo']"])
    assert is_subtype_invariant(ctx, Ctx["[~?]"])
    assert is_subtype_invariant(ctx, Ctx["$[~'foo']"])
    assert is_subtype_invariant(ctx, Ctx["$[~?]"])
    assert is_subtype_invariant(ctx, Ctx["[~'foo']", Of[dict[str, int]]])
    assert is_subtype_invariant(ctx, Ctx["[~?]", Of[dict[str, int]]])
    assert is_subtype_invariant(ctx, Ctx["[~'foo']", Of[dict[Any, int]]])
    assert is_subtype_invariant(ctx, Ctx["[~?]", Of[dict[Any, int]]])
    assert is_subtype_invariant(ctx, Ctx["[~'foo']", Of[dict]])
    assert is_subtype_invariant(ctx, Ctx["[~?]", Of[dict]])
    assert is_subtype_invariant(ctx, Ctx[int])
    assert is_subtype_invariant(ctx, Ctx[int, "[~'foo']"])
    assert is_subtype_invariant(ctx, Ctx[int, "[~?]"])
    assert is_subtype_invariant(ctx, Ctx[int, "$[~'foo']"])
    assert is_subtype_invariant(ctx, Ctx[int, "$[~?]"])
    assert not is_subtype_invariant(ctx, Ctx["[~'foo']", Of[dict[int, int]]])
    assert not is_subtype_invariant(ctx, Ctx["[~?]", Of[dict[int, int]]])
    assert not is_subtype_invariant(ctx, Ctx["['foo']"])
    assert not is_subtype_invariant(ctx, Ctx["[?]"])
    assert not is_subtype_invariant(ctx, Ctx[".?"])
    assert not is_subtype_invariant(ctx, Ctx["$[~'bar']"])
    assert not is_subtype_invariant(ctx, Ctx["$[0]"])
    assert not is_subtype_invariant(ctx, Ctx["$['foo']"])
    assert not is_subtype_invariant(ctx, Ctx[str])
    assert not is_subtype_invariant(ctx, Ctx[str, "[~'foo']"])
    assert not is_subtype_invariant(ctx, Ctx[str, "[~?]"])
    assert not is_subtype_invariant(ctx, Ctx[str, "$[~'foo']"])
    assert not is_subtype_invariant(ctx, Ctx[str, "$[~?]"])


def test_ctx_invalid():
    @dataclass
    class Foo: ...

    with pytest.raises(TypeError, match="Invalid type parameter"):
        Ctx[1]

    with pytest.raises(TypeError, match="Invalid type parameter"):
        Ctx[[1, 2]]  # type: ignore

    with pytest.raises(TypeError, match="Multiple type constraints"):
        Ctx[int, "$", str]  # type: ignore

    with pytest.raises(TypeError, match="Multiple type constraints"):
        Ctx[int, str]

    with pytest.raises(TypeError, match="Multiple type constraints"):
        Ctx[int, Any]

    with pytest.raises(TypeError, match="Multiple location expressions"):
        Ctx["$[0]", "$[1]"]

    with pytest.raises(TypeError, match="Multiple location expressions"):
        Ctx["[0]", "[1]"]

    with pytest.raises(TypeError, match="Multiple location expressions"):
        Ctx[".foo", "$.foo"]

    with pytest.raises(TypeError, match="Multiple location expressions"):
        Ctx["$.foo", ".foo"]

    with pytest.raises(TypeError, match="Multiple `Of` constraints"):
        Ctx[Of[list], Of[Foo]]

    with pytest.raises(TypeError, match="cannot be combined with a rooted path"):
        Ctx["$.foo", Of[Foo]]

    with pytest.raises(TypeError, match="Too many parameters"):
        Ctx[".foo", Of[Foo], int, str, list]

    with pytest.raises(TypeError, match="Forward references as strings are not supported"):
        Ctx["Foo"]


def test_field_ctx_get():
    @dataclass
    class Foo:
        a: int
        b: str

    ct1 = CtxImpl.getcls(int, Foo, Foo, "$.a")

    assert (
        ct1
        == CtxImpl[
            int,
            Foo,
            Foo,
            tuple[tuple[RootSeg], FieldSeg[Identifier[Literal["a"]]]],
        ]
    )

    ct2 = CtxImpl.getcls(str, Foo, Foo, "$.b")
    assert (
        ct2
        == CtxImpl[
            str,
            Foo,
            Foo,
            tuple[tuple[RootSeg], FieldSeg[Identifier[Literal["b"]]]],
        ]
    )

    assert ct1 != ct2

    ct1_again = CtxImpl.getcls(int, Foo, Foo, "$.a")
    assert ct1 is ct1_again

    @dataclass
    class Bar:
        a: int

    ct3 = CtxImpl.getcls(int, Bar, Bar, "$.a")
    assert ct3 != ct1


def test_field_ctx_get_nested_path():
    @dataclass
    class Inner:
        x: int

    ct = CtxImpl.getcls(int, Inner, Inner, "$.inner.x")
    assert (
        ct
        == CtxImpl[
            int,
            Inner,
            Inner,
            tuple[tuple[RootSeg, FieldSeg[Identifier[Literal["inner"]]]], FieldSeg[Identifier[Literal["x"]]]],
        ]
    )


def test_base_ctx_get():
    ct0 = CtxImpl.getcls(int, int, None, "$")
    assert ct0 == CtxImpl[int, int, None, tuple[tuple[()], RootSeg]]

    ct0_again = CtxImpl.getcls(int, int, None, "$")
    assert ct0 is ct0_again

    ct1 = CtxImpl.getcls(str, str, None, "$")
    assert ct1 == CtxImpl[str, str, None, tuple[tuple[()], RootSeg]]
    assert ct0 != ct1


def test_item_ctx_get():
    ct0 = CtxImpl.getcls(int, list[int], list[int], "$[0]")
    assert ct0 == CtxImpl[int, list[int], list[int], tuple[tuple[RootSeg], ItemSeg[Literal[0]]]]

    ct0_again = CtxImpl.getcls(int, list[int], list[int], "$[0]")
    assert ct0 is ct0_again

    ct1 = CtxImpl.getcls(int, list[int], list[int], "$[1]")
    assert ct1 == CtxImpl[int, list[int], list[int], tuple[tuple[RootSeg], ItemSeg[Literal[1]]]]
    assert ct0 != ct1

    ct3 = CtxImpl.getcls(int, tuple[int, ...], tuple[int, ...], "$[0]")
    assert ct3 != ct0


def test_item_ctx_get_unkeyed():
    ct = CtxImpl.getcls(int, set[int], set[int], "$[?]")
    assert ct == CtxImpl[int, set[int], set[int], tuple[tuple[RootSeg], ItemSeg[Any]]]

    ct_again = CtxImpl.getcls(int, set[int], set[int], "$[?]")
    assert ct is ct_again


def test_item_ctx_get_dict_value():
    ct = CtxImpl.getcls(str, dict[str, str], dict[str, str], "$['x']")
    assert ct == CtxImpl[str, dict[str, str], dict[str, str], tuple[tuple[RootSeg], ItemSeg[Literal["x"]]]]

    ct_again = CtxImpl.getcls(str, dict[str, str], dict[str, str], "$['x']")
    assert ct is ct_again


def test_key_ctx_get():
    ct = CtxImpl.getcls(int, dict[int, str], dict[int, str], "$[~?]")
    assert ct == CtxImpl[int, dict[int, str], dict[int, str], tuple[tuple[RootSeg], KeySeg[Any]]]

    ct_again = CtxImpl.getcls(int, dict[int, str], dict[int, str], "$[~?]")
    assert ct is ct_again

    ct_str = CtxImpl.getcls(str, dict[str, int], dict[str, int], "$[~?]")
    assert ct_str != ct


def test_strip():
    root = CtxImpl[int, int, None, tuple[tuple[()], RootSeg]](None, int, "$", "$", None)

    ctx = Ctx[int, "$[0]"](root, int, "$[0]", "$[0]", 0)
    assert ctx._strip() == Ctx[int](root, int, "$[0]", "$[0]", 0)

    ctx = CtxImpl.getcls(str, list[str], list[str], "$[0]")(root, str, "$[0]", "$[0]", 0)
    assert ctx._strip() == Ctx[str](root, str, "$[0]", "$[0]", 0)


def test_replace_type_preserves_root_at_root_ctx():
    # When replace_type is called on a root ctx (parent=None), the new ctx's structured_type
    # changes but root must NOT change. This matters for union/NewType narrowing at the root.
    root_ctx = CtxImpl.create(None, int | str, "$", "$", None)
    new_ctx = root_ctx._replace_type(int)
    assert new_ctx.structured_type is int
    assert get_args(new_ctx.__orig_class__)[1] == (int | str)  # root preserved


def test_replace_type_preserves_root_at_child_ctx():
    root_ctx = CtxImpl.create(None, list[int | str], "$", "$", None)
    child_ctx = CtxImpl.create(root_ctx, int | str, "$[0]", "$[0]", 0)
    narrowed = child_ctx._replace_type(int)
    assert narrowed.structured_type is int
    assert get_args(narrowed.__orig_class__)[1] == list[int | str]  # root preserved
    assert get_args(narrowed.__orig_class__)[2] == list[int | str]  # owner unchanged


def test_context_getters(testregister):
    captured = []

    @testregister
    def structure_hook(ctx: Ctx[int], data: int) -> int:
        captured.append(
            {
                "data": get_data(ctx),
                "extra": get_extra(ctx),
                "parent_ctx": get_parent(ctx),
                "root_ctx": get_root(ctx),
            }
        )
        return data

    with ctxure_config(dispatcher=testregister):
        structure(list[int], [10, 20], extra={"flag": True})

    assert len(captured) == 2
    assert {c["data"] for c in captured} == {10, 20}
    assert captured[0]["root_ctx"] is captured[1]["root_ctx"]
    # get_parent is a convenience wrapper around ctx.parent — should agree at every position
    assert captured[0]["parent_ctx"] is captured[1]["parent_ctx"]

    for c in captured:
        assert c["extra"] == {"flag": True}
        # For the int positions inside list[int], the parent IS the root ctx
        assert c["parent_ctx"] is c["root_ctx"]
        assert c["root_ctx"].parent is None
        # get_parent on the root ctx returns None
        assert get_parent(c["root_ctx"]) is None
        assert c["root_ctx"].structured_type == list[int]
        assert c["root_ctx"].structured_path == "$"
