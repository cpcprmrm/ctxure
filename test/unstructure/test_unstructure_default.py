from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum, IntEnum, StrEnum
from pathlib import Path
from typing import Any, Generic, Literal, NewType, NotRequired, Optional, Required, TypedDict, TypeVar, Union
from uuid import UUID

import pytest
from typing_extensions import ReadOnly
from typing_extensions import TypeAliasType
from typing_extensions import TypedDict as ExtTypedDict

from ctxure import AmbiguousUnion, NoUnstructureHook, ValidationError, unstructure


def test_unstructure_int():
    assert unstructure(int, 1) == 1
    assert unstructure(int, 2) == 2
    assert unstructure(int, True) == 1
    assert unstructure(int, False) == 0

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(int, 1.0)
    assert e.value.ctx.structured_type is int
    assert e.value.data == 1.0

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(int, "1")
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == "1"


def test_unstructure_bool():
    assert unstructure(bool, True) is True
    assert unstructure(bool, False) is False
    assert unstructure(bool, 1) is True
    assert unstructure(bool, -1) is True
    assert unstructure(bool, 0) is False

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(bool, 1.0)
    assert e.value.ctx.structured_type is bool
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 1.0

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(bool, "True")
    assert e.value.ctx.structured_type is bool
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == "True"


def test_unstructure_float():
    assert unstructure(float, 1.1) == 1.1
    assert unstructure(float, 1) == 1.0
    assert type(unstructure(float, 1)) is float
    assert unstructure(float, True) == 1.0
    assert type(unstructure(float, True)) is float
    assert unstructure(float, False) == 0.0
    assert type(unstructure(float, False)) is float

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(float, "1.0")
    assert e.value.ctx.structured_type is float
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == "1.0"


def test_unstructure_str():
    assert unstructure(str, "a") == "a"
    assert unstructure(str, "b") == "b"

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(str, 1)
    assert e.value.ctx.structured_type is str
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 1

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(str, 1.0)
    assert e.value.ctx.structured_type is str
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 1.0

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(str, True)
    assert e.value.ctx.structured_type is str
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == True


def test_unstructure_enum():
    class Foo(Enum):
        A = 1
        B = 2

    assert unstructure(Foo, Foo.A) == 1
    assert unstructure(Foo, Foo.B) == 2

    with pytest.raises(Exception):
        unstructure(Foo, 1)

    with pytest.raises(Exception):
        unstructure(Foo, 3)

    class Bar(Enum):
        A = "a"
        B = "b"

    assert unstructure(Bar, Bar.A) == "a"
    assert unstructure(Bar, Bar.B) == "b"

    with pytest.raises(Exception):
        unstructure(Bar, "a")

    with pytest.raises(Exception):
        unstructure(Bar, "c")


def test_unstructure_int_enum():
    class Foo(IntEnum):
        A = 1
        B = 2

    assert unstructure(Foo, Foo.A) == 1
    assert unstructure(Foo, Foo.B) == 2

    with pytest.raises(Exception):
        unstructure(Foo, 3)


def test_unstructure_str_enum():
    class Bar(StrEnum):
        A = "a"
        B = "b"

    assert unstructure(Bar, Bar.A) == "a"
    assert unstructure(Bar, Bar.B) == "b"

    with pytest.raises(Exception):
        unstructure(Bar, "c")


def test_unstructure_path():
    path = Path("/a/b/c")
    assert unstructure(Path, path) == str(path)


def test_unstructure_uuid():
    uuid = UUID("51801a3b-8247-4201-9ada-107a02527a48")
    assert unstructure(UUID, uuid) == str(uuid)


def test_unstructure_decimal():
    assert unstructure(Decimal, Decimal("1.23")) == "1.23"
    assert unstructure(Decimal, Decimal("0")) == "0"
    assert unstructure(Decimal, Decimal("-1E+10")) == "-1E+10"

    for rejected in (1, 1.23, True):
        with pytest.raises(NoUnstructureHook) as e:
            unstructure(Decimal, rejected)
        assert e.value.ctx.structured_type is Decimal
        assert e.value.data == rejected


def test_unstructure_bytes():
    assert unstructure(bytes, b"") == ""
    assert unstructure(bytes, b"abc") == "YWJj"
    assert unstructure(bytes, b"\x00\x01\x02\xff") == "AAEC/w=="
    assert unstructure(Any, b"abc") == "YWJj"

    for rejected in (1, 1.23, True, "not bytes"):
        with pytest.raises(NoUnstructureHook) as e:
            unstructure(bytes, rejected)
        assert e.value.ctx.structured_type is bytes
        assert e.value.data == rejected

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(object, b"abc")
    assert e.value.ctx.structured_type is object
    assert e.value.data == b"abc"


def test_unstructure_date():
    d = date(2026, 1, 2)
    assert unstructure(date, d) == "2026-01-02"


def test_unstructure_datetime():
    dt = datetime(2026, 1, 2, 3, 4, 5)
    assert unstructure(datetime, dt) == "2026-01-02T03:04:05"


def test_unstructure_list():
    assert unstructure(list[int], []) == []
    assert unstructure(list[int], [1]) == [1]
    assert unstructure(list[int], [1, 2]) == [1, 2]

    assert unstructure(list[str], []) == []
    assert unstructure(list[str], ["a"]) == ["a"]
    assert unstructure(list[str], ["a", "b"]) == ["a", "b"]

    assert unstructure(list, []) == []
    assert unstructure(list, [1]) == [1]
    assert unstructure(list, [1, "a"]) == [1, "a"]
    assert unstructure(list, [[1]]) == [[1]]

    assert unstructure(list[Any], []) == []
    assert unstructure(list[Any], [1]) == [1]
    assert unstructure(list[Any], [1, "a"]) == [1, "a"]
    assert unstructure(list[Any], [[1]]) == [[1]]

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(list[int], [1, "1"])
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$[1]"
    assert e.value.ctx.unstructured_path == "$[1]"
    assert e.value.data == "1"

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(list[int], 1)
    assert e.value.ctx.structured_type == list[int]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 1

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(list[str], "abc")
    assert e.value.ctx.structured_type == list[str]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == "abc"

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(object, [1, 2])
    assert e.value.ctx.structured_type is object
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == [1, 2]


