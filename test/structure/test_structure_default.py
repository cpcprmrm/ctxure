from collections.abc import Sequence
from dataclasses import InitVar, dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum, IntEnum, StrEnum
from pathlib import Path
from typing import Any, ClassVar, Generic, Literal, NewType, NotRequired, Optional, Required, TypedDict, TypeVar, Union
from uuid import UUID

import pytest
from typing_extensions import ReadOnly, TypeAliasType
from typing_extensions import TypedDict as ExtTypedDict

from ctxure import AmbiguousUnion, ExtraFields, MissingFields, NoStructureHook, ValidationError, structure


def test_structure_any():
    assert structure(Any, 1) == 1
    assert structure(Any, 1.1) == 1.1
    assert structure(Any, True) == True
    assert structure(Any, "a") == "a"
    assert structure(Any, None) is None


def test_structure_int():
    assert structure(int, 1) == 1
    assert structure(int, 2) == 2
    assert structure(int, True) == 1
    assert structure(int, False) == 0

    with pytest.raises(NoStructureHook) as e:
        structure(int, 1.0)
    assert e.value.ctx.structured_type is int
    assert e.value.data == 1.0

    with pytest.raises(NoStructureHook) as e:
        structure(int, "1")
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == "1"


def test_structure_bool():
    assert structure(bool, True) is True
    assert structure(bool, False) is False
    assert structure(bool, 1) is True
    assert structure(bool, -1) is True
    assert structure(bool, 0) is False

    with pytest.raises(NoStructureHook) as e:
        structure(bool, 1.0)
    assert e.value.ctx.structured_type is bool
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 1.0

    with pytest.raises(NoStructureHook) as e:
        structure(bool, "True")
    assert e.value.ctx.structured_type is bool
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == "True"


def test_structure_float():
    assert structure(float, 1.0) == 1.0
    assert structure(float, 1) == 1.0
    assert type(structure(float, 1)) is float
    assert structure(float, True) == 1.0
    assert type(structure(float, True)) is float
    assert structure(float, False) == 0.0
    assert type(structure(float, False)) is float

    with pytest.raises(NoStructureHook) as e:
        structure(float, "1.0")
    assert e.value.ctx.structured_type is float
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == "1.0"


def test_structure_str():
    assert structure(str, "a") == "a"
    assert structure(str, "b") == "b"

    with pytest.raises(NoStructureHook) as e:
        structure(str, 1)
    assert e.value.ctx.structured_type is str
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 1

    with pytest.raises(NoStructureHook) as e:
        structure(str, 1.0)
    assert e.value.ctx.structured_type is str
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 1.0

    with pytest.raises(NoStructureHook) as e:
        structure(str, True)
    assert e.value.ctx.structured_type is str
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == True


def test_structure_enum():
    class Foo(Enum):
        A = 1
        B = 2

    assert structure(Foo, 1) is Foo.A
    assert structure(Foo, 2) is Foo.B

    with pytest.raises(ValidationError) as e:
        structure(Foo, 3)
    assert e.value.ctx.structured_type is Foo
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 3

    class Bar(Enum):
        A = "a"
        B = "b"

    assert structure(Bar, "a") is Bar.A
    assert structure(Bar, "b") is Bar.B

    with pytest.raises(ValidationError) as e:
        structure(Bar, "c")
    assert e.value.ctx.structured_type is Bar
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == "c"


def test_structure_str_enum():
    class Foo(StrEnum):
        A = "a"
        B = "b"

    assert structure(Foo, "a") is Foo.A
    assert structure(Foo, "b") is Foo.B

    with pytest.raises(ValidationError) as e:
        structure(Foo, "c")
    assert e.value.ctx.structured_type is Foo
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == "c"


def test_structure_int_enum():
    class Foo(IntEnum):
        A = 1
        B = 2

    assert structure(Foo, 1) is Foo.A
    assert structure(Foo, 2) is Foo.B

    with pytest.raises(ValidationError) as e:
        structure(Foo, 3)
    assert e.value.ctx.structured_type is Foo
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 3


def test_structure_path():
    assert structure(Path, "/a/b/c") == Path("/a/b/c")


def test_structure_uuid():
    uuid = "51801a3b-8247-4201-9ada-107a02527a48"
    assert structure(UUID, uuid) == UUID(uuid)

    with pytest.raises(ValidationError) as e:
        assert structure(UUID, uuid[0:20])
    assert e.value.ctx.structured_type is UUID
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == uuid[0:20]

    with pytest.raises(NoStructureHook) as e:
        assert structure(UUID, 12345)
    assert e.value.ctx.structured_type is UUID
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 12345


def test_structure_decimal():
    assert structure(Decimal, "1.23") == Decimal("1.23")
    assert structure(Decimal, "0") == Decimal("0")
    assert structure(Decimal, "-1E+10") == Decimal("-1E+10")

    with pytest.raises(ValidationError) as e:
        structure(Decimal, "not a number")
    assert e.value.ctx.structured_type is Decimal
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == "not a number"

    for rejected in (1, 1.23, True):
        with pytest.raises(NoStructureHook) as e:
            structure(Decimal, rejected)
        assert e.value.ctx.structured_type is Decimal
        assert e.value.data == rejected


def test_structure_bytes():
    assert structure(bytes, "") == b""
    assert structure(bytes, "YWJj") == b"abc"
    assert structure(bytes, "AAEC/w==") == b"\x00\x01\x02\xff"

    with pytest.raises(ValidationError) as e:
        structure(bytes, "not valid base64!")
    assert e.value.ctx.structured_type is bytes
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == "not valid base64!"

    with pytest.raises(ValidationError):
        structure(bytes, "YW$Jj")

    for rejected in (1, 1.23, True, b"abc"):
        with pytest.raises(NoStructureHook) as e:
            structure(bytes, rejected)
        assert e.value.ctx.structured_type is bytes
        assert e.value.data == rejected


def test_structure_date():
    assert structure(date, "2025-01-01") == date(2025, 1, 1)

    with pytest.raises(ValidationError) as e:
        structure(date, "2025-12-31 10:30:00")
    assert e.value.ctx.structured_type is date
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == "2025-12-31 10:30:00"

    with pytest.raises(ValidationError) as e:
        structure(date, "invalid-date")
    assert e.value.ctx.structured_type is date
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == "invalid-date"

    with pytest.raises(ValidationError) as e:
        structure(date, "2025-13-01")
    assert e.value.ctx.structured_type is date
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == "2025-13-01"

    with pytest.raises(NoStructureHook) as e:
        structure(date, 1)
    assert e.value.ctx.structured_type is date
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 1


def test_structure_datetime():
    assert structure(datetime, "2025-01-15 10:30:00") == datetime(2025, 1, 15, 10, 30, 0)
    assert structure(datetime, "2025-01-15T10:30:00") == datetime(2025, 1, 15, 10, 30, 0)
    assert structure(datetime, "2025-01-15T10:30:00.123456") == datetime(2025, 1, 15, 10, 30, 0, 123456)
    assert structure(datetime, "2025-12-31T23:59:59") == datetime(2025, 12, 31, 23, 59, 59)
    assert structure(datetime, "2025-01-15") == datetime(2025, 1, 15, 0, 0, 0)

    with pytest.raises(ValidationError) as e:
        structure(datetime, "invalid-datetime")
    assert e.value.ctx.structured_type is datetime
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == "invalid-datetime"

    with pytest.raises(ValidationError) as e:
        structure(datetime, "2025-13-01T00:00:00")
    assert e.value.ctx.structured_type is datetime
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == "2025-13-01T00:00:00"

    with pytest.raises(NoStructureHook) as e:
        structure(datetime, 1)
    assert e.value.ctx.structured_type is datetime
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 1


