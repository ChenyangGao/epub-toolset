#!/usr/bin/env python3
# coding: utf-8

__author__  = "ChenyangGao <https://chenyanggao.github.io/>"
__version__ = (0, 1, 1)
__all__ = ["Mapper", "DictMapper"]

from typing import cast, Generic, Iterator, Mapping, MutableMapping, TypeVar

from util.undefined import undefined, UndefinedType


K = TypeVar("K")
V = TypeVar("V")


@MutableMapping.register
class Mapper(Generic[K, V]):

    def __init__(self, *args, **kwds):
        self.__dict__: dict[K, V]
        self.__dict__.update(*args, **kwds)

    def __contains__(self, key: K) -> bool:
        return key in self.__dict__

    def __iter__(self) -> Iterator[K]:
        return iter(self.__dict__)

    def __len__(self) -> int:
        return len(self.__dict__)

    def __getitem__(self, key: K) -> V:
        return self.__dict__[key]

    def __setitem__(self, key: K, val: V):
        self.__dict__[key] = val

    def __delitem__(self, key: K):
        del self.__dict__[key] 

    def __call__(self, key: K, val: UndefinedType | V = undefined) -> V:
        if val is undefined:
            return self.__dict__[key]
        val = cast(V, val)
        self.__dict__[key] = val
        return val

    def __repr__(self) -> str:
        return f"{type(self).__qualname__}({self.__dict__!r})"


class DictMapper(dict[K, V]):

    def __getattr__(self, key) -> V:
        try:
            return self[key]
        except KeyError as exc:
            raise AttributeError(key) from exc

    def __setattr__(self, key, val: V):
        self[key] = val

    def __delattr__(self, key):
        try:
            del self[key] 
        except KeyError as exc:
            raise AttributeError(key) from exc

    def __call__(self, key: K, val: UndefinedType | V = undefined) -> V:
        if val is undefined:
            return self[key]
        val = cast(V, val)
        self[key] = val
        return val