def test_unstructure_sequence():
    assert unstructure(Sequence[int], []) == []
    assert unstructure(Sequence[int], [1]) == [1]
    assert unstructure(Sequence[int], [1, 2]) == [1, 2]

    assert unstructure(Sequence[str], []) == []
    assert unstructure(Sequence[str], ["a"]) == ["a"]
    assert unstructure(Sequence[str], ["a", "b"]) == ["a", "b"]

    assert unstructure(Sequence, []) == []
    assert unstructure(Sequence, [1]) == [1]
    assert unstructure(Sequence, [1, "a"]) == [1, "a"]
    assert unstructure(Sequence, [[1]]) == [[1]]

    assert unstructure(Sequence[Any], []) == []
    assert unstructure(Sequence[Any], [1]) == [1]
    assert unstructure(Sequence[Any], [1, "a"]) == [1, "a"]
    assert unstructure(Sequence[Any], [[1]]) == [[1]]

    assert unstructure(Sequence[int], ()) == []
    assert unstructure(Sequence[int], (1,)) == [1]
    assert unstructure(Sequence[int], (1, 2)) == [1, 2]

    assert unstructure(Sequence[str], ()) == []
    assert unstructure(Sequence[str], ("a",)) == ["a"]
    assert unstructure(Sequence[str], ("a", "b")) == ["a", "b"]

    assert unstructure(Sequence, ()) == []
    assert unstructure(Sequence, (1,)) == [1]
    assert unstructure(Sequence, (1, "a")) == [1, "a"]
    assert unstructure(Sequence, ((1,),)) == [[1]]

    assert unstructure(Sequence[Any], ()) == []
    assert unstructure(Sequence[Any], (1,)) == [1]
    assert unstructure(Sequence[Any], (1, "a")) == [1, "a"]
    assert unstructure(Sequence[Any], ((1,),)) == [[1]]

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(Sequence[int], [1, "1"])
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$[1]"
    assert e.value.ctx.unstructured_path == "$[1]"
    assert e.value.data == "1"

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(Sequence[int], 1)
    assert e.value.ctx.structured_type == Sequence[int]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 1

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(Sequence[str], "abc")
    assert e.value.ctx.structured_type == Sequence[str]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == "abc"


def test_unstructure_tuple():
    assert unstructure(tuple[()], ()) == []
    assert unstructure(tuple[int], (1,)) == [1]
    assert unstructure(tuple[int, str], (1, "a")) == [1, "a"]

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(tuple[()], (1,))
    assert e.value.ctx.structured_type == tuple[()]
    assert e.value.data == (1,)

    assert unstructure(tuple, ()) == []
    assert unstructure(tuple, (1,)) == [1]
    assert unstructure(tuple, (1, "a")) == [1, "a"]
    assert unstructure(tuple, ((1,),)) == [[1]]

    assert unstructure(tuple[Any, ...], ()) == []
    assert unstructure(tuple[Any, ...], (1,)) == [1]
    assert unstructure(tuple[Any, ...], (1, "a")) == [1, "a"]
    assert unstructure(tuple[Any, ...], ((1,),)) == [[1]]

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(tuple[int], (1, "1"))
    assert e.value.ctx.structured_type == tuple[int]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == (1, "1")

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(tuple[int, float], (1, "1"))
    assert e.value.ctx.structured_type is float
    assert e.value.ctx.structured_path == "$[1]"
    assert e.value.ctx.unstructured_path == "$[1]"
    assert e.value.data == "1"

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(tuple[int], 1)
    assert e.value.ctx.structured_type == tuple[int]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 1

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(tuple[str], "abc")
    assert e.value.ctx.structured_type == tuple[str]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == "abc"


def test_unstructure_set():
    assert unstructure(set[int], set()) == []
    assert unstructure(set[int], {1}) == [1]
    assert unstructure(set[int], {1, 2}) == [1, 2]

    assert unstructure(set[str], set()) == []
    assert unstructure(set[str], {"a"}) == ["a"]
    _assert_set_list(unstructure(set[str], {"a", "b"}), ["a", "b"])

    assert unstructure(set, set()) == []
    assert unstructure(set, {1}) == [1]
    _assert_set_list(unstructure(set, {1, "a"}), [1, "a"])
    assert unstructure(set, {(1,)}) == [[1]]

    assert unstructure(set[Any], set()) == []
    assert unstructure(set[Any], {1}) == [1]
    _assert_set_list(unstructure(set, {1, "a"}), [1, "a"])
    assert unstructure(set[Any], {(1,)}) == [[1]]

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(set[int], {"1"})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$[?]"
    assert e.value.ctx.unstructured_path == "$[0]"
    assert e.value.data == "1"

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(set[int], 1)
    assert e.value.ctx.structured_type == set[int]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 1

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(set[str], "abc")
    assert e.value.ctx.structured_type == set[str]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == "abc"


def test_unstructure_frozenset():
    assert unstructure(frozenset[int], frozenset()) == []
    assert unstructure(frozenset[int], frozenset({1})) == [1]
    assert unstructure(frozenset[int], frozenset({1, 2})) == [1, 2]

    assert unstructure(frozenset[str], frozenset()) == []
    assert unstructure(frozenset[str], frozenset({"a"})) == ["a"]
    _assert_set_list(unstructure(frozenset[str], frozenset({"a", "b"})), ["a", "b"])

    assert unstructure(frozenset, frozenset()) == []
    assert unstructure(frozenset, frozenset({1})) == [1]
    _assert_set_list(unstructure(frozenset, frozenset({1, "a"})), [1, "a"])
    assert unstructure(frozenset, frozenset({frozenset({1})})) == [[1]]

    assert unstructure(frozenset[Any], frozenset()) == []
    assert unstructure(frozenset[Any], frozenset({1})) == [1]
    _assert_set_list(unstructure(frozenset, frozenset({1, "a"})), [1, "a"])
    assert unstructure(frozenset[Any], frozenset({frozenset({1})})) == [[1]]

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(frozenset[int], frozenset({"1"}))
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$[?]"
    assert e.value.ctx.unstructured_path == "$[0]"
    assert e.value.data == "1"

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(frozenset[int], 1)
    assert e.value.ctx.structured_type == frozenset[int]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 1

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(frozenset[str], "abc")
    assert e.value.ctx.structured_type == frozenset[str]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == "abc"


