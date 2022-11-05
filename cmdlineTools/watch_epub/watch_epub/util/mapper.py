#!/usr/bin/env python3
# coding: utf-8

__author__  = "ChenyangGao <https://chenyanggao.github.io/>"
__version__ = (0, 1)
__all__ = ["Mapper", "DictMapper"]

from typing import MutableMapping

from util.undefined import undefined


@MutableMapping.register
class Mapper:

    def __init__(self, *args, **kwds):
        self.__dict__.update(*args, **kwds)

    def __contains__(self, key):
        return key in self.__dict__

    def __iter__(self):
        return iter(self.__dict__)

    def __len__(self):
        return len(self.__dict__)

    def __getitem__(self, key):
        return self.__dict__[key]

    def __setitem__(self, key, val):
        self.__dict__[key] = val

    def __delitem__(self, key):
        del self.__dict__[key] 

    def __call__(self, key, val=undefined):
        if val is undefined:
            return self.__dict__[key]
        self.__dict__[key] = val
        return val

    def __repr__(self):
        return f"{type(self).__qualname__}({self.__dict__!r})"


class DictMapper(dict):

    def __getattr__(self, key):
        return self[key]

    def __setattr__(self, key, val):
        self[key] = val

    def __delattr__(self, key):
        del self[key] 

    def __call__(self, key, val=undefined):
        if val is undefined:
            return self.__dict__[key]
        self[key] = val
        return val

