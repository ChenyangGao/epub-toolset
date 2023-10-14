#!/usr/bin/env python3
# coding: utf-8

__author__  = "ChenyangGao <https://chenyanggao.github.io/>"
__version__ = (0, 0, 1)
__all__ = ["bind_function_registry", "FunctionRegistry"]

from functools import partial
from operator import attrgetter
from typing import Callable, MutableMapping, Optional, TypeVar


K = TypeVar("K")


def bind_function_registry(
    maps: MutableMapping[K, Callable], 
    /, 
    key_func: Callable[[Callable], K] = attrgetter("__name__"), 
) -> tuple[Callable, Callable]:
    """
    """
    def register(
        func_or_key: K | Callable, 
        /, 
        key: Optional[K] = None, 
    ):
        if not callable(func_or_key):
            return partial(register, key=func_or_key)
        if key is None:
            key = key_func(func_or_key)
        maps[key] = func_or_key
        return func_or_key

    def unregister(
        func_or_key: K | Callable, 
        /, 
        key: Optional[K] = None, 
    ):
        if key is None:
            key = key_func(func_or_key) if callable(func_or_key) else func_or_key
        del maps[key]

    return register, unregister


class FunctionRegistry(dict[K, Callable]):
    """
    """
    def __init__(
        self, 
        /, 
        key_func: Callable[[Callable], K] = attrgetter("__name__"), 
    ):
        self.key_func = key_func

    def register(
        self, 
        func_or_key: K | Callable, 
        /, 
        key: Optional[K] = None, 
    ):
        if not callable(func_or_key):
            return partial(self.register, key=func_or_key)
        if key is None:
            key = self.key_func(func_or_key)
        self[key] = func_or_key
        return func_or_key

    __call__ = register

    def unregister(
        self, 
        func_or_key: K | Callable, 
        /, 
        key: Optional[K] = None, 
    ):
        if key is None:
            key = self.key_func(func_or_key) if callable(func_or_key) else func_or_key
        del self[key]

    def call(self, key, /, *args, **kwds):
        return self[key](*args, **kwds)