def test_unstructure_dict():
    assert unstructure(dict[str, int], {}) == {}
    assert unstructure(dict[str, int], {"a": 1}) == {"a": 1}
    assert unstructure(dict[str, int], {"a": 1, "b": 2}) == {"a": 1, "b": 2}

    assert unstructure(dict[int, int], {1: 2}) == {"1": 2}
    assert unstructure(dict[int, str], {-1: "x"}) == {"-1": "x"}
    assert unstructure(dict[date, int], {date(2000, 1, 2): 3}) == {"2000-01-02": 3}
    assert unstructure(dict[Literal["a"], int], {"a": 1}) == {"a": 1}
    assert unstructure(dict[Literal[1], int], {1: 2}) == {"1": 2}

    assert unstructure(dict[int, float], {True: False}) == {"True": 0.0}

    class Foo(Enum):
        A = "a"
        B = "b"

    assert unstructure(dict[Enum, int], {Foo.A: 1}) == {"a": 1}
    assert unstructure(dict[Enum, int], {Foo.B: 1}) == {"b": 1}
    assert unstructure(dict[Literal[Foo.A], int], {Foo.A: 1}) == {"a": 1}

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(dict[str, int], {"a": "1"})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$['a']"
    assert e.value.ctx.unstructured_path == "$['a']"
    assert e.value.data == "1"

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(dict[Literal["a"], int], {"a": "1"})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$['a']"
    assert e.value.ctx.unstructured_path == "$['a']"
    assert e.value.data == "1"

    with pytest.raises(ValidationError) as e:
        unstructure(dict[bool, int], {True: 1})
    assert e.value.ctx.structured_type is bool
    assert e.value.ctx.structured_path == "$[~?]"
    assert e.value.ctx.unstructured_path == "$[~?]"
    assert e.value.data == True

    with pytest.raises(ValidationError) as e:
        unstructure(dict[float, int], {1.1: 2})
    assert e.value.ctx.structured_type is float
    assert e.value.ctx.structured_path == "$[~?]"
    assert e.value.ctx.unstructured_path == "$[~?]"
    assert e.value.data == 1.1

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(dict[str, int], [])
    assert e.value.ctx.structured_type == dict[str, int]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == []

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(dict[str, int], "abc")
    assert e.value.ctx.structured_type == dict[str, int]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == "abc"


def test_unstructure_literal_dict_key_edge_cases():
    class Color(Enum):
        RED = 1
        BLUE = 2

    assert unstructure(dict[Literal[b"\x00"], int], {b"\x00": 1}) == {"AA==": 1}

    with pytest.raises(ValidationError) as e:
        unstructure(dict[Literal[True], int], {True: 1})
    assert e.value.ctx.structured_type == Literal[True]
    assert e.value.data is True

    with pytest.raises(ValidationError) as e:
        unstructure(dict[Literal[False], int], {True: 1})
    assert e.value.ctx.structured_type == Literal[False]
    assert e.value.data is True

    with pytest.raises(ValidationError) as e:
        unstructure(dict[Literal[2], int], {1: 1})
    assert e.value.ctx.structured_type == Literal[2]
    assert e.value.data == 1

    with pytest.raises(ValidationError) as e:
        unstructure(dict[Literal[2.0], int], {1.5: 1})
    assert e.value.ctx.structured_type == Literal[2.0]
    assert e.value.data == 1.5

    with pytest.raises(ValidationError) as e:
        unstructure(dict[Literal[Color.RED], int], {Color.BLUE: 1})
    assert e.value.ctx.structured_type == Literal[Color.RED]
    assert e.value.data is Color.BLUE

    with pytest.raises(ValidationError) as e:
        unstructure(dict[Literal[1], int], {None: 1})
    assert e.value.ctx.structured_type == Literal[1]
    assert e.value.data is None


def test_unstructure_dataclass():
    @dataclass
    class Foo:
        pass

    assert unstructure(Foo, Foo()) == {}

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(Foo, 1)
    assert e.value.ctx.structured_type is Foo
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 1

    @dataclass
    class Bar:
        a: float

    assert unstructure(Bar, Bar(1.1)) == {"a": 1.1}
    assert unstructure(Bar, Bar(1)) == {"a": 1.0}

    # `unstructure` recognizes fields of the declared dataclass type, not dataclass type itself.
    assert unstructure(Foo, Bar(1)) == {}

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(Bar, 1)
    assert e.value.ctx.structured_type is Bar
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 1

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(Bar, Bar("x"))  # type: ignore
    assert e.value.ctx.structured_type is float
    assert e.value.ctx.structured_path == "$.a"
    assert e.value.ctx.unstructured_path == "$['a']"
    assert e.value.data == "x"

    @dataclass
    class Baz(Bar):
        b: str

    assert unstructure(Baz, Baz(1.1, "xyz")) == {"a": 1.1, "b": "xyz"}
    assert unstructure(Bar, Baz(1.1, "xyz")) == {"a": 1.1}
    assert unstructure(Any, Baz(1.1, "xyz")) == {"a": 1.1, "b": "xyz"}

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(Baz, 1)
    assert e.value.ctx.structured_type is Baz
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 1

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(Baz, Baz(1, 2))  # type: ignore
    assert e.value.ctx.structured_type is str
    assert e.value.ctx.structured_path == "$.b"
    assert e.value.ctx.unstructured_path == "$['b']"
    assert e.value.data == 2

    @dataclass
    class Qux:
        p: Any
        q: Bar
        r: Baz

    assert unstructure(Qux, Qux(Bar(0.0), Baz(1.1, "xyz"), Baz(2.2, "lmn"))) == {
        "p": {"a": 0.0},
        "q": {"a": 1.1},
        "r": {"a": 2.2, "b": "lmn"},
    }
    assert unstructure(Any, Qux(Bar(0.0), Baz(1.1, "xyz"), Baz(2.2, "lmn"))) == {
        "p": {"a": 0.0},
        "q": {"a": 1.1, "b": "xyz"},
        "r": {"a": 2.2, "b": "lmn"},
    }

    with pytest.raises(AttributeError):
        unstructure(Qux, Qux(Foo(), Foo(), Baz(0.0, "a")))  # type: ignore


