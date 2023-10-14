#!/usr/bin/env python3
# coding: utf-8

__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 0)
__all__ = ['cm', 'acm', 'ensure_cm', 'ensure_acm']

from contextlib import asynccontextmanager, contextmanager, ExitStack, AsyncExitStack
from typing import AsyncContextManager, ContextManager


@contextmanager
def cm(yield_=None, /):
    yield yield_


@asynccontextmanager
async def acm(yield_=None, /):
    yield yield_


def ensure_cm(
    obj, /, default=None
) -> ContextManager:
    if hasattr(type(obj), '__enter__'):
        return obj
    if default is None:
        default = obj
    return cm(default)


def ensure_acm(
    obj, /, default=None
) -> AsyncContextManager:
    if hasattr(type(obj), '__aenter__'):
        return obj
    if default is None:
        default = obj
    return acm(default)