def test_structure_list():
    assert structure(list[int], []) == []
    assert structure(list[int], [1]) == [1]
    assert structure(list[int], [1, 2]) == [1, 2]

    assert structure(list[str], ()) == []
    assert structure(list[str], ("a",)) == ["a"]
    assert structure(list[str], ("a", "b")) == ["a", "b"]

    assert structure(list[int], set()) == []
    assert structure(list[int], {1}) == [1]
    assert structure(list[int], {1, 2}) in ([1, 2], [2, 1])

    assert structure(list[str], frozenset()) == []
    assert structure(list[str], frozenset(["a"])) == ["a"]
    assert structure(list[str], frozenset(["a", "b"])) in [["a", "b"], ["b", "a"]]

    assert structure(list, [1, "a"]) == [1, "a"]
    assert structure(list[Any], [1, "a"]) == [1, "a"]
    assert structure(list, (1, "a")) == [1, "a"]
    assert structure(list[Any], (1, "a")) == [1, "a"]
    assert structure(list, {1, "a"}) in [[1, "a"], ["a", 1]]
    assert structure(list[Any], {1, "a"}) in [[1, "a"], ["a", 1]]
    assert structure(list, frozenset([1, "a"])) in [[1, "a"], ["a", 1]]
    assert structure(list[Any], frozenset([1, "a"])) in [[1, "a"], ["a", 1]]

    with pytest.raises(NoStructureHook) as e:
        structure(list[int], [1, "1"])
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$[1]"
    assert e.value.ctx.unstructured_path == "$[1]"
    assert e.value.data == "1"

    with pytest.raises(NoStructureHook) as e:
        structure(list[int], {"1"})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$[0]"
    assert e.value.ctx.unstructured_path == "$[?]"
    assert e.value.data == "1"

    with pytest.raises(NoStructureHook) as e:
        structure(list[int], 1)
    assert e.value.ctx.structured_type == list[int]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 1

    with pytest.raises(NoStructureHook) as e:
        structure(list[str], "abc")
    assert e.value.ctx.structured_type == list[str]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == "abc"


def test_structure_sequence():
    assert structure(Sequence[int], []) == []
    assert structure(Sequence[int], [1]) == [1]
    assert structure(Sequence[int], [1, 2]) == [1, 2]

    assert structure(Sequence[str], ()) == []
    assert structure(Sequence[str], ("a",)) == ["a"]
    assert structure(Sequence[str], ("a", "b")) == ["a", "b"]

    assert structure(Sequence[int], set()) == []
    assert structure(Sequence[int], {1}) == [1]
    assert structure(Sequence[int], {1, 2}) in ([1, 2], [2, 1])

    assert structure(Sequence[str], frozenset()) == []
    assert structure(Sequence[str], frozenset(["a"])) == ["a"]
    assert structure(Sequence[str], frozenset(["a", "b"])) in [["a", "b"], ["b", "a"]]

    assert structure(Sequence, [1, "a"]) == [1, "a"]
    assert structure(Sequence[Any], [1, "a"]) == [1, "a"]
    assert structure(Sequence, (1, "a")) == [1, "a"]
    assert structure(Sequence[Any], (1, "a")) == [1, "a"]
    assert structure(Sequence, {1, "a"}) in [[1, "a"], ["a", 1]]
    assert structure(Sequence[Any], {1, "a"}) in [[1, "a"], ["a", 1]]
    assert structure(Sequence, frozenset([1, "a"])) in [[1, "a"], ["a", 1]]
    assert structure(Sequence[Any], frozenset([1, "a"])) in [[1, "a"], ["a", 1]]

    with pytest.raises(NoStructureHook) as e:
        structure(Sequence[int], [1, "1"])
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$[1]"
    assert e.value.ctx.unstructured_path == "$[1]"
    assert e.value.data == "1"

    with pytest.raises(NoStructureHook) as e:
        structure(Sequence[int], {"1"})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$[0]"
    assert e.value.ctx.unstructured_path == "$[?]"
    assert e.value.data == "1"

    with pytest.raises(NoStructureHook) as e:
        structure(Sequence[int], 1)
    assert e.value.ctx.structured_type == Sequence[int]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 1

    with pytest.raises(NoStructureHook) as e:
        structure(Sequence[str], "abc")
    assert e.value.ctx.structured_type == Sequence[str]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == "abc"


def test_structure_collection():
    from collections.abc import Collection

    assert structure(Collection[int], [1, 2]) == [1, 2]
    assert structure(Collection[int], (1, 2)) == [1, 2]
    assert structure(Collection[str], ["a", "b"]) == ["a", "b"]

    with pytest.raises(NoStructureHook) as e:
        structure(Collection[int], [1, "x"])
    assert e.value.ctx.structured_type is int


def test_structure_tuple():
    assert structure(tuple[()], []) == ()
    assert structure(tuple[int], [1]) == (1,)
    assert structure(tuple[int, str], [1, "a"]) == (1, "a")

    assert structure(tuple[()], ()) == ()
    assert structure(tuple[str], ("a",)) == ("a",)
    assert structure(tuple[str, int], ("a", 1)) == ("a", 1)

    assert structure(tuple[()], set()) == ()
    assert structure(tuple[int], {1}) == (1,)
    assert structure(tuple[int, int], {1, 2}) in [(1, 2), (2, 1)]

    assert structure(tuple[()], frozenset()) == ()
    assert structure(tuple[str], frozenset(["a"])) == ("a",)
    assert structure(tuple[str, str], frozenset(["a", "b"])) in [("a", "b"), ("b", "a")]

    with pytest.raises(NoStructureHook) as e:
        structure(tuple[()], [1])
    assert e.value.ctx.structured_type == tuple[()]
    assert e.value.data == [1]

    assert structure(tuple, [1, "a", 1.1]) == (1, "a", 1.1)
    assert structure(tuple[Any, ...], [1, "a", 1.1]) == (1, "a", 1.1)
    assert structure(tuple, (1, "a", 1.1)) == (1, "a", 1.1)
    assert structure(tuple[Any, ...], (1, "a", 1.1)) == (1, "a", 1.1)
    assert structure(tuple, {1, 2}) in [(1, 2), (2, 1)]
    assert structure(tuple[Any, ...], {1, 1.1}) in [(1, 1.1), (1.1, 1)]
    assert structure(tuple, frozenset([1, 1.1])) in [(1, 1.1), (1.1, 1)]
    assert structure(tuple[Any, ...], frozenset([1, 1.1])) in [(1, 1.1), (1.1, 1)]
    assert structure(tuple[int, ...], [1, 2, 3]) == (1, 2, 3)

    assert structure(tuple[int, Any], [1, 2]) == (1, 2)
    assert structure(tuple[int, Any], [1, "a"]) == (1, "a")
    assert structure(tuple[Any, int], [1, 2]) == (1, 2)
    assert structure(tuple[Any, int], ["a", 2]) == ("a", 2)
    assert structure(tuple[Any, Any], [1, 2]) == (1, 2)
    assert structure(tuple[Any, Any], [1.1, 2.2]) == (1.1, 2.2)

    with pytest.raises(NoStructureHook) as e:
        structure(tuple[int, int], (1, "1"))
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$[1]"
    assert e.value.ctx.unstructured_path == "$[1]"
    assert e.value.data == "1"

    with pytest.raises(NoStructureHook) as e:
        structure(tuple[int], {"1"})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$[0]"
    assert e.value.ctx.unstructured_path == "$[?]"
    assert e.value.data == "1"

    with pytest.raises(NoStructureHook) as e:
        structure(tuple[int], (1, "1"))
    assert e.value.ctx.structured_type == tuple[int]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == (1, "1")

    with pytest.raises(NoStructureHook) as e:
        structure(tuple[int], 1)
    assert e.value.ctx.structured_type == tuple[int]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 1

    with pytest.raises(NoStructureHook) as e:
        structure(tuple[str], "a")
    assert e.value.ctx.structured_type == tuple[str]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == "a"


def test_structure_set():
    assert structure(set[int], []) == set()
    assert structure(set[int], [1]) == {1}
    assert structure(set[int], [1, 2]) == {1, 2}

    assert structure(set[str], ()) == set()
    assert structure(set[str], ("a",)) == {"a"}
    assert structure(set[str], ("a", "b")) == {"a", "b"}

    assert structure(set[int], set()) == set()
    assert structure(set[int], {1}) == {1}
    assert structure(set[int], {1, 2}) == {1, 2}

    assert structure(set[str], frozenset()) == set()
    assert structure(set[str], frozenset(["a"])) == {"a"}
    assert structure(set[str], frozenset(["a", "b"])) == {"a", "b"}

    assert type(structure(set[int], [1, 2])) is set
    assert type(structure(set[int], (1, 2))) is set
    assert type(structure(set[int], {1, 2})) is set
    assert type(structure(set[int], frozenset([1, 2]))) is set

    assert structure(set, [1, "a"]) == {1, "a"}
    assert structure(set[Any], [1, "a"]) == {1, "a"}
    assert structure(set, (1, "a")) == {1, "a"}
    assert structure(set[Any], (1, "a")) == {1, "a"}
    assert structure(set, {1, "a"}) == {1, "a"}
    assert structure(set[Any], {1, "a"}) == {1, "a"}
    assert structure(set, frozenset([1, "a"])) == {1, "a"}
    assert structure(set[Any], frozenset([1, "a"])) == {1, "a"}

    with pytest.raises(NoStructureHook) as e:
        structure(set[int], {1, "1"})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$[?]"
    assert e.value.ctx.unstructured_path == "$[?]"
    assert e.value.data == "1"

    with pytest.raises(NoStructureHook) as e:
        structure(set[int], [1, "1"])
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$[?]"
    assert e.value.ctx.unstructured_path == "$[1]"
    assert e.value.data == "1"

    with pytest.raises(NoStructureHook) as e:
        structure(set[int], 1)
    assert e.value.ctx.structured_type == set[int]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 1

    with pytest.raises(NoStructureHook) as e:
        structure(set[str], "abc")
    assert e.value.ctx.structured_type == set[str]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == "abc"


