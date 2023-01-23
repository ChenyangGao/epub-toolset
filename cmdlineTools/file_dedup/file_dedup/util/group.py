#!/usr/bin/env python3
# coding: utf-8

__author__ = "ChenyangGao <https://chenyanggao.github.io/>"
__version__ = (0, 0, 1)
__all__ = ["groupdict"]

from typing import Callable, Iterable, TypeVar


T = TypeVar("T")
K = TypeVar("K")


def groupdict(
    it: Iterable[T], /, 
    key: Callable[[T], K], 
) -> dict[K, list[T]]:
    """
    """
    d: dict[K, list[T]] = {}
    df: dict[K, Callable] = {}
    for i in it:
        try:
            k = key(i)
        except Exception as exc:
            raise ValueError(f"Can't get the key of {i!r}") from exc
        try:
            df[k](i)
        except KeyError:
            l = d[k] = [i]
            df[k] = l.append
    return d

