from inspect import getfullargspec
from typing import Callable, Optional


__all__ = ['argcount', 'int_to_bytes', 'id_to_bytes']


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
    byteorder: str = 'little', 
    signed: Optional[bool] = None,
) -> bytes:
    if signed is None:
        signed = i < 0
    return i.to_bytes(i.bit_length() // 8 + 1, byteorder, signed=signed)


def id_to_bytes(obj, fillup: bool = True) -> bytes:
    if fillup:
        return id(obj).to_bytes(POINTER_LENGTH, 'little')
    return int_to_bytes(id(obj), signed=False)