def test_structure_frozenset():
    assert structure(frozenset[int], []) == frozenset()
    assert structure(frozenset[int], [1]) == frozenset({1})
    assert structure(frozenset[int], [1, 2]) == frozenset({1, 2})

    assert structure(frozenset[str], ()) == frozenset()
    assert structure(frozenset[str], ("a",)) == frozenset({"a"})
    assert structure(frozenset[str], ("a", "b")) == frozenset({"a", "b"})

    assert structure(frozenset[int], frozenset()) == frozenset()
    assert structure(frozenset[int], {1}) == frozenset({1})
    assert structure(frozenset[int], {1, 2}) == frozenset({1, 2})

    assert structure(frozenset[str], frozenset()) == frozenset()
    assert structure(frozenset[str], frozenset(["a"])) == frozenset({"a"})
    assert structure(frozenset[str], frozenset(["a", "b"])) == frozenset({"a", "b"})

    assert type(structure(frozenset[int], [1, 2])) is frozenset
    assert type(structure(frozenset[int], (1, 2))) is frozenset
    assert type(structure(frozenset[int], {1, 2})) is frozenset
    assert type(structure(frozenset[int], frozenset([1, 2]))) is frozenset

    assert structure(frozenset, [1, "a"]) == frozenset({1, "a"})
    assert structure(frozenset[Any], [1, "a"]) == frozenset({1, "a"})
    assert structure(frozenset, (1, "a")) == frozenset({1, "a"})
    assert structure(frozenset[Any], (1, "a")) == frozenset({1, "a"})
    assert structure(frozenset, {1, "a"}) == frozenset({1, "a"})
    assert structure(frozenset[Any], {1, "a"}) == frozenset({1, "a"})
    assert structure(frozenset, frozenset([1, "a"])) == frozenset({1, "a"})
    assert structure(frozenset[Any], frozenset([1, "a"])) == frozenset({1, "a"})

    with pytest.raises(NoStructureHook) as e:
        structure(frozenset[int], frozenset([1, "1"]))
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$[?]"
    assert e.value.ctx.unstructured_path == "$[?]"
    assert e.value.data == "1"

    with pytest.raises(NoStructureHook) as e:
        structure(frozenset[int], [1, "1"])
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$[?]"
    assert e.value.ctx.unstructured_path == "$[1]"
    assert e.value.data == "1"

    with pytest.raises(NoStructureHook) as e:
        structure(frozenset[int], 1)
    assert e.value.ctx.structured_type == frozenset[int]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 1

    with pytest.raises(NoStructureHook) as e:
        structure(frozenset[str], "abc")
    assert e.value.ctx.structured_type == frozenset[str]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == "abc"


def test_structure_dict():
    assert structure(dict[str, int], {}) == {}
    assert structure(dict[str, int], {"a": 1}) == {"a": 1}
    assert structure(dict[str, int], {"a": 1, "b": 2}) == {"a": 1, "b": 2}

    assert structure(dict[int, int], {"1": 10, 2: 20}) == {1: 10, 2: 20}
    assert structure(dict[date, int], {"2000-01-02": 3}) == {date(2000, 1, 2): 3}
    assert structure(dict[Literal["a"], int], {"a": 1}) == {"a": 1}
    assert structure(dict[Literal[1], int], {"1": 10}) == {1: 10}

    class Foo(Enum):
        A = "a"
        B = "b"

    assert structure(dict[Foo, int], {"a": 1, "b": 2}) == {Foo.A: 1, Foo.B: 2}
    assert structure(dict[Literal[Foo.A], int], {"a": 1}) == {Foo.A: 1}
    assert structure(dict[int, Foo], {1: "a", 2: "b"}) == {1: Foo.A, 2: Foo.B}
    assert structure(dict[Foo, Path], {"a": "/a", "b": "/b"}) == {Foo.A: Path("/a"), Foo.B: Path("/b")}

    with pytest.raises(NoStructureHook) as e:
        structure(dict[str, int], {"a": "1"})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$['a']"
    assert e.value.ctx.unstructured_path == "$['a']"
    assert e.value.data == "1"

    with pytest.raises(NoStructureHook) as e:
        structure(dict[int, int], {1: "a"})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$[1]"
    assert e.value.ctx.unstructured_path == "$[1]"
    assert e.value.data == "a"

    with pytest.raises(NoStructureHook) as e:
        structure(dict[Literal["a"], int], {"a": "x"})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$['a']"
    assert e.value.ctx.unstructured_path == "$['a']"
    assert e.value.data == "x"

    with pytest.raises(NoStructureHook) as e:
        structure(dict[Foo, int], {"a": "x"})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$[Foo.A]"
    assert e.value.ctx.unstructured_path == "$['a']"
    assert e.value.data == "x"

    with pytest.raises(NoStructureHook) as e:
        structure(dict[str, int], {1: 2})
    assert e.value.ctx.structured_type is str
    assert e.value.ctx.structured_path == "$[~?]"
    assert e.value.ctx.unstructured_path == "$[~1]"
    assert e.value.data == 1

    with pytest.raises(NoStructureHook) as e:
        structure(dict[str, int], [])
    assert e.value.ctx.structured_type == dict[str, int]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == []

    with pytest.raises(NoStructureHook) as e:
        structure(dict[str, int], "abc")
    assert e.value.ctx.structured_type == dict[str, int]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == "abc"


def test_structure_dict_key_validation_errors():
    class Foo(Enum):
        A = "a"

    with pytest.raises(ValidationError) as e:
        structure(dict[int, int], {"x": 1})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$[~?]"
    assert e.value.ctx.unstructured_path == "$[~'x']"
    assert e.value.data == "x"
    assert "Cannot parse 'x' as int" in str(e.value)

    with pytest.raises(ValidationError) as e:
        structure(dict[Literal[True], int], {"True": 1})
    assert e.value.ctx.structured_type == Literal[True]
    assert e.value.data == "True"

    with pytest.raises(ValidationError) as e:
        structure(dict[Literal[1], int], {None: 1})
    assert e.value.ctx.structured_type == Literal[1]
    assert e.value.ctx.unstructured_path == "$[~?]"
    assert e.value.data is None

    with pytest.raises(ValidationError) as e:
        structure(dict[Literal[Foo.A], int], {"z": 1})
    assert e.value.ctx.structured_type == Literal[Foo.A]
    assert e.value.data == "z"


class _Color(Enum):
    RED = "red"


@pytest.mark.parametrize(
    "target, bad, message",
    [
        (_Color, "blue", "'blue' is not a valid value of"),
        (UUID, "not-a-uuid", "Cannot parse 'not-a-uuid' as <class 'uuid.UUID'>"),
        (Decimal, "not-a-decimal", "Cannot parse 'not-a-decimal' as <class 'decimal.Decimal'>"),
        (bytes, "YW$Jj", "Cannot decode 'YW$Jj' as base64"),
        (date, "not-a-date", "Cannot parse 'not-a-date' as <class 'datetime.date'>"),
        (datetime, "not-a-datetime", "Cannot parse 'not-a-datetime' as <class 'datetime.datetime'>"),
        (Literal[1, "a"], 2, "Expected one of 1, 'a', got 2"),
    ],
)
def test_structure_validation_error_message(target, bad, message):
    with pytest.raises(ValidationError) as e:
        structure(target, bad)
    assert message in str(e.value)
    assert e.value.data == bad


def test_structure_optional_field_explicit_none():
    @dataclass
    class Foo:
        a: int | None = 5

    class Bar(TypedDict):
        a: NotRequired[int | None]

    # An explicit None is a value, not a missing key.
    assert structure(Foo, {"a": None}) == Foo(None)
    assert structure(Foo, {}) == Foo(5)
    assert structure(Bar, {"a": None}) == {"a": None}
    assert structure(Bar, {}) == {}