def test_unstructure_typeddict():
    class Foo(TypedDict):
        a: int
        b: str

    assert unstructure(Foo, {"a": 1, "b": "x"}) == {"a": 1, "b": "x"}

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(Foo, 1)
    assert e.value.ctx.structured_type is Foo
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 1

    assert unstructure(Foo, {"a": 1}) == {"a": 1}
    assert unstructure(Foo, {}) == {}

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(Foo, {"a": "x", "b": "y"})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$.a"
    assert e.value.ctx.unstructured_path == "$['a']"
    assert e.value.data == "x"


def test_unstructure_typeddict_extras_dropped():
    class Foo(TypedDict):
        a: int

    assert unstructure(Foo, {"a": 1, "extra": 99}) == {"a": 1}
    assert unstructure(Foo, {"a": 1, "x": "y", "z": 0}) == {"a": 1}


def test_unstructure_typeddict_total_false():
    class Foo(TypedDict, total=False):
        a: int
        b: str

    assert unstructure(Foo, {"a": 1, "b": "x"}) == {"a": 1, "b": "x"}
    assert unstructure(Foo, {"a": 1}) == {"a": 1}
    assert unstructure(Foo, {}) == {}


def test_unstructure_typeddict_required_notrequired():
    class Foo(TypedDict):
        a: int
        b: NotRequired[str]

    assert unstructure(Foo, {"a": 1, "b": "x"}) == {"a": 1, "b": "x"}
    assert unstructure(Foo, {"a": 1}) == {"a": 1}
    assert unstructure(Foo, {"b": "x"}) == {"b": "x"}

    class Bar(TypedDict, total=False):
        a: int
        b: Required[str]

    assert unstructure(Bar, {"a": 1, "b": "x"}) == {"a": 1, "b": "x"}
    assert unstructure(Bar, {"b": "x"}) == {"b": "x"}
    assert unstructure(Bar, {"a": 1}) == {"a": 1}


def test_unstructure_typeddict_inheritance():
    class Base(TypedDict):
        a: int

    class Sub(Base):
        b: str

    assert unstructure(Sub, {"a": 1, "b": "x"}) == {"a": 1, "b": "x"}
    assert unstructure(Sub, {"a": 1}) == {"a": 1}


def test_unstructure_typeddict_generic():
    T = TypeVar("T")

    class GenTD(TypedDict, Generic[T]):
        x: T

    assert unstructure(GenTD[int], {"x": 42}) == {"x": 42}
    assert unstructure(GenTD[datetime], {"x": datetime(2026, 1, 2, 3, 4, 5)}) == {"x": "2026-01-02T03:04:05"}

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(GenTD[int], {"x": "not-an-int"})
    assert e.value.ctx.structured_type is int


def test_unstructure_typeddict_nonidentifier_names():
    Foo = TypedDict("Foo", {"foo-bar": int, "x y": str})

    assert unstructure(Foo, {"foo-bar": 1, "x y": "hello"}) == {"foo-bar": 1, "x y": "hello"}

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(Foo, {"foo-bar": "bad", "x y": "ok"})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$.foo-bar"

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(Foo, {"foo-bar": 1, "x y": 99})
    assert e.value.ctx.structured_type is str
    assert e.value.ctx.structured_path == "$.'x y'"


def test_unstructure_typeddict_optional_field_appears_later():
    class Foo(TypedDict):
        a: int
        b: NotRequired[str]

    class Bar(TypedDict, total=False):
        a: int
        b: NotRequired[int]

    # First call without optional `b`, then later call with `b` present.
    assert unstructure(Foo, {"a": 1}) == {"a": 1}
    assert unstructure(Foo, {"a": 1, "b": "x"}) == {"a": 1, "b": "x"}
    assert unstructure(Foo, {"a": 2, "b": "y"}) == {"a": 2, "b": "y"}
    assert unstructure(Foo, {"a": 3}) == {"a": 3}

    # Same pattern with all-optional TypedDict.
    assert unstructure(Bar, {}) == {}
    assert unstructure(Bar, {"a": 1}) == {"a": 1}
    assert unstructure(Bar, {"a": 1, "b": 2}) == {"a": 1, "b": 2}
    assert unstructure(Bar, {"b": 2}) == {"b": 2}


def test_unstructure_typeddict_closed():
    class Foo(ExtTypedDict, closed=True):
        a: int

    # Closed TypedDict: extra keys in data are silently dropped during unstructure.
    assert unstructure(Foo, {"a": 1}) == {"a": 1}
    assert unstructure(Foo, {"a": 1, "extra": 99}) == {"a": 1}
    assert unstructure(Foo, {"a": 1, "x": 1, "y": 2}) == {"a": 1}


def test_unstructure_typeddict_extra_items_typed():
    class Foo(ExtTypedDict, extra_items=int):
        a: str

    assert unstructure(Foo, {"a": "hi", "x": 1, "y": 2}) == {"a": "hi", "x": 1, "y": 2}
    assert unstructure(Foo, {"a": "hi"}) == {"a": "hi"}

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(Foo, {"a": "hi", "bad": "not-an-int"})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$.bad"
    assert e.value.ctx.unstructured_path == "$['bad']"
    assert e.value.ctx.structured_key == "bad"
    assert e.value.ctx.parent is not None
    assert e.value.ctx.parent.structured_type is Foo


def test_unstructure_typeddict_extra_items_readonly():
    class Foo(ExtTypedDict, extra_items=ReadOnly[int]):
        a: str

    assert unstructure(Foo, {"a": "hi", "extra": 1}) == {"a": "hi", "extra": 1}

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(Foo, {"a": "bad", "extra": "not-an-int"})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$.extra"


