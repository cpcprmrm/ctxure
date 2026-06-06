from typing import Any, Literal

import pytest

from ctxure._location import (
    FieldSeg,
    Identifier,
    ItemSeg,
    KeySeg,
    LocationParseError,
    RootSeg,
    get_field,
    get_key,
    location_to_str,
    parse_path,
)


def test_parse_location_path():
    assert parse_path("$") == (RootSeg,)
    assert parse_path("$.foo") == (RootSeg, FieldSeg[Identifier[Literal["foo"]]])
    assert parse_path("$.?") == (RootSeg, FieldSeg[Any])
    assert parse_path("$[?]") == (RootSeg, ItemSeg[Any])
    assert parse_path("$[3]") == (RootSeg, ItemSeg[Literal[3]])
    assert parse_path("$['foo']") == (RootSeg, ItemSeg[Literal["foo"]])
    assert parse_path('$["foo"]') == (RootSeg, ItemSeg[Literal["foo"]])
    assert parse_path("$[foo.BAR]") == (RootSeg, ItemSeg[Identifier[Literal["foo.BAR"]]])
    assert parse_path("$[~1]") == (RootSeg, KeySeg[Literal[1]])
    assert parse_path("$[~'foo']") == (RootSeg, KeySeg[Literal["foo"]])
    assert parse_path('$[~"foo"]') == (RootSeg, KeySeg[Literal["foo"]])
    assert parse_path("$[~foo.BAR]") == (RootSeg, KeySeg[Identifier[Literal["foo.BAR"]]])
    assert parse_path("$[~?]") == (RootSeg, KeySeg[Any])


def test_parse_location_pathless():
    assert parse_path(".foo") == FieldSeg[Identifier[Literal["foo"]]]
    assert parse_path(".?") == FieldSeg[Any]
    assert parse_path("[?]") == ItemSeg[Any]
    assert parse_path("[3]") == ItemSeg[Literal[3]]
    assert parse_path("['foo']") == ItemSeg[Literal["foo"]]
    assert parse_path('["foo"]') == ItemSeg[Literal["foo"]]
    assert parse_path("[foo.BAR]") == ItemSeg[Identifier[Literal["foo.BAR"]]]
    assert parse_path("[~1]") == KeySeg[Literal[1]]
    assert parse_path("[~'foo']") == KeySeg[Literal["foo"]]
    assert parse_path('[~"foo"]') == KeySeg[Literal["foo"]]
    assert parse_path("[~foo.BAR]") == KeySeg[Identifier[Literal["foo.BAR"]]]
    assert parse_path("[~?]") == KeySeg[Any]


def test_parse_unknown_location():
    assert parse_path("?") == Any


def test_parse_location_after_field():
    assert parse_path("$.foo.bar") == (
        RootSeg,
        FieldSeg[Identifier[Literal["foo"]]],
        FieldSeg[Identifier[Literal["bar"]]],
    )
    assert parse_path("$.foo[0]") == (
        RootSeg,
        FieldSeg[Identifier[Literal["foo"]]],
        ItemSeg[Literal[0]],
    )
    assert parse_path("$.foo['a']") == (
        RootSeg,
        FieldSeg[Identifier[Literal["foo"]]],
        ItemSeg[Literal["a"]],
    )
    assert parse_path("$.foo[?]") == (
        RootSeg,
        FieldSeg[Identifier[Literal["foo"]]],
        ItemSeg[Any],
    )
    assert parse_path("$.foo[~?]") == (
        RootSeg,
        FieldSeg[Identifier[Literal["foo"]]],
        KeySeg[Any],
    )


def test_parse_location_after_int_key_item():
    assert parse_path("$[0].foo") == (
        RootSeg,
        ItemSeg[Literal[0]],
        FieldSeg[Identifier[Literal["foo"]]],
    )
    assert parse_path("$[0][1]") == (
        RootSeg,
        ItemSeg[Literal[0]],
        ItemSeg[Literal[1]],
    )
    assert parse_path("$[0]['a']") == (
        RootSeg,
        ItemSeg[Literal[0]],
        ItemSeg[Literal["a"]],
    )
    assert parse_path("$[0][?]") == (
        RootSeg,
        ItemSeg[Literal[0]],
        ItemSeg[Any],
    )
    assert parse_path("$[0][~?]") == (
        RootSeg,
        ItemSeg[Literal[0]],
        KeySeg[Any],
    )