def test_structure_dict_literal_key_conversion_skips_non_matching_members():
    class Foo(Enum):
        A = "A"

    # bool members are skipped, so "1" still converts to the int member.
    assert structure(dict[Literal[True, 1], int], {"1": 5}) == {1: 5}
    # A failed int conversion moves on to the enum member.
    assert structure(dict[Literal[1, Foo.A], int], {"A": 5}) == {Foo.A: 5}
    assert structure(dict[Literal[1, Foo.A], int], {"1": 5}) == {1: 5}


def test_structure_dataclass():
    @dataclass
    class Foo:
        pass

    assert structure(Foo, {}) == Foo()

    with pytest.raises(NoStructureHook) as e:
        structure(Foo, 1)
    assert e.value.ctx.structured_type is Foo
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 1

    with pytest.raises(ExtraFields) as e:
        structure(Foo, {"a": "x"})
    assert e.value.ctx.structured_type is Foo
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == {"a": "x"}
    assert e.value.extra == ["a"]

    @dataclass
    class Bar:
        a: float

    assert structure(Bar, {"a": 1.0}) == Bar(1.0)
    assert structure(Bar, {"a": 1}) == Bar(1)

    with pytest.raises(NoStructureHook) as e:
        structure(Bar, 1)
    assert e.value.ctx.structured_type is Bar
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 1

    with pytest.raises(NoStructureHook) as e:
        structure(Bar, {"a": "x"})
    assert e.value.ctx.structured_type is float
    assert e.value.ctx.structured_path == "$.a"
    assert e.value.ctx.unstructured_path == "$['a']"
    assert e.value.data == "x"

    with pytest.raises(ExtraFields) as e:
        structure(Bar, {"a": 0.1, "b": 1})
    assert e.value.ctx.structured_type is Bar
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == {"a": 0.1, "b": 1}
    assert e.value.extra == ["b"]

    with pytest.raises(MissingFields) as e:
        structure(Bar, {})
    assert e.value.ctx.structured_type is Bar
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == {}
    assert e.value.missing == ["a"]

    @dataclass
    class WithComputed:
        name: str
        slug: str = field(init=False)

        def __post_init__(self) -> None:
            self.slug = self.name.upper()

    assert structure(WithComputed, {"name": "book"}) == WithComputed("book")

    with pytest.raises(ExtraFields) as e:
        structure(WithComputed, {"name": "book", "slug": "manual"})
    assert e.value.ctx.structured_type is WithComputed
    assert e.value.extra == ["slug"]

    @dataclass
    class WithClassVar:
        name: str
        kind: ClassVar[str] = "item"

    assert structure(WithClassVar, {"name": "book"}) == WithClassVar("book")

    with pytest.raises(ExtraFields) as e:
        structure(WithClassVar, {"name": "book", "kind": "manual"})
    assert e.value.ctx.structured_type is WithClassVar
    assert e.value.extra == ["kind"]

    @dataclass
    class WithInitVar:
        name: str
        raw: InitVar[int]
        doubled: int = field(init=False)

        def __post_init__(self, raw: int) -> None:
            self.doubled = raw * 2

    assert structure(WithInitVar, {"name": "book", "raw": 3}) == WithInitVar("book", 3)

    with pytest.raises(MissingFields) as e:
        structure(WithInitVar, {"name": "book"})
    assert e.value.missing == ["raw"]

    @dataclass(init=False)
    class WithoutGeneratedInit:
        name: str

    with pytest.raises(NoStructureHook) as e:
        structure(WithoutGeneratedInit, {"name": "book"})
    assert e.value.ctx.structured_type is WithoutGeneratedInit
    assert e.value.data == {"name": "book"}

    @dataclass
    class WithCustomInit:
        name: str

        def __init__(self, raw: str) -> None:
            self.name = raw.upper()

    with pytest.raises(NoStructureHook) as e:
        structure(WithCustomInit, {"name": "book"})
    assert e.value.ctx.structured_type is WithCustomInit
    assert e.value.data == {"name": "book"}

    @dataclass
    class Baz:
        a: int
        b: str

    assert structure(Baz, {"a": 1, "b": "xyz"}) == Baz(1, "xyz")

    with pytest.raises(NoStructureHook) as e:
        structure(Baz, 1)
    assert e.value.ctx.structured_type is Baz
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 1

    with pytest.raises(NoStructureHook) as e:
        structure(Baz, {"a": "x", "b": "y"})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$.a"
    assert e.value.ctx.unstructured_path == "$['a']"
    assert e.value.data == "x"

    with pytest.raises(MissingFields) as e:
        structure(Baz, {})
    assert e.value.ctx.structured_type is Baz
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == {}
    assert sorted(e.value.missing) == ["a", "b"]

    with pytest.raises(MissingFields) as e:
        structure(Baz, {"a": 1, "c": "x"})
    assert e.value.ctx.structured_type is Baz
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == {"a": 1, "c": "x"}
    assert e.value.missing == ["b"]

    with pytest.raises(ExtraFields) as e:
        structure(Baz, {"a": 1, "b": "x", "c": 0, "d": "_"})
    assert e.value.ctx.structured_type is Baz
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == {"a": 1, "b": "x", "c": 0, "d": "_"}
    assert sorted(e.value.extra) == ["c", "d"]

    @dataclass
    class Qux:
        a: int
        b: Any
        c: float = 9.9

    assert structure(Qux, {"a": 1, "b": "xyz"}) == Qux(1, "xyz", 9.9)
    assert structure(Qux, {"a": 1, "b": 3, "c": 1.1}) == Qux(1, 3, 1.1)


def test_structure_generic_dataclass():
    T = TypeVar("T")

    @dataclass
    class Foo(Generic[T]):
        a: T
        b: str

    assert structure(Foo[int], {"a": 1, "b": "zzz"}) == Foo[int](1, "zzz")
    assert structure(Foo[str], {"a": "1", "b": "xyz"}) == Foo[str]("1", "xyz")

    with pytest.raises(NoStructureHook) as e:
        structure(Foo[int], {"a": "x"})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$.a"
    assert e.value.ctx.unstructured_path == "$['a']"
    assert e.value.data == "x"

    U = TypeVar("U")

    @dataclass
    class Bar(Generic[T, U]):
        a: T
        b: U

    assert structure(Bar[int, str], {"a": 1, "b": "zzz"}) == Bar[int, str](1, "zzz")
    assert structure(Bar[bool, float], {"a": True, "b": 1.1}) == Bar[bool, float](True, 1.1)

    with pytest.raises(NoStructureHook) as e:
        structure(Foo[int], Bar[int, str](1, "x"))
    assert e.value.ctx.structured_type == Foo[int]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == Bar[int, str](1, "x")


def test_structure_optional():
    assert structure(int | None, 1) == 1
    assert structure(None | int, 1) == 1
    assert structure(int | None, None) is None
    assert structure(None | int, None) is None
    assert structure(Optional[int], 1) == 1
    assert structure(Optional[int], None) is None
    assert structure(list[int | None], [1, None]) == [1, None]
    assert structure(list[Optional[int]], [1, None]) == [1, None]
    assert structure(Optional[list[int]], [1, 2]) == [1, 2]
    assert structure(Optional[list[int]], None) is None
    assert structure(list[int] | None, [1, 2]) == [1, 2]
    assert structure(list[int] | None, None) is None

    @dataclass
    class Foo:
        a: str | None

    assert structure(Foo, {"a": "x"}) == Foo("x")
    assert structure(Foo, {"a": None}) == Foo(None)

    with pytest.raises(NoStructureHook) as e:
        structure(int | None, "a")
    assert e.value.ctx.structured_type == int | None
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == "a"

    with pytest.raises(NoStructureHook) as e:
        structure(int, None)
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data is None

    with pytest.raises(NoStructureHook) as e:
        structure(list[int], [1, None])
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$[1]"
    assert e.value.ctx.unstructured_path == "$[1]"
    assert e.value.data is None