def test_unstructure_typeddict_extra_items_readonly_type_alias():
    Int = TypeAliasType("Int", ReadOnly[int])  # type: ignore

    class Foo(ExtTypedDict, extra_items=Int):  # type: ignore
        a: str

    assert unstructure(Foo, {"a": "hi", "extra": 1}) == {"a": "hi", "extra": 1}

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(Foo, {"a": "bad", "extra": "not-an-int"})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$.extra"


def test_unstructure_typeddict_extra_items_complex_type():
    class Foo(ExtTypedDict, extra_items=list[int]):
        a: int

    assert unstructure(Foo, {"a": 1, "xs": [1, 2, 3]}) == {"a": 1, "xs": [1, 2, 3]}


def test_unstructure_typeddict_legacy_default_unchanged():
    class Foo(TypedDict):
        a: int

    # Open (default) TypedDict: extra keys in data are silently dropped.
    assert unstructure(Foo, {"a": 1, "extra": 99}) == {"a": 1}


def test_unstructure_typeddict_inheritance_closedness():
    class Base(ExtTypedDict, closed=True):
        a: int

    class Sub(Base):
        pass

    assert unstructure(Sub, {"a": 1}) == {"a": 1}
    assert unstructure(Sub, {"a": 1, "extra": 99}) == {"a": 1}


def test_unstructure_typeddict_inheritance_extra_items():
    class Base(ExtTypedDict, extra_items=int):
        a: str

    class Sub(Base):
        pass

    assert unstructure(Sub, {"a": "hi", "x": 1, "y": 2}) == {"a": "hi", "x": 1, "y": 2}


def test_unstructure_typeddict_inheritance_subclass_narrows_to_closed():
    class Base(ExtTypedDict):
        a: int

    class Sub(Base, closed=True):
        pass

    assert unstructure(Sub, {"a": 1}) == {"a": 1}
    assert unstructure(Sub, {"a": 1, "extra": 99}) == {"a": 1}


def test_unstructure_typeddict_generic_with_closed():
    T = TypeVar("T")

    class GenTD(ExtTypedDict, Generic[T], closed=True):
        x: T

    assert unstructure(GenTD[int], {"x": 42}) == {"x": 42}
    assert unstructure(GenTD[int], {"x": 42, "extra": 1}) == {"x": 42}


def test_unstructure_typeddict_generic_with_extra_items():
    T = TypeVar("T")

    class Bag(ExtTypedDict, Generic[T], extra_items=T):
        name: str

    assert unstructure(Bag[int], {"name": "ok", "extra": 1}) == {"name": "ok", "extra": 1}

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(Bag[int], {"name": "bad", "extra": "not-an-int"})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$.extra"


def test_unstructure_typeddict_generic_with_complex_extra_items():
    T = TypeVar("T")

    class Bag(ExtTypedDict, Generic[T], extra_items=list[T]):
        name: str

    assert unstructure(Bag[int], {"name": "ok", "extra": [1, 2]}) == {"name": "ok", "extra": [1, 2]}

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(Bag[int], {"name": "bad", "extra": ["not-an-int"]})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$.extra[0]"


def test_unstructure_typeddict_generic_inherited_extra_items():
    T = TypeVar("T")

    class Base(ExtTypedDict, Generic[T], extra_items=T):
        name: str

    class Bag(Base[T]):
        label: NotRequired[str]

    assert unstructure(Bag[int], {"name": "ok", "label": "bag", "extra": 1}) == {
        "name": "ok",
        "label": "bag",
        "extra": 1,
    }

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(Bag[int], {"name": "bad", "label": "bag", "extra": "not-an-int"})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$.extra"


def test_unstructure_typeddict_extra_items_direct_specialized_base():
    T = TypeVar("T")

    class Base(ExtTypedDict, Generic[T], extra_items=T):
        pass

    class Leaf(Base[list[int]]):  # type: ignore
        pass

    assert unstructure(Leaf, {"x": [1]}) == {"x": [1]}

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(Leaf, {"x": ["bad"]})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$.x[0]"


def test_unstructure_typeddict_extra_items_inherited_specialized_base():
    T = TypeVar("T")

    class Base(ExtTypedDict, Generic[T], extra_items=T):
        pass

    class Mid(Base[list[T]], Generic[T]):  # type: ignore
        pass

    class Leaf(Mid[int]):
        pass

    assert unstructure(Leaf, {"x": [1]}) == {"x": [1]}

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(Leaf, {"x": ["bad"]})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$.x[0]"


def test_unstructure_typeddict_extra_items_non_string_key():
    class Foo(ExtTypedDict, extra_items=int):
        a: int

    data = {"a": 1, 1: 2}
    with pytest.raises(ValidationError) as e:
        unstructure(Foo, data)
    assert "TypedDict extra key must be str, got int: 1" in str(e.value)
    assert e.value.data is data
    assert e.value.ctx.structured_type is Foo
    assert e.value.ctx.structured_path == "$"


def test_unstructure_generic_dataclass():
    T = TypeVar("T")

    @dataclass
    class Foo(Generic[T]):
        a: T

    assert unstructure(Foo[int], Foo[int](1)) == {"a": 1}
    assert unstructure(Foo[int], Foo(1)) == {"a": 1}
    assert unstructure(Foo[str], Foo[str]("x")) == {"a": "x"}
    assert unstructure(Foo, Foo(1)) == {"a": 1}
    assert unstructure(Foo, Foo[int](1)) == {"a": 1}
    assert unstructure(Foo, Foo[Any](1)) == {"a": 1}
    assert unstructure(Foo[Any], Foo(1)) == {"a": 1}
    assert unstructure(Foo[Any], Foo[int](1)) == {"a": 1}
    assert unstructure(Foo[Any], Foo[Any](1)) == {"a": 1}

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(Foo[int], Foo[str]("a"))
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$.a"
    assert e.value.ctx.unstructured_path == "$['a']"
    assert e.value.data == "a"

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(Foo[int], Foo("a"))
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$.a"
    assert e.value.ctx.unstructured_path == "$['a']"
    assert e.value.data == "a"

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(Foo[int], 1)
    assert e.value.ctx.structured_type == Foo[int]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 1


