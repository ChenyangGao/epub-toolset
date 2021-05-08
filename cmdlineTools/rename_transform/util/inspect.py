import sys
import struct

from inspect import getfullargspec
from typing import Callable, Optional


__all__ = ['argcount', 'int_to_bytes', 'id_to_bytes', 'get_sys_byteorder']


# C pointer bytes length
POINTER_LENGTH: int = __import__('struct').calcsize('P')


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
    # return ('big', 'little')[struct.pack('i', 1)[0]]
    if struct.pack('<L', 0x12345678)[0] == 0x78:
        return 'little'
    else:
        return 'big'