def test_structure_primitive_union():
    @dataclass
    class Foo:
        a: int | str

    assert structure(int | str, 1) == 1
    assert structure(int | str, "a") == "a"
    assert structure(Union[int, str], 1) == 1

    assert structure(int | bool, True) is True
    assert structure(int | bool, 1) == 1

    assert structure(int | float, 1.1) == 1.1
    assert structure(int | float, 1) == 1
    assert type(structure(int | float, 1)) is int

    assert structure(int | str | None, 1) == 1
    assert structure(int | str | None, "a") == "a"
    assert structure(int | str | None, None) is None

    assert structure(list | set, [1, 2]) == [1, 2]
    assert structure(list | set, {1, 2}) == {1, 2}
    assert structure(set | list, [1, 2]) == [1, 2]

    assert structure(tuple | list, (1, 2)) == (1, 2)
    assert structure(tuple | list, [1, 2]) == [1, 2]

    assert structure(list[int | str], [1, "a"]) == [1, "a"]
    assert structure(tuple[int | str, ...], [1, "a"]) == (1, "a")
    assert structure(tuple[int | str, float], [1, 1.1]) == (1, 1.1)
    assert structure(tuple[int | str, float], ["a", 1.1]) == ("a", 1.1)

    assert structure(Foo, {"a": 1}) == Foo(1)
    assert structure(Foo, {"a": "x"}) == Foo("x")

    assert structure(date | str, "2000-01-01") == "2000-01-01"

    with pytest.raises(AmbiguousUnion) as e:
        structure(list[int] | list[str], [1, 2])
    assert e.value.ctx.structured_type == list[int] | list[str]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == [1, 2]

    with pytest.raises(NoStructureHook) as e:
        structure(int | str, 1.1)
    assert e.value.ctx.structured_type == int | str
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 1.1

    with pytest.raises(NoStructureHook) as e:
        structure(int | str, None)
    assert e.value.ctx.structured_type == int | str
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data is None

    with pytest.raises(NoStructureHook) as e:
        structure(int | str, {"a": 1})
    assert e.value.ctx.structured_type == int | str
    assert e.value.ctx.structured_path == "$"
    assert e.value.data == {"a": 1}

    with pytest.raises(NoStructureHook) as e:
        structure(list[int | str], [1, None])
    assert e.value.ctx.structured_type == int | str
    assert e.value.ctx.structured_path == "$[1]"
    assert e.value.ctx.unstructured_path == "$[1]"
    assert e.value.data is None

    with pytest.raises(NoStructureHook) as e:
        structure(list[int | str], [1, 1.1])
    assert e.value.ctx.structured_type == int | str
    assert e.value.ctx.structured_path == "$[1]"
    assert e.value.ctx.unstructured_path == "$[1]"
    assert e.value.data == 1.1

    with pytest.raises(NoStructureHook) as e:
        structure(tuple[int | str, ...], [1, 2, 1.1])
    assert e.value.ctx.structured_type == int | str
    assert e.value.ctx.structured_path == "$[2]"
    assert e.value.ctx.unstructured_path == "$[2]"
    assert e.value.data == 1.1

    with pytest.raises(NoStructureHook) as e:
        structure(Foo, {"a": 1.1})
    assert e.value.ctx.structured_type == int | str
    assert e.value.ctx.structured_path == "$.a"
    assert e.value.ctx.unstructured_path == "$['a']"
    assert e.value.data == 1.1


def test_structure_literal_union():
    assert structure(Literal["a"] | Literal["b"], "a") == "a"
    assert structure(Literal["a"] | Literal["b"], "b") == "b"

    for _ in range(3):
        assert structure(Literal["a"] | Literal["b"], "a") == "a"
        assert structure(Literal["a"] | Literal["b"], "a") == "a"
        assert structure(Literal["a"] | Literal["b"], "b") == "b"

    assert structure(Literal[1, 2] | Literal[3, 4], 1) == 1
    assert structure(Literal[1, 2] | Literal[3, 4], 2) == 2
    assert structure(Literal[1, 2] | Literal[3, 4], 3) == 3
    assert structure(Literal[1, 2] | Literal[3, 4], 4) == 4

    assert structure(Literal["a"] | Literal[0], "a") == "a"
    assert structure(Literal["a"] | Literal[0], 0) == 0

    assert structure(Literal["a", "b"], "a") == "a"
    assert structure(Literal["a", "b"], "b") == "b"

    assert structure(Literal["a"] | int, "a") == "a"
    assert structure(Literal["a"] | int, 9) == 9

    assert structure(Literal["a"] | str, "a") == "a"
    assert structure(Literal["a"] | str, "b") == "b"

    with pytest.raises(NoStructureHook) as e:
        structure(Literal["a"] | Literal["b"], "c")
    assert e.value.ctx.structured_type == Literal["a"] | Literal["b"]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == "c"


def test_structure_union_duplicated_members():
    assert structure(int | str | int, 1) == 1
    assert structure(int | int, 1) == 1

    @dataclass
    class Foo:
        a: int

    @dataclass
    class Bar:
        b: int

    assert structure(Foo | Foo, {"a": 1}) == Foo(1)
    assert structure(Foo | Bar | Foo, {"a": 1}) == Foo(1)


IntOrStr = TypeAliasType("IntOrStr", int | str)


def test_structure_union_with_union_alias_member():
    assert structure(IntOrStr | None, 1) == 1
    assert structure(IntOrStr | None, "a") == "a"
    assert structure(IntOrStr | None, None) is None
    assert structure(IntOrStr | int, 1) == 1

    with pytest.raises(NoStructureHook):
        structure(IntOrStr | None, 1.5)


def test_structure_typeddict():
    class Foo(TypedDict):
        a: int
        b: str

    assert structure(Foo, {"a": 1, "b": "x"}) == {"a": 1, "b": "x"}

    with pytest.raises(NoStructureHook) as e:
        structure(Foo, 1)
    assert e.value.ctx.structured_type is Foo
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 1

    data = {"a": 1}
    with pytest.raises(MissingFields) as e:
        structure(Foo, data)
    assert e.value.ctx.structured_type is Foo
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.missing == ["b"]
    assert e.value.data is data

    with pytest.raises(MissingFields) as e:
        structure(Foo, {})
    assert sorted(e.value.missing) == ["a", "b"]

    with pytest.raises(NoStructureHook) as e:
        structure(Foo, {"a": "x", "b": "y"})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$.a"
    assert e.value.ctx.unstructured_path == "$['a']"
    assert e.value.data == "x"


def test_structure_typeddict_extras_dropped():
    class Foo(TypedDict):
        a: int

    assert structure(Foo, {"a": 1, "extra": 99}) == {"a": 1}
    assert structure(Foo, {"a": 1, "x": "y", "z": 0}) == {"a": 1}


def test_structure_typeddict_total_false():
    class Foo(TypedDict, total=False):
        a: int
        b: str

    assert structure(Foo, {"a": 1, "b": "x"}) == {"a": 1, "b": "x"}
    assert structure(Foo, {"a": 1}) == {"a": 1}
    assert structure(Foo, {}) == {}


def test_structure_typeddict_required_notrequired():
    class Foo(TypedDict):
        a: int
        b: NotRequired[str]

    assert structure(Foo, {"a": 1, "b": "x"}) == {"a": 1, "b": "x"}
    assert structure(Foo, {"a": 1}) == {"a": 1}

    with pytest.raises(MissingFields) as e:
        structure(Foo, {"b": "x"})
    assert e.value.missing == ["a"]

    class Bar(TypedDict, total=False):
        a: int
        b: Required[str]

    assert structure(Bar, {"a": 1, "b": "x"}) == {"a": 1, "b": "x"}
    assert structure(Bar, {"b": "x"}) == {"b": "x"}

    with pytest.raises(MissingFields) as e:
        structure(Bar, {"a": 1})
    assert e.value.missing == ["b"]


def test_structure_typeddict_optional_field_appears_later():
    class Foo(TypedDict):
        a: int
        b: NotRequired[str]

    class Bar(TypedDict, total=False):
        a: int
        b: NotRequired[int]

    # First call without optional `b`, then later call with `b` present.
    assert structure(Foo, {"a": 1}) == {"a": 1}
    assert structure(Foo, {"a": 1, "b": "x"}) == {"a": 1, "b": "x"}
    assert structure(Foo, {"a": 2, "b": "y"}) == {"a": 2, "b": "y"}
    assert structure(Foo, {"a": 3}) == {"a": 3}

    # Same pattern with all-optional TypedDict.
    assert structure(Bar, {}) == {}
    assert structure(Bar, {"a": 1}) == {"a": 1}
    assert structure(Bar, {"a": 1, "b": 2}) == {"a": 1, "b": 2}
    assert structure(Bar, {"b": 2}) == {"b": 2}


def test_structure_typeddict_inheritance():
    class Base(TypedDict):
        a: int

    class Sub(Base):
        b: str

    assert structure(Sub, {"a": 1, "b": "x"}) == {"a": 1, "b": "x"}

    with pytest.raises(MissingFields) as e:
        structure(Sub, {"a": 1})
    assert e.value.missing == ["b"]


