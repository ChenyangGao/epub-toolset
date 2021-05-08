from itertools import product
from types import MappingProxyType
from typing import Dict, Tuple


__all__ = ['BaseCharsEncodeError', 'BaseCharsDecodeError', 'BaseChars', 'BaseCharsProduct']


class BaseCharsEncodeError(ValueError):
    pass


class BaseCharsDecodeError(ValueError):
    pass


class BaseChars:

    __slots__: Tuple[str, ...] = ('_chars', '_charmap', '_bits', '_sup')

    def __init__(self, chars: str) -> None:
        l: int = len(chars)
        if l < 2:
            raise ValueError('length of `chars` at least 2')
        elif l & (l-1):
            raise ValueError('length of `chars` must be a positive integer power of 2')
        self._charmap: Dict[str, int] = dict(zip(chars, range(l)))
        if len(self._charmap) != l:
            raise ValueError('`chars` must consist of different characters')
        self._chars: str = chars
        self._bits: int = l.bit_length() - 1
        self._sup: int = (1 << self._bits) - 1

    def encode(self, n: int) -> str:
        chars: str = self._chars
        sup: int = self._sup
        try:
            return ''.join(
                chars[(n >> i) & sup]
                for i in range(0, n.bit_length(), self._bits)
            )[::-1]
        except Exception as exc:
            raise BaseCharsEncodeError from exc

    def decode(self, s: str) -> int:
        bits: int = self._bits
        charmap: Dict[str, int] = self._charmap
        n: int = 0
        try:
            for ch in s:
                n = (n << bits) | charmap[ch]
            return n
        except Exception as exc:
            raise BaseCharsDecodeError from exc

    def encode_bytes(self, b: bytes) -> str:
        return self.encode(int.from_bytes(b, 'big'))

    def decode_bytes(self, s: str) -> bytes:
        n: int = self.decode(s)
        return int.to_bytes(n, (n.bit_length() + 7) // 8, 'big')


class BaseCharsProduct:

    __slots__: Tuple[str, ...] = ('_chars', '_repeat', '_ivmap', '_vimap')

    _expected_chars_count: Tuple[int, ...] = (1 << 1, 1 << 2, 1 << 4, 1 << 8)
    _expected_chars_repeat: Tuple[int, ...] = (8, 4, 2, 1)

    def __init__(self, chars: str):
        chars_count: int = len(chars)
        if chars_count != len(set(chars)):
            raise ValueError('`chars` must consist of different characters')
        repeat: int
        try:
            repeat = self._expected_chars_repeat[
                self._expected_chars_count.index(chars_count)]
        except ValueError as exc:
            raise ValueError(
                'Expected a string within %r different characters, get %d' 
                % (self._expected_chars_count, chars_count)) from exc
        self._chars: str = chars
        self._repeat: int = repeat
        self._ivmap: MappingProxyType = MappingProxyType(
            {i: ''.join(l) for i, l in enumerate(product(chars, repeat=repeat))}
        )
        self._vimap: MappingProxyType = MappingProxyType(
            {v: k for k, v in self._ivmap.items()}
        )

    def encode(self, b: bytes) -> str:
        ivmap = self._ivmap
        try:
            return ''.join(ivmap[i] for i in b)
        except Exception as exc:
            raise BaseCharsEncodeError from exc

    def decode(self, s: str) -> bytes:
        repeat: int = self._repeat
        try:
            return bytes(self._vimap[s[i:i+repeat]] 
                         for i in range(0, len(s), repeat))
        except Exception as exc:
            raise BaseCharsDecodeError from exc

