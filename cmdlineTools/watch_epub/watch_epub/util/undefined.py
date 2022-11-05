#!/usr/bin/env python3
# coding: utf-8

__author__  = "ChenyangGao <https://chenyanggao.github.io/>"
__version__ = (0, 0, 1)
__all__ = ["UndefinedType", "undefined"]


class UndefinedType:
    """A new singleton constant to Python that is passed in 
    when a parameter is not mapped to an argument."""
    __slots__ = ()
    __bool__ = staticmethod(lambda: False)
    __eq__ = lambda self, other: self is other
    __hash__ = staticmethod(lambda: 0)
    __repr__ = staticmethod(lambda: "undefined")

    def __new__(cls):
        try:
            return cls.__instance__
        except AttributeError:
            inst = cls.__instance__ = super().__new__(cls)
            return inst

    def __init_subclass__(cls, /, **kwargs):
        if __class__ in cls.__bases__:
            raise TypeError("Subclassing is not allowed!")
        return super().__init_subclass__(**kwargs)

undefined = UndefinedType()