def test_structure_typeddict_generic():
    T = TypeVar("T")

    class GenTD(TypedDict, Generic[T]):
        x: T

    assert structure(GenTD[int], {"x": 42}) == {"x": 42}
    assert structure(GenTD[str], {"x": "hello"}) == {"x": "hello"}

    with pytest.raises(NoStructureHook) as e:
        structure(GenTD[int], {"x": "not-an-int"})
    assert e.value.ctx.structured_type is int


def test_structure_typeddict_nonidentifier_names():
    Foo = TypedDict("Foo", {"foo-bar": int, "x y": str})

    assert structure(Foo, {"foo-bar": 1, "x y": "hello"}) == {"foo-bar": 1, "x y": "hello"}

    with pytest.raises(NoStructureHook) as e:
        structure(Foo, {"foo-bar": "bad", "x y": "ok"})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$.foo-bar"

    with pytest.raises(NoStructureHook) as e:
        structure(Foo, {"foo-bar": 1, "x y": 99})
    assert e.value.ctx.structured_type is str
    assert e.value.ctx.structured_path == "$.'x y'"


def test_structure_typeddict_closed():
    class Foo(ExtTypedDict, closed=True):
        a: int

    assert structure(Foo, {"a": 1}) == {"a": 1}

    data = {"a": 1, "extra": 99}
    with pytest.raises(ExtraFields) as e:
        structure(Foo, data)
    assert e.value.ctx.structured_type is Foo
    assert e.value.ctx.structured_path == "$"
    assert set(e.value.extra) == {"extra"}
    assert e.value.data is data

    with pytest.raises(ExtraFields) as e:
        structure(Foo, {"a": 1, "x": 1, "y": 2})
    assert set(e.value.extra) == {"x", "y"}

    with pytest.raises(ExtraFields) as e:
        structure(Foo, {"a": 1, 1: 2})
    assert set(e.value.extra) == {1}

    with pytest.raises(MissingFields) as e:
        structure(Foo, {"extra": 1})
    assert e.value.missing == ["a"]


def test_structure_typeddict_extra_items_typed():
    class Foo(ExtTypedDict, extra_items=int):
        a: str

    assert structure(Foo, {"a": "hi", "x": 1, "y": 2}) == {"a": "hi", "x": 1, "y": 2}
    assert structure(Foo, {"a": "hi"}) == {"a": "hi"}

    with pytest.raises(NoStructureHook) as e:
        structure(Foo, {"a": "hi", "bad": "not-an-int"})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$.bad"
    assert e.value.ctx.unstructured_path == "$['bad']"
    assert e.value.ctx.structured_key == "bad"
    assert e.value.ctx.parent is not None
    assert e.value.ctx.parent.structured_type is Foo
    assert e.value.data == "not-an-int"


def test_structure_typeddict_extra_items_readonly():
    class Foo(ExtTypedDict, extra_items=ReadOnly[int]):
        a: str

    assert structure(Foo, {"a": "hi", "extra": 1}) == {"a": "hi", "extra": 1}

    with pytest.raises(NoStructureHook) as e:
        structure(Foo, {"a": "bad", "extra": "not-an-int"})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$.extra"


def test_structure_typeddict_extra_items_readonly_type_alias():
    Int = TypeAliasType("Int", ReadOnly[int])  # type: ignore

    class Foo(ExtTypedDict, extra_items=Int):  # type: ignore
        a: str

    assert structure(Foo, {"a": "hi", "extra": 1}) == {"a": "hi", "extra": 1}

    with pytest.raises(NoStructureHook) as e:
        structure(Foo, {"a": "bad", "extra": "not-an-int"})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$.extra"


def test_structure_typeddict_extra_items_complex_type():
    class Foo(ExtTypedDict, extra_items=list[int]):
        a: int

    assert structure(Foo, {"a": 1, "xs": [1, 2, 3]}) == {"a": 1, "xs": [1, 2, 3]}


def test_structure_typeddict_legacy_default_unchanged():
    class Foo(TypedDict):
        a: int

    assert structure(Foo, {"a": 1, "extra": 99}) == {"a": 1}


def test_structure_typeddict_inheritance_closedness():
    class Base(ExtTypedDict, closed=True):
        a: int

    class Sub(Base):
        pass

    assert structure(Sub, {"a": 1}) == {"a": 1}

    with pytest.raises(ExtraFields) as e:
        structure(Sub, {"a": 1, "extra": 99})
    assert set(e.value.extra) == {"extra"}


def test_structure_typeddict_inheritance_extra_items():
    class Base(ExtTypedDict, extra_items=int):
        a: str

    class Sub(Base):
        pass

    assert structure(Sub, {"a": "hi", "x": 1, "y": 2}) == {"a": "hi", "x": 1, "y": 2}


def test_structure_typeddict_inheritance_subclass_narrows_to_closed():
    class Base(ExtTypedDict):
        a: int

    class Sub(Base, closed=True):
        pass

    assert structure(Sub, {"a": 1}) == {"a": 1}

    with pytest.raises(ExtraFields) as e:
        structure(Sub, {"a": 1, "extra": 99})
    assert set(e.value.extra) == {"extra"}


def test_structure_typeddict_generic_with_closed():
    T = TypeVar("T")

    class GenTD(ExtTypedDict, Generic[T], closed=True):
        x: T

    assert structure(GenTD[int], {"x": 42}) == {"x": 42}

    with pytest.raises(ExtraFields) as e:
        structure(GenTD[int], {"x": 42, "extra": 1})
    assert set(e.value.extra) == {"extra"}


def test_structure_typeddict_generic_with_extra_items():
    T = TypeVar("T")

    class Bag(ExtTypedDict, Generic[T], extra_items=T):
        name: str

    assert structure(Bag[int], {"name": "ok", "extra": 1}) == {"name": "ok", "extra": 1}

    with pytest.raises(NoStructureHook) as e:
        structure(Bag[int], {"name": "bad", "extra": "not-an-int"})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$.extra"


def test_structure_typeddict_generic_with_complex_extra_items():
    T = TypeVar("T")

    class Bag(ExtTypedDict, Generic[T], extra_items=list[T]):
        name: str

    assert structure(Bag[int], {"name": "ok", "extra": [1, 2]}) == {"name": "ok", "extra": [1, 2]}

    with pytest.raises(NoStructureHook) as e:
        structure(Bag[int], {"name": "bad", "extra": ["not-an-int"]})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$.extra[0]"


def test_structure_typeddict_generic_inherited_extra_items():
    T = TypeVar("T")

    class Base(ExtTypedDict, Generic[T], extra_items=T):
        name: str

    class Bag(Base[T]):
        label: NotRequired[str]

    assert structure(Bag[int], {"name": "ok", "label": "bag", "extra": 1}) == {
        "name": "ok",
        "label": "bag",
        "extra": 1,
    }

    with pytest.raises(NoStructureHook) as e:
        structure(Bag[int], {"name": "bad", "label": "bag", "extra": "not-an-int"})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$.extra"


def test_structure_typeddict_extra_items_direct_specialized_base():
    T = TypeVar("T")

    class Base(ExtTypedDict, Generic[T], extra_items=T):
        pass

    class Leaf(Base[list[int]]):  # type: ignore
        pass

    assert structure(Leaf, {"x": [1]}) == {"x": [1]}

    with pytest.raises(NoStructureHook) as e:
        structure(Leaf, {"x": ["bad"]})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$.x[0]"


def test_structure_typeddict_extra_items_inherited_specialized_base():
    T = TypeVar("T")

    class Base(ExtTypedDict, Generic[T], extra_items=T):
        pass

    class Mid(Base[list[T]], Generic[T]):  # type: ignore
        pass

    class Leaf(Mid[int]):
        pass

    assert structure(Leaf, {"x": [1]}) == {"x": [1]}

    with pytest.raises(NoStructureHook) as e:
        structure(Leaf, {"x": ["bad"]})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$.x[0]"


def test_structure_typeddict_extra_items_non_string_key():
    class Foo(ExtTypedDict, extra_items=int):
        a: int

    data = {"a": 1, 1: 2}
    with pytest.raises(ValidationError) as e:
        structure(Foo, data)
    assert "TypedDict extra key must be str, got int: 1" in str(e.value)
    assert e.value.data is data
    assert e.value.ctx.structured_type is Foo
    assert e.value.ctx.structured_path == "$"