def test_parse_location_after_str_key_item():
    assert parse_path("$['a'].foo") == (
        RootSeg,
        ItemSeg[Literal["a"]],
        FieldSeg[Identifier[Literal["foo"]]],
    )
    assert parse_path("$['a'][0]") == (
        RootSeg,
        ItemSeg[Literal["a"]],
        ItemSeg[Literal[0]],
    )
    assert parse_path("$['a']['b']") == (
        RootSeg,
        ItemSeg[Literal["a"]],
        ItemSeg[Literal["b"]],
    )
    assert parse_path("$['a'][?]") == (
        RootSeg,
        ItemSeg[Literal["a"]],
        ItemSeg[Any],
    )
    assert parse_path("$['a'][~?]") == (
        RootSeg,
        ItemSeg[Literal["a"]],
        KeySeg[Any],
    )
    assert parse_path('$["a"]["b"]') == (
        RootSeg,
        ItemSeg[Literal["a"]],
        ItemSeg[Literal["b"]],
    )


def test_parse_location_after_wildcard_key_item():
    assert parse_path("$[?].foo") == (
        RootSeg,
        ItemSeg[Any],
        FieldSeg[Identifier[Literal["foo"]]],
    )
    assert parse_path("$[?][0]") == (
        RootSeg,
        ItemSeg[Any],
        ItemSeg[Literal[0]],
    )
    assert parse_path("$[?]['a']") == (
        RootSeg,
        ItemSeg[Any],
        ItemSeg[Literal["a"]],
    )
    assert parse_path("$[?][?]") == (
        RootSeg,
        ItemSeg[Any],
        ItemSeg[Any],
    )
    assert parse_path("$[?][~?]") == (
        RootSeg,
        ItemSeg[Any],
        KeySeg[Any],
    )


def test_parse_location_after_dict_key():
    assert parse_path("$[~?].foo") == (
        RootSeg,
        KeySeg[Any],
        FieldSeg[Identifier[Literal["foo"]]],
    )
    assert parse_path("$[~?][0]") == (
        RootSeg,
        KeySeg[Any],
        ItemSeg[Literal[0]],
    )
    assert parse_path("$[~?]['a']") == (
        RootSeg,
        KeySeg[Any],
        ItemSeg[Literal["a"]],
    )
    assert parse_path("$[~'a']['b']") == (
        RootSeg,
        KeySeg[Literal["a"]],
        ItemSeg[Literal["b"]],
    )
    assert parse_path('$[~"a"]["b"]') == (
        RootSeg,
        KeySeg[Literal["a"]],
        ItemSeg[Literal["b"]],
    )


def test_parse_location_three_segments():
    assert parse_path("$[0][1][2]") == (
        RootSeg,
        ItemSeg[Literal[0]],
        ItemSeg[Literal[1]],
        ItemSeg[Literal[2]],
    )
    assert parse_path("$.foo[0].bar") == (
        RootSeg,
        FieldSeg[Identifier[Literal["foo"]]],
        ItemSeg[Literal[0]],
        FieldSeg[Identifier[Literal["bar"]]],
    )
    assert parse_path("$[1].foo[~bar.BAR]") == (
        RootSeg,
        ItemSeg[Literal[1]],
        FieldSeg[Identifier[Literal["foo"]]],
        KeySeg[Identifier[Literal["bar.BAR"]]],
    )
    assert parse_path("$['a']['b']['c']") == (
        RootSeg,
        ItemSeg[Literal["a"]],
        ItemSeg[Literal["b"]],
        ItemSeg[Literal["c"]],
    )
    assert parse_path("$['a'][~?]['b']") == (
        RootSeg,
        ItemSeg[Literal["a"]],
        KeySeg[Any],
        ItemSeg[Literal["b"]],
    )
    assert parse_path("$.foo.bar.baz") == (
        RootSeg,
        FieldSeg[Identifier[Literal["foo"]]],
        FieldSeg[Identifier[Literal["bar"]]],
        FieldSeg[Identifier[Literal["baz"]]],
    )


