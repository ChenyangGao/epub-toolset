#!/usr/bin/env python3
# coding: utf-8

__author__ = "ChenyangGao <https://chenyanggao.github.io/>"
__version__ = (0, 0, 1)
__all__ = ["lazyproperty"]


class lazyproperty:

    def __init__(self, propfn, /):
        self.__func__ = propfn
        self.__name__ = propfn.__name__

    def __get__(self, instance, cls, /):
        if instance is None:
            return self
        value = self.__func__(instance)
        setattr(instance, self.__name__, value)
        return value