def test_unstructure_any_leaf():
    assert unstructure(Any, None) is None
    assert unstructure(Any, 1) == 1
    assert unstructure(Any, 1.1) == 1.1
    assert unstructure(Any, True) == True
    assert unstructure(Any, False) == False
    assert unstructure(Any, "a") == "a"
    assert unstructure(Any, Path("a/b/c")) == "a/b/c"
    uuid = UUID("51801a3b-8247-4201-9ada-107a02527a48")
    assert unstructure(Any, uuid) == str(uuid)
    assert unstructure(Any, date(2026, 1, 2)) == "2026-01-02"
    assert unstructure(Any, datetime(2026, 1, 2, 3, 4, 5)) == "2026-01-02T03:04:05"

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(Any, range(10))
    assert e.value.ctx.structured_type is Any
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == range(10)


def test_unstructure_any_collection_and_dataclass():
    @dataclass(frozen=True)
    class Foo:
        a: int

    assert unstructure(Any, []) == []
    assert unstructure(Any, [1]) == [1]
    assert unstructure(Any, [1, "a"]) == [1, "a"]
    assert unstructure(Any, [[1]]) == [[1]]
    assert unstructure(Any, [Foo(0), Foo(1)]) == [{"a": 0}, {"a": 1}]

    assert unstructure(Any, ()) == []
    assert unstructure(Any, (1,)) == [1]
    assert unstructure(Any, (1, "a")) == [1, "a"]
    assert unstructure(Any, ((1,),)) == [[1]]
    assert unstructure(Any, (Foo(0), Foo(1))) == [{"a": 0}, {"a": 1}]

    assert unstructure(Any, set()) == []
    assert unstructure(Any, {1}) == [1]
    _assert_set_list(unstructure(Any, {1, "a"}), [1, "a"])
    assert unstructure(Any, {(1,)}) == [[1]]
    _assert_set_list(unstructure(Any, {Foo(0), Foo(1)}), [{"a": 0}, {"a": 1}])

    assert unstructure(Any, frozenset()) == []
    assert unstructure(Any, frozenset({1})) == [1]
    _assert_set_list(unstructure(Any, frozenset({1, "a"})), [1, "a"])
    assert unstructure(Any, frozenset({frozenset({1})})) == [[1]]
    _assert_set_list(unstructure(Any, frozenset({Foo(0), Foo(1)})), [{"a": 0}, {"a": 1}])

    assert unstructure(Any, {}) == {}
    assert unstructure(Any, {"a": 1}) == {"a": 1}
    assert unstructure(Any, {"a": 1, "b": 2}) == {"a": 1, "b": 2}
    assert unstructure(Any, {"a": {"b": 1}}) == {"a": {"b": 1}}
    assert unstructure(Any, {"x": Foo(1), "y": Foo(2)}) == {"x": {"a": 1}, "y": {"a": 2}}


def test_unstructure_any_dict_non_string_key():
    with pytest.raises(ValidationError) as e:
        unstructure(Any, {1: "a"})
    assert "Dict key must unstructure to str" in str(e.value)


def test_unstructure_any_dataclass():
    @dataclass
    class Foo:
        a: int

    @dataclass
    class Bar(Foo):
        b: str

    assert unstructure(Any, Foo(1)) == {"a": 1}
    assert unstructure(Any, Foo("A")) == {"a": "A"}  # type: ignore
    assert unstructure(Any, Bar(1, "B")) == {"a": 1, "b": "B"}


def test_unstructure_any_generic_dataclass():
    T = TypeVar("T")

    @dataclass
    class Foo(Generic[T]):
        a: T

    assert unstructure(Any, Foo[int](1)) == {"a": 1}
    assert unstructure(Any, Foo[str]("A")) == {"a": "A"}
    assert unstructure(Any, Foo[int]("A")) == {"a": "A"}  # type: ignore


def test_unstructure_optional():
    assert unstructure(int | None, 1) == 1
    assert unstructure(None | int, 1) == 1
    assert unstructure(int | None, None) is None
    assert unstructure(None | int, None) is None
    assert unstructure(Optional[int], 1) == 1
    assert unstructure(Optional[int], None) is None
    assert unstructure(list[int | None], [1, None]) == [1, None]
    assert unstructure(list[Optional[int]], [1, None]) == [1, None]

    @dataclass
    class Foo:
        a: str | None

    assert unstructure(Foo, Foo("x")) == {"a": "x"}
    assert unstructure(Foo, Foo(None)) == {"a": None}

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(int | None, "a")
    assert e.value.ctx.structured_type == int | None
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == "a"

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(int, None)
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data is None

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(list[int], [1, None])
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.unstructured_path == "$[1]"
    assert e.value.ctx.unstructured_path == "$[1]"
    assert e.value.data is None