def test_structure_dataclass_union():
    @dataclass
    class Foo:
        a: int

    @dataclass
    class Bar:
        b: str

    assert structure(Foo | Bar, {"a": 1}) == Foo(1)
    assert structure(Foo | Bar, {"b": "x"}) == Bar("x")
    assert structure(Foo | int, {"a": 1}) == Foo(1)
    assert structure(Foo | int, 1) == 1

    with pytest.raises(NoStructureHook) as e:
        structure(Foo | Bar, {"c": 1})
    assert e.value.ctx.structured_type == Foo | Bar
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == {"c": 1}

    with pytest.raises(NoStructureHook) as e:
        structure(Foo | Bar, {"a": 1, "b": "x"})
    assert e.value.ctx.structured_type == Foo | Bar
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == {"a": 1, "b": "x"}

    with pytest.raises(NoStructureHook) as e:
        structure(Foo | str, 1)
    assert e.value.ctx.structured_type == Foo | str
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 1

    with pytest.raises(ExtraFields) as e:
        structure(Foo | Bar, {"a": 1, "c": 1})
    assert e.value.ctx.structured_type == Foo
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == {"a": 1, "c": 1}


def test_structure_dataclass_union_uses_init_fields_for_discrimination():
    @dataclass
    class ByInitVar:
        kind: InitVar[Literal["init"]]
        value: int
        seen_kind: str = field(init=False)

        def __post_init__(self, kind: str) -> None:
            self.seen_kind = kind

    @dataclass
    class Plain:
        value: int
        other: str
        computed: str = field(init=False)

        def __post_init__(self) -> None:
            self.computed = self.other.upper()

    assert structure(ByInitVar | Plain, {"kind": "init", "value": 1}) == ByInitVar("init", 1)
    assert structure(ByInitVar | Plain, {"value": 1, "other": "x"}) == Plain(1, "x")

    with pytest.raises(NoStructureHook) as e:
        structure(ByInitVar | Plain, {"value": 1, "computed": "X"})
    assert e.value.ctx.structured_type == ByInitVar | Plain
    assert e.value.data == {"value": 1, "computed": "X"}


def test_structure_dataclass_union_ignores_classvar_for_discrimination():
    @dataclass
    class WithClassVar:
        name: str
        kind: ClassVar[Literal["item"]] = "item"

    @dataclass
    class Tagged:
        kind: Literal["tagged"]
        value: int

    assert structure(WithClassVar | Tagged, {"name": "book"}) == WithClassVar("book")
    assert structure(WithClassVar | Tagged, {"kind": "tagged", "value": 1}) == Tagged("tagged", 1)

    with pytest.raises(NoStructureHook) as e:
        structure(WithClassVar | Tagged, {"name": "book", "kind": "item"})
    assert e.value.ctx.structured_type == WithClassVar | Tagged
    assert e.value.data == {"name": "book", "kind": "item"}


def test_structure_generic_dataclass_union():
    T = TypeVar("T")

    @dataclass
    class Foo(Generic[T]):
        a: T

    @dataclass
    class Bar(Generic[T]):
        b: T

    assert structure(Foo[int] | Bar[int], {"a": 1}) == Foo(1)
    assert structure(Foo[str] | Bar[str], {"b": "x"}) == Bar("x")
    assert structure(Foo[int] | int, {"a": 1}) == Foo(1)
    assert structure(Foo[int] | int, 1) == 1

    assert structure(Foo | Bar, {"a": 1}) == Foo(1)
    assert structure(Foo[Any] | Bar[Any], {"a": 1}) == Foo(1)

    assert structure(Foo[Bar] | Bar[str], {"a": {"b": "x"}}) == Foo(Bar("x"))

    with pytest.raises(NoStructureHook) as e:
        structure(Foo[int] | Bar[int], {"c": 1})
    assert e.value.ctx.structured_type == Foo[int] | Bar[int]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == {"c": 1}

    with pytest.raises(AmbiguousUnion) as e:
        structure(Foo[int] | Foo[str], {"a": 1})
    assert e.value.ctx.structured_type == Foo[int] | Foo[str]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == {"a": 1}

    with pytest.raises(NoStructureHook) as e:
        structure(Foo[int] | Bar[str], {"a": 1, "b": "x"})
    assert e.value.ctx.structured_type == Foo[int] | Bar[str]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == {"a": 1, "b": "x"}

    with pytest.raises(NoStructureHook) as e:
        structure(Foo[str] | Bar[int], {"a": 1, "b": "x"})
    assert e.value.ctx.structured_type == Foo[str] | Bar[int]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == {"a": 1, "b": "x"}

    with pytest.raises(NoStructureHook) as e:
        structure(Foo[int] | str, 1)
    assert e.value.ctx.structured_type == Foo[int] | str
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 1

    with pytest.raises(ExtraFields) as e:
        structure(Foo[int] | Bar[int], {"a": 1, "c": 1})
    assert e.value.ctx.structured_type == Foo[int]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == {"a": 1, "c": 1}

    with pytest.raises(NoStructureHook) as e:
        structure(Foo[str] | Bar[int], {"a": 1, "c": 1})
    assert e.value.ctx.structured_type is str
    assert e.value.ctx.structured_path == "$.a"
    assert e.value.ctx.unstructured_path == "$['a']"
    assert e.value.data == 1


def test_structure_dataclass_union_members_in_hierarchy():
    @dataclass
    class Base:
        x: int
        y: int

    @dataclass
    class Extended(Base):
        z: int

    assert structure(Base | Extended, {"x": 1, "y": 2}) == Base(1, 2)
    assert structure(Base | Extended, {"x": 1, "y": 2, "z": 3}) == Extended(1, 2, 3)


def test_structure_dataclass_tagged_union():
    @dataclass
    class Foo:
        a: int
        b: Literal["F"]

    @dataclass
    class Bar:
        a: str
        b: Literal["B"]

    assert structure(Foo | Bar, {"a": 1, "b": "F"}) == Foo(1, "F")
    assert structure(Foo | Bar, {"a": "x", "b": "B"}) == Bar("x", "B")
    assert structure(Foo | int, {"a": 1, "b": "F"}) == Foo(1, "F")
    assert structure(Foo | int, 1) == 1

    with pytest.raises(NoStructureHook) as e:
        structure(Foo | Bar, {"c": 1})
    assert e.value.ctx.structured_type == Foo | Bar
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == {"c": 1}

    with pytest.raises(NoStructureHook) as e:
        structure(Foo | Bar, {"a": 1, "b": "x"})
    assert e.value.ctx.structured_type == Foo | Bar
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == {"a": 1, "b": "x"}

    with pytest.raises(NoStructureHook) as e:
        structure(Foo | str, 1)
    assert e.value.ctx.structured_type == Foo | str
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 1

    with pytest.raises(ExtraFields) as e:
        structure(Foo | Bar, {"a": 1, "b": "F", "c": 1})
    assert e.value.ctx.structured_type == Foo
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == {"a": 1, "b": "F", "c": 1}


def test_structure_typeddict_union():
    class Foo(TypedDict):
        a: int

    class Bar(TypedDict):
        b: str

    assert structure(Foo | Bar, {"a": 1}) == {"a": 1}
    assert structure(Foo | Bar, {"a": 1, "c": "z"}) == {"a": 1}
    assert structure(Foo | Bar, {"b": "x"}) == {"b": "x"}
    assert structure(Foo | Bar, {"b": "x", "c": "z"}) == {"b": "x"}
    assert structure(Foo | str, {"a": 1}) == {"a": 1}
    assert structure(Foo | str, "z") == "z"

    with pytest.raises(NoStructureHook) as e:
        structure(Foo | Bar, {"c": 1})
    assert e.value.ctx.structured_type == Foo | Bar
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == {"c": 1}

    with pytest.raises(NoStructureHook) as e:
        structure(Foo | Bar, {"a": 1, "b": "x"})
    assert e.value.ctx.structured_type == Foo | Bar
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == {"a": 1, "b": "x"}

    with pytest.raises(NoStructureHook) as e:
        structure(Foo | str, 1)
    assert e.value.ctx.structured_type == Foo | str
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 1


