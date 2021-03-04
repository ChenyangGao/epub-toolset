from itertools import product
from random import shuffle
from types import MappingProxyType
from typing import Callable, Iterable, NoReturn, Tuple, Type
from uuid import uuid4, UUID

random_bytes: Callable[[int], bytes]
try:
    from secrets import token_bytes as random_bytes
except ImportError:
    from os import urandom as random_bytes


__all__ = ['BaseCharsEncodeError', 'BaseCharsDecodeError', 'BaseCharsProduct']


class BaseCharsEncodeError(ValueError):
    pass


class BaseCharsDecodeError(ValueError):
    pass


class BaseCharsProduct:

    __slots__: Tuple[str, ...] = ('chars', 'repeat', 'ivmap', 'vimap')

    _expected_chars_count: Tuple[int, ...] = (1 << 1, 1 << 2, 1 << 4, 1 << 8)
    _expected_chars_repeat: Tuple[int, ...] = (8, 4, 2, 1)

    def __init__(self, chars: str, do_shuffle: bool = False):
        cls: Type[BaseCharsProduct] = type(self)
        chars_count: int = len(chars)
        if not chars_count == len(set(chars)):
            raise ValueError(
                'Expected a string with different characters')
        repeat: int
        try:
            repeat = self._expected_chars_repeat[
                cls._expected_chars_count.index(chars_count)]
        except ValueError as e:
            raise ValueError(
                'Expected a string within %r different characters, get %d' 
                % (cls._expected_chars_count, chars_count)) from e
        self.chars: str
        super().__setattr__('chars', chars)
        self.repeat: int
        super().__setattr__('repeat', repeat)
        prod: Iterable = product(chars, repeat=repeat)
        if do_shuffle:
            prod = list(prod)
            shuffle(prod)
        self.ivmap: MappingProxyType
        super().__setattr__('ivmap', MappingProxyType(
            {i: ''.join(l) for i, l in enumerate(prod)}))
        self.vimap: MappingProxyType
        super().__setattr__('vimap', MappingProxyType(
            {v: k for k, v in self.ivmap.items()}))

    def __setattr__(self, attr, val) -> NoReturn:
        raise TypeError('setting properties is not allowed')

    def encode(self, b: bytes) -> str:
        try:
            return ''.join(self.ivmap[i] for i in b)
        except Exception as e:
            raise BaseCharsEncodeError from e

    def decode(self, s: str) -> bytes:
        repeat: int = self.repeat
        try:
            return bytes(self.vimap[s[i:i+repeat]] 
                         for i in range(0, len(s), repeat))
        except Exception as e:
            raise BaseCharsDecodeError from e

    def random(self, bytes_len: int = 1) -> Tuple[bytes, str]:
        rb: bytes = random_bytes(bytes_len)
        return rb, self.encode(rb)

    def random_uuid(self) -> Tuple[UUID, str]:
        uuid: UUID = uuid4()
        return uuid, self.encode(uuid.bytes)