def test_parse_location_kebab_field():
    assert parse_path(".foo-bar") == FieldSeg[Identifier[Literal["foo-bar"]]]
    assert parse_path(".foo--bar") == FieldSeg[Identifier[Literal["foo--bar"]]]
    assert parse_path(".x-y-z") == FieldSeg[Identifier[Literal["x-y-z"]]]
    assert parse_path(".x-request-id") == FieldSeg[Identifier[Literal["x-request-id"]]]
    assert parse_path("$.foo-bar") == (
        RootSeg,
        FieldSeg[Identifier[Literal["foo-bar"]]],
    )
    assert parse_path("$.a.b-c.d") == (
        RootSeg,
        FieldSeg[Identifier[Literal["a"]]],
        FieldSeg[Identifier[Literal["b-c"]]],
        FieldSeg[Identifier[Literal["d"]]],
    )


def test_parse_location_quoted_field():
    assert parse_path(".'foo bar'") == FieldSeg[Identifier[Literal["foo bar"]]]
    assert parse_path('."foo bar"') == FieldSeg[Identifier[Literal["foo bar"]]]
    assert parse_path(".'$id'") == FieldSeg[Identifier[Literal["$id"]]]
    assert parse_path(".'foo.bar'") == FieldSeg[Identifier[Literal["foo.bar"]]]
    assert parse_path('$.a."b c".d') == (
        RootSeg,
        FieldSeg[Identifier[Literal["a"]]],
        FieldSeg[Identifier[Literal["b c"]]],
        FieldSeg[Identifier[Literal["d"]]],
    )


def test_location_to_str_roundtrip():
    def roundtrip(s):
        return location_to_str(parse_path(s))

    assert roundtrip("?") == "?"

    assert roundtrip("$") == "$"
    assert roundtrip("$.foo") == "$.foo"
    assert roundtrip("$.?") == "$.?"
    assert roundtrip("$[1]") == "$[1]"
    assert roundtrip("$['a']") == "$['a']"
    assert roundtrip('$["a"]') == "$['a']"
    assert roundtrip("$[Foo.ABC]") == "$[Foo.ABC]"
    assert roundtrip("$[?]") == "$[?]"
    assert roundtrip("$[~'a']") == "$[~'a']"
    assert roundtrip('$[~"a"]') == "$[~'a']"
    assert roundtrip("$[~Foo.ABC]") == "$[~Foo.ABC]"
    assert roundtrip("$[~?]") == "$[~?]"

    assert roundtrip("$.foo[0]['bar']") == "$.foo[0]['bar']"
    assert roundtrip("$[0][?][1]") == "$[0][?][1]"
    assert roundtrip("$[~'foo'][0][?][foo.FOO]") == "$[~'foo'][0][?][foo.FOO]"
    assert roundtrip("$.foo[1].bar['a'].baz") == "$.foo[1].bar['a'].baz"
    assert roundtrip("$['a']['b']['c']") == "$['a']['b']['c']"
    assert roundtrip("$['a'][~?]['b']") == "$['a'][~?]['b']"
    assert roundtrip("$.foo.bar.baz") == "$.foo.bar.baz"
    assert roundtrip("$[~'a']['b']") == "$[~'a']['b']"

    assert roundtrip(".foo-bar") == ".foo-bar"
    assert roundtrip("$.x-request-id") == "$.x-request-id"
    assert roundtrip(".'foo bar'") == ".'foo bar'"
    assert roundtrip('."foo bar"') == ".'foo bar'"
    assert roundtrip(".'foo.bar'") == ".'foo.bar'"
    assert roundtrip(".'$id'") == ".'$id'"

    assert roundtrip("[3]") == "[3]"
    assert roundtrip("['a']") == "['a']"
    assert roundtrip('["a"]') == "['a']"
    assert roundtrip("[Foo.ABC]") == "[Foo.ABC]"
    assert roundtrip("[?]") == "[?]"
    assert roundtrip("[~2]") == "[~2]"
    assert roundtrip("[~'a']") == "[~'a']"
    assert roundtrip('[~"a"]') == "[~'a']"
    assert roundtrip("[~Foo.ABC]") == "[~Foo.ABC]"
    assert roundtrip("[~?]") == "[~?]"
    assert roundtrip(".foo") == ".foo"
    assert roundtrip(".?") == ".?"


