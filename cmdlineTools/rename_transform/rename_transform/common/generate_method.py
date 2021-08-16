#! /usr/bin/env python3
# coding: utf-8

__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 2)


import posixpath

from functools import partial
from typing import cast, Any, Callable, Dict, Mapping, Optional, Set, Union
from uuid import uuid4
from warnings import warn

random_bytes: Callable[[int], bytes]
try:
    from secrets import token_bytes as random_bytes
except ImportError:
    from os import urandom as random_bytes
# OR from random import randbytes as random_bytes

from util.basechars import BaseChars
from util.matter import argcount, astype_str, as_closure
from util.path import split_components, split3


__all__ = ['WIN_INVALID_CHARS', 'BASE4CHARS', 'NAME_GENERATORS', 'register',
           'reset_all', 'make_generator', 'make_bcp_generator']


# 所有在 Windows 上的文件名非法字符
WIN_INVALID_CHARS = r'/\:*?"<>|'
# 3 个 Windows 下文件名非法字符和字符 _ （因为非法字符会被处理成 _ ）
BASE4CHARS = r':*|_'
# 文件名生成器
NAME_GENERATORS = {}


def register(fn=None, *, name=None):
    '把函数注册到文件名生成器中（模块全局变量 NAME_GENERATORS）'
    if fn is None:
        return partial(register, name=name)
    if name is None:
        try:
            name = fn.__name__
        except AttributeError:
            name = hex(id(fn))
    NAME_GENERATORS[name] = fn
    return fn


def reset_all():
    '重置所有的文件名生成器（如果它有 reset 方法的话）'
    for fn in NAME_GENERATORS.values():
        try:
            reset = fn.reset
        except AttributeError:
            pass
        else:
            reset()


@register
@as_closure
def get_enum_id():
    n = 0
    def reset():
        nonlocal n
        n = 0
    def _() -> int:
        '提供全局递增计数，第一次调用，得到 1，以后每一次调用，得到的是前 1 次的值 + 1'
        nonlocal n
        n += 1
        return n
    _.reset = reset # type: ignore
    return _


@register
@as_closure
def get_sep_enum_id():
    cache: Dict[str, int] = {}
    def _(attrib) -> int:
        '为每个文件夹中的文件，分别提供递增计数，从 1 开始递增'
        components = split_components(attrib['href'])
        dir_ = cast(str, components[0] if len(components) > 1 else '')
        if dir_ in cache:
            cache[dir_] += 1
            return cache[dir_]
        else:
            cache[dir_] = 1
            return 1
    _.reset = lambda: cache.clear() # type: ignore
    return _


@register
def get_item_href_stem(attrib: Mapping[str, str]) -> str:
    '返回文件名（不包括所在目录和扩展名）'
    return cast(str, split3(attrib['href'], lib=posixpath)[1])


@register
def get_item_id(attrib: Mapping[str, str]) -> str:
    '文件名为 OPF 文件内对应 item 元素的 id 属性'
    return attrib['id']


@register
def get_id(attrib: Any) -> int:
    '在 CPython 中，返回传入的对象的内存地址（你不需要知道传入什么对象，只需要知道这个 id 是唯一的）'
    return id(attrib)


@register
def get_uuid() -> bytes:
    '获取一个随机的 uuid (使用 uuid.uuid4() 生成，长度为 16 字节)'
    return uuid4().bytes


@register
@as_closure
def get_random_bytes(
    size: int = 5, 
    step: int = 1, 
    max_collisions: int=8, 
):
    assert step > 0
    cache: Set[bytes] = set()
    def _() -> bytes:
        '使用 os.urandom 产生一个指定长度的字节字符串'
        nonlocal size
        collision_count = 0
        while (b := random_bytes(size)) in cache:
            collision_count += 1
            if collision_count > max_collisions:
                warn(f'get_random_bytes has been updated {size=}, {step=}, {max_collisions=}')
                collision_count = 0
                size += step
                cache.clear()
        cache.add(b)
        return b
    _.reset = lambda: cache.clear() # type: ignore
    return _


def make_generator(
    gen: Callable[..., Union[int, bytes, str]],
    doc: Optional[str] = None,
    name: Optional[str] = None,
) -> Callable[..., str]:
    ac: int = argcount(gen)
    generate: Callable[..., str]
    if ac == 0:
        def generate(attrib: Mapping[str, str]) -> str:
            return astype_str(gen())
    elif ac == 1:
        def generate(attrib: Mapping[str, str]) -> str:
            return astype_str(gen(attrib))
    else:
        raise TypeError(
            f'{gen!r} has {ac} parameters, but at most 1 is accepted')
    if doc:
        generate.__doc__ = doc
    else:
        generate.__doc__ = getattr(gen, '__doc__', '')
    if name:
        generate.__name__ = name
    else:
        generate.__name__ = getattr(gen, '__name__', repr(gen))
    return generate


def make_bcp_generator(
    gen: Callable[..., bytes],
    chars: str = BASE4CHARS,
    doc: Optional[str] = None,
    name: Optional[str] = None,
) -> Callable[..., str]:
    ac: int = argcount(gen)
    generate: Callable[..., str]
    bcp = BaseChars(chars)
    if ac == 0:
        def generate(attrib: Mapping[str, str]) -> str:
            return bcp.encode(gen())
    elif ac == 1:
        def generate(attrib: Mapping[str, str]) -> str:
            return bcp.encode(gen(attrib))
    elif ac == 2:
        def generate(attrib: Mapping[str, str]) -> str:
            return bcp.encode(gen(attrib, bcp))
    else:
        raise TypeError(
            f'{gen!r} has {ac} parameters, but at most 2 is accepted')
    if not doc:
        doc = gen.__doc__
    if name:
        generate.__name__ = name
    else:
        name = generate.__name__ = getattr(gen, '__name__', repr(gen))
    generate.__doc__ = (
f'''首先调用 {name}，它会【
    {doc}
】，再把得到的返回值用 {len(chars)} 个字符 {chars} 的可重排列\
逐字节转换（类比 base64 编码）''')
    return generate