def test_unstructure_primitive_union():
    @dataclass
    class Foo:
        a: int | str

    assert unstructure(int | str, 1) == 1
    assert unstructure(int | str, "a") == "a"
    assert unstructure(Union[int, str], 1) == 1

    assert unstructure(int | float, 1.1) == 1.1
    assert unstructure(int | float, 1) == 1
    assert type(unstructure(int | float, 1)) is int

    assert unstructure(int | bool, True) is True
    assert unstructure(int | bool, 1) == 1

    assert unstructure(int | str | None, 1) == 1
    assert unstructure(int | str | None, "a") == "a"
    assert unstructure(int | str | None, None) is None

    assert unstructure(list | set, [1, 2]) == [1, 2]
    assert unstructure(list | set, {1, 2}) == [1, 2]
    assert unstructure(set | list, [1, 2]) == [1, 2]

    assert unstructure(tuple | list, (1, 2)) == [1, 2]
    assert unstructure(tuple | list, [1, 2]) == [1, 2]

    assert unstructure(list[int | str], [1, "a"]) == [1, "a"]
    assert unstructure(tuple[int | str, ...], (1, "a")) == [1, "a"]
    assert unstructure(tuple[int | str, float], (1, 1.1)) == [1, 1.1]
    assert unstructure(tuple[int | str, float], ("a", 1.1)) == ["a", 1.1]

    assert unstructure(date | str, "2000-01-01") == "2000-01-01"
    assert unstructure(date | str, date(2000, 1, 1)) == "2000-01-01"

    assert unstructure(Foo, Foo(1)) == {"a": 1}
    assert unstructure(Foo, Foo("x")) == {"a": "x"}

    with pytest.raises(AmbiguousUnion) as e:
        unstructure(list[int] | list[str], [1, 2])
    assert e.value.ctx.structured_type == list[int] | list[str]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == [1, 2]

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(int | str, 1.1)
    assert e.value.ctx.structured_type == int | str
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 1.1

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(int | str, None)
    assert e.value.ctx.structured_type == int | str
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data is None

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(list[int | str], [1, None])
    assert e.value.ctx.structured_type == int | str
    assert e.value.ctx.structured_path == "$[1]"
    assert e.value.ctx.unstructured_path == "$[1]"
    assert e.value.data is None

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(list[int | str], [1, 1.1])
    assert e.value.ctx.structured_type == int | str
    assert e.value.ctx.structured_path == "$[1]"
    assert e.value.ctx.unstructured_path == "$[1]"
    assert e.value.data == 1.1

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(tuple[int | str, ...], [1, 2, 1.1])
    assert e.value.ctx.structured_type == tuple[int | str, ...]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == [1, 2, 1.1]

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(Foo, Foo(1.1))  # type: ignore
    assert e.value.ctx.structured_type == int | str
    assert e.value.ctx.structured_path == "$.a"
    assert e.value.ctx.unstructured_path == "$['a']"
    assert e.value.data == 1.1


def test_unstructure_dataclass_union():
    @dataclass
    class Foo:
        a: int

    @dataclass
    class Bar:
        b: str

    assert unstructure(Foo | Bar, Foo(1)) == {"a": 1}
    assert unstructure(Foo | Bar, Bar("x")) == {"b": "x"}
    assert unstructure(Foo | int, 1) == 1
    assert unstructure(Foo | Bar | int, 1) == 1
    assert unstructure(Foo | Bar | int | str, 1) == 1

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(Foo | Bar, 1)
    assert e.value.ctx.structured_type == Foo | Bar
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 1


def test_unstructure_generic_dataclass_union():
    T = TypeVar("T")

    @dataclass
    class Foo(Generic[T]):
        a: T

    @dataclass
    class Bar(Generic[T]):
        b: T

    assert unstructure(Foo[int] | Bar[str], Foo[int](1)) == {"a": 1}
    assert unstructure(Foo[int] | Bar[str], Bar[str]("x")) == {"b": "x"}
    assert unstructure(Foo[int] | int, 1) == 1
    assert unstructure(Foo[int] | Bar[int] | int, 1) == 1
    assert unstructure(Foo[int] | Bar[str] | int | str, 1) == 1

    assert unstructure(Foo[int] | Foo[str], Foo[int](1)) == {"a": 1}
    assert unstructure(Foo[int] | Foo[str], Foo[str]("x")) == {"a": "x"}

    assert unstructure(Foo | Bar, Foo[int](1)) == {"a": 1}
    assert unstructure(Foo | Bar, Bar[str]("x")) == {"b": "x"}
    assert unstructure(Foo | Bar, Foo(1)) == {"a": 1}
    assert unstructure(Foo | Bar, Bar("x")) == {"b": "x"}

    assert unstructure(Foo | Foo[int], Foo[int](1)) == {"a": 1}
    assert unstructure(Foo | Foo[int], Foo[str]("x")) == {"a": "x"}
    assert unstructure(Foo | Foo[int], Foo(1)) == {"a": 1}

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(Foo[int] | Bar[str], Foo(1))
    assert e.value.ctx.structured_type == Foo[int] | Bar[str]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == Foo(1)

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(Foo[int] | Foo[str], Foo(1))
    assert e.value.ctx.structured_type == Foo[int] | Foo[str]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == Foo(1)

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(Foo[int] | Foo[str], Foo[float](1))
    assert e.value.ctx.structured_type == Foo[int] | Foo[str]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == Foo(1)

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(Foo[int] | Bar[int], 1)
    assert e.value.ctx.structured_type == Foo[int] | Bar[int]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 1


def test_unstructure_typeddict_union_members_in_hierarchy():
    class Base(TypedDict):
        x: int
        y: int

    class Extended(Base):
        z: int

    assert unstructure(Base | Extended, {"x": 1, "y": 2}) == {"x": 1, "y": 2}
    assert unstructure(Base | Extended, {"x": 1, "y": 2, "z": 3}) == {"x": 1, "y": 2, "z": 3}


def test_unstructure_generic_typeddict_union():
    T = TypeVar("T")

    class Foo(TypedDict, Generic[T]):
        a: T

    class Bar(TypedDict, Generic[T]):
        b: T

    assert unstructure(Foo[int] | Bar[str], {"a": 1}) == {"a": 1}
    assert unstructure(Foo[int] | Bar[str], {"b": "x"}) == {"b": "x"}
    assert unstructure(Foo[int] | str, {"a": 1}) == {"a": 1}
    assert unstructure(Foo[int] | str, "z") == "z"

    assert unstructure(Foo | Bar, {"a": 1}) == {"a": 1}
    assert unstructure(Foo | Bar, {"b": "x"}) == {"b": "x"}

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(Foo[int] | Bar[str], {"c": 1})
    assert e.value.ctx.structured_type == Foo[int] | Bar[str]
    assert e.value.data == {"c": 1}

    with pytest.raises(AmbiguousUnion) as e:
        unstructure(Foo[int] | Foo[str], {"a": 1})
    assert e.value.ctx.structured_type == Foo[int] | Foo[str]
    assert e.value.data == {"a": 1}

    with pytest.raises(AmbiguousUnion) as e:
        unstructure(Foo | Foo[str], {"a": 1})
    assert e.value.ctx.structured_type == Foo | Foo[str]
    assert e.value.data == {"a": 1}

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(Foo[int] | Bar[str], {"a": 1, "b": "x"})
    assert e.value.ctx.structured_type == Foo[int] | Bar[str]
    assert e.value.data == {"a": 1, "b": "x"}