def test_path_segment_accessors():
    def pl(expr: str) -> Any:
        return parse_path(expr)

    # FieldSeg
    assert get_field(pl("$.foo")[1]) == "foo"
    assert get_field(pl("$.?")[1]) is None

    # FieldSeg
    assert get_field(pl(".foo")) == "foo"
    assert get_field(pl(".?")) is None

    # ItemSeg
    assert get_key(pl("$[3]")[1]) == 3
    assert get_key(pl("$['a']")[1]) == "a"
    assert get_key(pl("$[?]")[1]) is None
    assert get_key(pl("$[Foo.BAR]")[1]) == "Foo.BAR"

    # KeySeg
    assert get_key(pl("$[~5]")[1]) == 5
    assert get_key(pl("$[~'k']")[1]) == "k"
    assert get_key(pl("$[~?]")[1]) is None

    # ItemSeg
    assert get_key(pl("[3]")) == 3
    assert get_key(pl("['a']")) == "a"
    assert get_key(pl("[?]")) is None

    # KeySeg
    assert get_key(pl("[~5]")) == 5
    assert get_key(pl("[~'k']")) == "k"
    assert get_key(pl("[~?]")) is None


def test_parse_location_invalid():
    with pytest.raises(LocationParseError) as e:
        parse_path("")
    assert e.value.pos == 0

    with pytest.raises(LocationParseError) as e:
        parse_path("$0]")
    assert e.value.pos == 1

    with pytest.raises(LocationParseError) as e:
        parse_path("$[0].")
    assert e.value.pos == 5

    with pytest.raises(LocationParseError) as e:
        parse_path("$[0_]")
    assert e.value.pos == 3

    with pytest.raises(LocationParseError) as e:
        parse_path("$['a'1]")
    assert e.value.pos == 5

    with pytest.raises(LocationParseError) as e:
        parse_path("$..foo")
    assert e.value.pos == 2

    with pytest.raises(LocationParseError) as e:
        parse_path("$.foo.")
    assert e.value.pos == 6

    with pytest.raises(LocationParseError) as e:
        parse_path(".-foo")
    assert e.value.pos == 1

    with pytest.raises(LocationParseError) as e:
        parse_path(".foo-")
    assert e.value.pos == 4

    with pytest.raises(LocationParseError) as e:
        parse_path(".foo--")
    assert e.value.pos == 4

    with pytest.raises(LocationParseError) as e:
        parse_path("$[*]")
    assert e.value.pos == 2

    with pytest.raises(LocationParseError) as e:
        parse_path("$<0>")
    assert e.value.pos == 1

    with pytest.raises(LocationParseError) as e:
        parse_path("$.foo[abc]")
    assert e.value.pos == 6

    with pytest.raises(LocationParseError) as e:
        parse_path("$.foo[abc.]")
    assert e.value.pos == 6

    with pytest.raises(LocationParseError) as e:
        parse_path("$.foo[10")
    assert e.value.pos == 8

    with pytest.raises(LocationParseError) as e:
        parse_path("[0][1]")
    assert e.value.pos == 3

    with pytest.raises(LocationParseError) as e:
        parse_path("[0")
    assert e.value.pos == 2

    with pytest.raises(LocationParseError) as e:
        parse_path("0]")
    assert e.value.pos == 0

    with pytest.raises(LocationParseError) as e:
        parse_path("['foo\"]")
    assert e.value.pos == 1

    with pytest.raises(LocationParseError) as e:
        parse_path(".")
    assert e.value.pos == 1

    with pytest.raises(LocationParseError) as e:
        parse_path(".1")
    assert e.value.pos == 1

    with pytest.raises(LocationParseError) as e:
        parse_path(".foo$")
    assert e.value.pos == 4

    with pytest.raises(LocationParseError) as e:
        parse_path("Foo.")
    assert e.value.pos == 0

    with pytest.raises(LocationParseError) as e:
        parse_path("Foo")
    assert e.value.pos == 0

    with pytest.raises(LocationParseError) as e:
        parse_path("Foo.foo")
    assert e.value.pos == 0

    with pytest.raises(LocationParseError) as e:
        parse_path("abc.def.Foo")
    assert e.value.pos == 0
