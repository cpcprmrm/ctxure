# type: ignore

from collections import Counter, defaultdict, deque
from collections.abc import (
    Collection,
    Container,
    Iterable,
    Iterator,
    Mapping,
    MutableMapping,
    MutableSequence,
    MutableSet,
    Reversible,
    Sequence,
)
from collections.abc import (
    Set as ABCSet,
)
from typing import ChainMap, NamedTuple, TypeVar

from typing_extensions import OrderedDict


class TypeInfo(NamedTuple):
    mro: tuple
    orig_bases: tuple
    parameters: tuple


_T = TypeVar("_T")

_K = TypeVar("_K")

_V = TypeVar("_V")


_type_info: dict[type, TypeInfo] = {
    Iterable: TypeInfo(Iterable.__mro__, (), (_T,)),
    Container: TypeInfo(Container.__mro__, (), (_T,)),
    Iterator: TypeInfo(Iterator.__mro__, (Iterable[_T],), (_T,)),
    Reversible: TypeInfo(Reversible.__mro__, (Iterable[_T],), (_T,)),
    Collection: TypeInfo(Collection.__mro__, (Iterable[_T], Container[_T]), (_T,)),
    Sequence: TypeInfo(Sequence.__mro__, (Reversible[_T], Collection[_T]), (_T,)),
    MutableSequence: TypeInfo(MutableSequence.__mro__, (Sequence[_T],), (_T,)),
    ABCSet: TypeInfo(ABCSet.__mro__, (Collection[_T],), (_T,)),
    MutableSet: TypeInfo(MutableSet.__mro__, (ABCSet[_T],), (_T,)),
    Mapping: TypeInfo(Mapping.__mro__, (Collection[_K],), (_K, _V)),
    MutableMapping: TypeInfo(MutableMapping.__mro__, (Mapping[_K, _V],), (_K, _V)),
    list: TypeInfo((list, *MutableSequence.__mro__), (MutableSequence[_T],), (_T,)),
    dict: TypeInfo((dict, *MutableMapping.__mro__), (MutableMapping[_K, _V],), (_K, _V)),
    set: TypeInfo((set, *MutableSet.__mro__), (MutableSet[_T],), (_T,)),
    frozenset: TypeInfo((frozenset, *ABCSet.__mro__), (ABCSet[_T],), (_T,)),
    tuple: TypeInfo((tuple, *Sequence.__mro__), (), ()),
    type: TypeInfo(type.__mro__, (), (_T,)),
    deque: TypeInfo((deque, *MutableSequence.__mro__), (MutableSequence[_T],), (_T,)),
    defaultdict: TypeInfo((defaultdict, dict, *MutableMapping.__mro__), (dict[_K, _V],), (_K, _V)),
    OrderedDict: TypeInfo((OrderedDict, dict, *MutableMapping.__mro__), (dict[_K, _V],), (_K, _V)),
    Counter: TypeInfo((Counter, dict, *MutableMapping.__mro__), (dict[_T, int],), (_T,)),
    ChainMap: TypeInfo((ChainMap, *MutableMapping.__mro__), (MutableMapping[_K, _V],), (_K, _V)),
}