def test_structure_generic_typeddict_union():
    T = TypeVar("T")

    class Foo(TypedDict, Generic[T]):
        a: T

    class Bar(TypedDict, Generic[T]):
        b: T

    assert structure(Foo[int] | Bar[str], {"a": 1}) == {"a": 1}
    assert structure(Foo[int] | Bar[str], {"a": 1, "c": "z"}) == {"a": 1}
    assert structure(Foo[int] | Bar[str], {"b": "x"}) == {"b": "x"}
    assert structure(Foo[int] | Bar[str], {"b": "x", "c": "z"}) == {"b": "x"}
    assert structure(Foo[int] | str, {"a": 1}) == {"a": 1}
    assert structure(Foo[int] | str, "z") == "z"

    assert structure(Foo | Bar, {"a": 1}) == {"a": 1}
    assert structure(Foo[Any] | Bar[Any], {"a": 1}) == {"a": 1}

    assert structure(Foo[Bar] | Bar, {"a": {"b": "x"}}) == {"a": {"b": "x"}}

    with pytest.raises(NoStructureHook) as e:
        structure(Foo[int] | Bar[str], {"c": 1})
    assert e.value.ctx.structured_type == Foo[int] | Bar[str]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == {"c": 1}

    with pytest.raises(AmbiguousUnion) as e:
        structure(Foo[int] | Foo[str], {"a": 1})
    assert e.value.ctx.structured_type == Foo[int] | Foo[str]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == {"a": 1}

    with pytest.raises(NoStructureHook) as e:
        structure(Foo[int] | Bar[str], {"a": 1, "b": "x"})
    assert e.value.ctx.structured_type == Foo[int] | Bar[str]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == {"a": 1, "b": "x"}

    with pytest.raises(NoStructureHook) as e:
        structure(Foo[int] | str, 1)
    assert e.value.ctx.structured_type == Foo[int] | str
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 1

    with pytest.raises(NoStructureHook) as e:
        structure(Foo[int] | str, {"a": "x"})
    assert e.value.ctx.structured_type is int
    assert e.value.ctx.structured_path == "$.a"
    assert e.value.ctx.unstructured_path == "$['a']"
    assert e.value.data == "x"


def test_structure_typeddict_tagged_union():
    class Foo(TypedDict):
        a: int
        b: Literal["foo"]

    class Bar(TypedDict):
        a: str
        b: Literal["bar"]

    assert structure(Foo | Bar, {"a": 1, "b": "foo"}) == {"a": 1, "b": "foo"}
    assert structure(Foo | Bar, {"a": 1, "b": "foo", "c": "z"}) == {"a": 1, "b": "foo"}
    assert structure(Foo | Bar, {"a": "x", "b": "bar"}) == {"a": "x", "b": "bar"}
    assert structure(Foo | Bar, {"a": "x", "b": "bar", "c": "z"}) == {"a": "x", "b": "bar"}
    assert structure(Foo | str, {"a": 1, "b": "foo"}) == {"a": 1, "b": "foo"}
    assert structure(Foo | str, "z") == "z"

    with pytest.raises(NoStructureHook) as e:
        structure(Foo | Bar, {"c": 1})
    assert e.value.ctx.structured_type == Foo | Bar
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == {"c": 1}

    with pytest.raises(NoStructureHook) as e:
        structure(Foo | Bar, {"a": 1, "b": "x"})
    assert e.value.ctx.structured_type == Foo | Bar
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == {"a": 1, "b": "x"}

    with pytest.raises(NoStructureHook) as e:
        structure(Foo | str, 1)
    assert e.value.ctx.structured_type == Foo | str
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 1


def test_structure_dataclass_typeddict_union():
    @dataclass
    class Foo:
        a: int

    class Bar(TypedDict):
        b: str

    assert structure(Foo | Bar, {"a": 1}) == Foo(1)
    assert structure(Foo | Bar, {"b": "x"}) == {"b": "x"}
    assert structure(Foo | Bar, {"b": "x", "c": "z"}) == {"b": "x"}
    assert structure(Foo | Bar | str | int, {"a": 5}) == Foo(5)
    assert structure(Foo | Bar | str | int, {"b": "x"}) == {"b": "x"}
    assert structure(Foo | Bar | str | int, "z") == "z"
    assert structure(Foo | Bar | str | int, 9) == 9

    with pytest.raises(NoStructureHook) as e:
        structure(Foo | Bar, {"c": 1})
    assert e.value.ctx.structured_type == Foo | Bar
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == {"c": 1}

    with pytest.raises(NoStructureHook) as e:
        structure(Foo | Bar, {"a": 1, "b": "x"})
    assert e.value.ctx.structured_type == Foo | Bar
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == {"a": 1, "b": "x"}

    with pytest.raises(NoStructureHook) as e:
        structure(Foo | str, 1)
    assert e.value.ctx.structured_type == Foo | str
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 1

    with pytest.raises(ExtraFields) as e:
        structure(Foo | Bar, {"a": 1, "c": 1})
    assert e.value.ctx.structured_type == Foo
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == {"a": 1, "c": 1}


def test_structure_literal():
    assert structure(Literal[1, "a"], 1) == 1
    assert structure(Literal[1, "a"], "a") == "a"

    with pytest.raises(ValidationError) as e:
        structure(Literal[1, "a"], 2)
    assert e.value.ctx.structured_type == Literal[1, "a"]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 2

    with pytest.raises(ValidationError) as e:
        structure(Literal[1, "a"], None)
    assert e.value.ctx.structured_type == Literal[1, "a"]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data is None


def test_structure_newtype():
    Int = NewType("Int", int)

    assert structure(Int, 1) == 1

    with pytest.raises(NoStructureHook) as e:
        structure(Int, "1")
    assert e.value.ctx.structured_type is Int
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == "1"

    @dataclass
    class Foo:
        a: int

    Bar = NewType("Bar", Foo)

    assert structure(Bar, {"a": 0}) == Foo(0)

    with pytest.raises(NoStructureHook) as e:
        structure(Bar, 8)
    assert e.value.ctx.structured_type is Bar
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 8

    with pytest.raises(MissingFields) as e:
        structure(Bar, {"b": 1})
    assert e.value.ctx.structured_type is Bar
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.missing == ["a"]
    assert e.value.data == {"b": 1}


def test_structure_newtype_union():
    Int = NewType("Int", int)
    Str = NewType("Str", str)

    assert structure(Int | Str, 1) == 1
    assert structure(Int | Str, "x") == "x"

    with pytest.raises(NoStructureHook) as e:
        structure(Int | Str, 1.1)
    assert e.value.ctx.structured_type == Int | Str
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 1.1

    with pytest.raises(NoStructureHook) as e:
        structure(Int | Str, None)
    assert e.value.ctx.structured_type == Int | Str
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data is None


def test_structure_dataclass_literal_union():
    @dataclass
    class Foo:
        type: Literal["foo"]
        value: int

    assert structure(Foo | Literal["a"], {"type": "foo", "value": 42}) == Foo("foo", 42)


def test_structure_enum_literal():
    class Foo(Enum):
        A = 1
        B = 2

    assert structure(Literal[Foo.A], Foo.A) == Foo.A
    assert structure(Literal[Foo.B], Foo.B) == Foo.B
    assert structure(Literal[Foo.A, Foo.B], Foo.B) == Foo.B
    assert structure(Literal[Foo.A, 1], Foo.A) == Foo.A
    assert structure(Literal[Foo.A, 1], 1) == 1

    with pytest.raises(ValidationError) as e:
        structure(Literal[Foo.A], 1)
    assert e.value.ctx.structured_type == Literal[Foo.A]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == 1

    with pytest.raises(ValidationError) as e:
        structure(Literal[Foo.A], Foo.B)
    assert e.value.ctx.structured_type == Literal[Foo.A]
    assert e.value.ctx.structured_path == "$"
    assert e.value.ctx.unstructured_path == "$"
    assert e.value.data == Foo.B


def test_structure_unsupported_conversion():
    class Foo:
        pass

    with pytest.raises(NoStructureHook):
        structure(Foo, Foo)


@dataclass
class FooDC:
    a: "FooDC | None"


def test_structure_dataclass_optional_recursive():
    assert structure(FooDC, {"a": {"a": {"a": None}}}) == FooDC(FooDC(FooDC(None)))


class FooTD(TypedDict):
    a: "FooTD | None"


def test_structure_typeddict_optional_recursive():
    assert structure(FooTD, {"a": {"a": {"a": None}}}) == {"a": {"a": {"a": None}}}


AliasInt = TypeAliasType("AliasInt", int)


def test_structure_type_alias():
    assert structure(AliasInt, 1) == 1


def test_structure_dataclass_with_aliased_field():
    @dataclass
    class _FooWithAliasedField:
        x: AliasInt

    assert structure(_FooWithAliasedField, {"x": 1}) == _FooWithAliasedField(x=1)


K = TypeVar("K")
V = TypeVar("V")
SwapDict = TypeAliasType("SwapDict", dict[V, K], type_params=(K, V))


def test_structure_parameterized_alias_with_reordering():
    result = structure(SwapDict[str, int], {1: "a", 2: "b"})
    assert result == {1: "a", 2: "b"}


AliasA = TypeAliasType("AliasA", int)
AliasB = TypeAliasType("AliasB", AliasA)


def test_structure_transitive_alias_chain():
    assert structure(AliasB, 1) == 1