def test_unstructure_typeddict_union():
    class Foo(TypedDict):
        a: int

    class Bar(TypedDict):
        b: str

    assert unstructure(Foo | Bar, {"a": 1}) == {"a": 1}
    assert unstructure(Foo | Bar, {"b": "x"}) == {"b": "x"}
    assert unstructure(Foo | str, {"a": 1}) == {"a": 1}
    assert unstructure(Foo | str, "z") == "z"

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(Foo | Bar, {"c": 1})
    assert e.value.ctx.structured_type == Foo | Bar
    assert e.value.data == {"c": 1}

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(Foo | Bar, {"a": 1, "b": "x"})
    assert e.value.ctx.structured_type == Foo | Bar
    assert e.value.data == {"a": 1, "b": "x"}


def test_unstructure_dataclass_typeddict_union():
    @dataclass
    class Foo:
        a: int

    class Bar(TypedDict):
        b: str

    assert unstructure(Foo | Bar, Foo(1)) == {"a": 1}
    assert unstructure(Foo | Bar, {"b": "x"}) == {"b": "x"}
    assert unstructure(Foo | Bar | str | int, Foo(5)) == {"a": 5}
    assert unstructure(Foo | Bar | str | int, {"b": "x"}) == {"b": "x"}
    assert unstructure(Foo | Bar | str | int, "z") == "z"
    assert unstructure(Foo | Bar | str | int, 9) == 9


def test_unstructure_union_duplicated_members():
    assert unstructure(int | str | int, 1) == 1
    assert unstructure(int | int, 1) == 1

    @dataclass
    class Foo:
        a: int

    @dataclass
    class Bar:
        b: int

    assert unstructure(Foo | Foo, Foo(1)) == {"a": 1}
    assert unstructure(Foo | Bar | Foo, Foo(1)) == {"a": 1}


IntOrStr = TypeAliasType("IntOrStr", int | str)


def test_unstructure_union_with_union_alias_member():
    assert unstructure(IntOrStr | None, 1) == 1
    assert unstructure(IntOrStr | None, "a") == "a"
    assert unstructure(IntOrStr | None, None) is None
    assert unstructure(IntOrStr | int, 1) == 1


def test_unstructure_literal_union():
    assert unstructure(Literal["a"] | int, "a") == "a"
    assert unstructure(Literal["a"] | int, 3) == 3

    with pytest.raises(NoUnstructureHook):
        unstructure(Literal["a"] | int, "b")


def test_unstructure_indistinguishable_union():
    class Foo(TypedDict):
        a: int

    class Bar(TypedDict):
        a: int

    with pytest.raises(AmbiguousUnion):
        unstructure(Foo | Bar, {"a": 1})


def test_declared_as_object():
    with pytest.raises(NoUnstructureHook):
        unstructure(object, 1)

    with pytest.raises(NoUnstructureHook):
        unstructure(object, Path("/a/b/c"))

    with pytest.raises(NoUnstructureHook):
        unstructure(object, UUID("51801a3b-8247-4201-9ada-107a02527a48"))

    with pytest.raises(NoUnstructureHook):
        unstructure(object, date(2026, 1, 2))

    with pytest.raises(NoUnstructureHook):
        unstructure(object, datetime(2026, 1, 2, 3, 4, 5))

    with pytest.raises(NoUnstructureHook):
        unstructure(object, 1)

    with pytest.raises(NoUnstructureHook):
        unstructure(object, [1, 2])

    with pytest.raises(NoUnstructureHook):
        unstructure(object, (1, 2))

    with pytest.raises(NoUnstructureHook):
        unstructure(object, {1, 2})

    with pytest.raises(NoUnstructureHook):
        unstructure(object, frozenset({1, 2}))

    with pytest.raises(NoUnstructureHook):
        unstructure(object, {"a": 1})

    @dataclass
    class Foo:
        pass

    with pytest.raises(NoUnstructureHook):
        unstructure(object, Foo())


def test_unstructure_literal():
    assert unstructure(Literal[None, True], True) == True
    assert unstructure(Literal[None, True], None) is None
    assert unstructure(Literal[1.0], 1.0) == 1.0
    assert unstructure(Literal[1, "a"], 1) == 1
    assert unstructure(Literal[1, "a"], "a") == "a"
    assert unstructure(Literal[b"\x00\x01\x02\xff"], b"\x00\x01\x02\xff") == "AAEC/w=="

    # `unstructure` does not validate the value against the Literal.
    assert unstructure(Literal[1, "a"], 2) == 2

    class Color(Enum):
        RED = 1
        GREEN = 2

    assert unstructure(Literal[Color.RED, Color.GREEN], Color.RED) == 1
    assert unstructure(Literal[Color.RED, Color.GREEN, 1], Color.GREEN) == 2


def test_unstructure_newtype():
    Int = NewType("Int", int)

    assert unstructure(Int, 1) == 1

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(Int, "1")
    assert e.value.ctx.structured_type is Int
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == "1"


def test_unstructure_newtype_union():
    Int = NewType("Int", int)
    Str = NewType("Str", str)

    assert unstructure(Int | Str, 1) == 1
    assert unstructure(Int | Str, "x") == "x"

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(Int | Str, 1.1)
    assert e.value.ctx.structured_type == Int | Str
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 1.1

    with pytest.raises(NoUnstructureHook) as e:
        unstructure(Int | Str, None)
    assert e.value.ctx.structured_type == Int | Str
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data is None


def _assert_set_list(x: set | frozenset, y: Any):
    assert type(y) is list
    assert len(x) == len(y)
    assert all(e in x for e in y)


@pytest.mark.parametrize("declared", [dict[tuple[int, int], int], Any])
def test_unstructure_dict_key_must_unstructure_to_str(declared):
    key = (1, 2)
    with pytest.raises(ValidationError) as e:
        unstructure(declared, {key: 3})
    assert "Dict key must unstructure to str, got list: [1, 2]" in str(e.value)
    assert e.value.data is key
    assert e.value.ctx.structured_path == "$[~?]"
