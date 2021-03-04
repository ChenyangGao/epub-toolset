from functools import partial
from itertools import count
from os import path, urandom
from typing import Any, Callable, Mapping, Optional, Union
from uuid import uuid4

from util.basechars import BaseCharsProduct
from util.inspect import argcount, int_to_bytes


__all__ = ['BASE4CHARS', 'BASE2CHARS', 'NAME_GENERATORS', 'register',
           'make_generator', 'make_bcp_generator']


# 所有在 Windows 上的文件名非法字符
WIN_INVALID_CHARS = r'/\:*?"<>|'
# 3 个 Windows 下文件名非法字符和字符 _ （因为非法字符会被处理成 _ ）
BASE4CHARS = r':*|_'
# 2 个 Windows 下文件名非法字符
BASE2CHARS = r':*'
# 文件名生成器
NAME_GENERATORS = {}


def register(fn=None, *, name=None):
    '把函数注册到文件名生成器中（模块全局变量 NAME_GENERATORS）'
    if fn is None:
        return partial(register, name=name)
    if name is None:
        name = fn.__name__
    NAME_GENERATORS[name] = fn
    return fn


@register
def get_item_href_stem(attrib: Mapping) -> str:
    '返回文件名（不包括扩展名），可用于不想改变文件名的情况'
    return path.splitext(path.basename(attrib['href']))[0]


@register
def get_enum_id(*, _c=count(1)) -> int:
    '第一次调用，得到 1，以后每一次调用，得到的是前 1 次的值 + 1'
    return next(_c)


@register
def get_id(attrib: Any) -> int:
    '返回对象的 id 值，在 CPython 中就是对象的内存地址'
    return id(attrib)


@register
def get_uuid() -> bytes:
    '获取一个随机的 uuid (使用 uuid.uuid4() 生成)'
    return uuid4().bytes


@register
def get_item_id(attrib: Mapping) -> str:
    '文件名为 OPF 文件内对应 item 元素的 id 属性'
    return attrib['id']


@register
def get_urandom(
    *, size: int=5, max_collisions: int=8, _dup=set(),
) -> bytes:
    '使用 os.urandom 产生一个指定长度（默认为 5）的字节字符串'
    b = urandom(size)
    collision_count = 0
    while b in _dup:
        collision_count += 1
        if collision_count > max_collisions:
            raise RuntimeError('Too many collisions!')
        b = urandom(size)
    _dup.add(b)
    return b


def _as_str(o: Any) -> str:
    '把对象处理为字符串'
    if isinstance(o, (bytes, bytearray)):
        return o.decode('latin-1')
    return str(o)


def _as_bytes(o: Any) -> bytes:
    '把对象处理为字节字符串'
    if isinstance(o, int):
        return int_to_bytes(o)
    elif isinstance(o, str):
        return o.encode('latin-1')
    try:
        return bytes(o)
    except TypeError:
        return str(o).encode('latin-1')


def make_generator(
    gen: Callable[..., Union[int, bytes, str]],
    doc: Optional[str] = None,
    name: Optional[str] = None,
) -> Callable[..., str]:
    ac: int = argcount(gen)
    generate: Callable[..., str]
    if ac == 0:
        def generate(attrib: Mapping) -> str:
            return _as_str(gen())
    elif ac == 1:
        def generate(attrib: Mapping) -> str:
            return _as_str(gen(attrib))
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
    bcp = BaseCharsProduct(chars)
    if ac == 0:
        def generate(attrib: Mapping) -> str:
            return bcp.encode(_as_bytes(gen()))
    elif ac == 1:
        def generate(attrib: Mapping) -> str:
            return bcp.encode(_as_bytes(gen(attrib)))
    elif ac == 2:
        def generate(attrib: Mapping) -> str:
            return bcp.encode(_as_bytes(gen(attrib, bcp)))
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

