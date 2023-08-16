#! /usr/bin/env python3
# coding: utf-8

__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 2)
__all__ = ['ppartial', 'argcount', 'int_to_bytes', 'id_to_bytes', 
           'get_sys_byteorder', 'astype_bytes', 'astype_str', 'as_closure']


import sys
import struct

from functools import partial
from inspect import getfullargspec
from typing import Any, ByteString, Callable, Optional

from .undefined import undefined


# C pointer bytes length
POINTER_LENGTH: int = __import__('struct').calcsize('P')


class ppartial(partial):

    def __call__(self, *args, **kwargs):
        a, k = self.args, self.keywords
        k.update(kwargs)
        if undefined in a:
            a1, a2 = iter(a), iter(args)
            a = (*(next(a2, v) if v is undefined else v for v in a1), 
                 *a1, *a2)
        else:
            a += args
        if undefined in a or undefined in k.values():
            return type(self)(self.func, *a, **k)
        return self.func(*a, **k)


def argcount(func: Callable) -> int:
    if hasattr(func, '__code__'):
        return func.__code__.co_argcount
    try:
        return len(getfullargspec(func).args)
    except:
        return 0


def int_to_bytes(
    i: int, 
    byteorder: str = sys.byteorder, 
    signed: Optional[bool] = None,
) -> bytes:
    if signed is None:
        signed = i < 0
    return i.to_bytes(
        (i.bit_length() + 7) // 8, 
        byteorder, 
        signed=signed
    )


def id_to_bytes(
    obj, 
    fillup: bool = True,
    byteorder: str = sys.byteorder,
) -> bytes:
    if fillup:
        return id(obj).to_bytes(POINTER_LENGTH, byteorder)
    return int_to_bytes(id(obj), byteorder=byteorder, signed=False)


def get_sys_byteorder():
    # OR return ('big', 'little')[struct.pack('i', 1)[0]]
    if struct.pack('<L', 0x12345678)[0] == 0x78:
        return 'little'
    else:
        return 'big'


def astype_bytes(o: Any) -> bytes:
    if isinstance(o, int):
        return int_to_bytes(o)
    if not isinstance(o, str):
        try:
            return bytes(o)
        except TypeError:
            o = str(o)
    try:
        return o.encode()
    except:
        return o.encode('latin-1')


def astype_str(o: Any) -> str:
    if isinstance(o, str):
        return o
    elif isinstance(o, ByteString):
        o = bytes(o)
        try:
            return str(o, encoding='utf-8')
        except:
            return str(o, encoding='latin-1')
    else:
        return str(o)


def as_closure(
    fn: Optional[Callable[..., Callable]] = None, 
    /, 
    *args, 
    **kwargs, 
) -> Callable:
    if fn is None:
        return ppartial(as_closure, undefined, *args, **kwargs)
    f = fn(*args, **kwargs)
    try:
        f.__name__ = fn.__name__
    except AttributeError:
        pass
    try:
        f.__qualname__ = fn.__qualname__
    except AttributeError:
        pass
    return f

