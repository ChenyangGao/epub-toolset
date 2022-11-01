__all__ = [
    'startswith_protocol', 'relative_path', 'ElementPath', 'get_path', 
    'get_xpath', 'get_csssel', 
]

from __future__ import annotations
from itertools import takewhile
from os import path
from types import ModuleType
from typing import overload, NamedTuple, Optional, Union

from lxml.etree import _Element # type: ignore


def startswith_protocol(
    link: str, 
    _cre=__import__('re').compile('^(?a:\w)+://'), 
):
    return _cre.match(link) is not None


@overload
def split(
    s: bytes, 
    sep: Optional[bytes], 
    maxsplit: int, 
    start: int
) -> list[bytes]:
    ...
@overload
def split(
    s: str, 
    sep: Optional[str], 
    maxsplit: int, 
    start: int
) -> list[str]:
    ...
def split(
    s, 
    sep=None, 
    maxsplit=-1, 
    start=0, 
):
    if start == 0:
        return s.split(sep, maxsplit)
    prefix, remain = s[:start], s[start:]
    parts = remain.split(sep, maxsplit)
    parts[0] = prefix + parts[0]
    return parts


@overload
def relative_path(
    ref_path: bytes, 
    rel_path: Union[bytes, str], 
    lib: ModuleType, 
) -> bytes:
    ...
@overload
def relative_path(
    ref_path: str, 
    rel_path: Union[bytes, str], 
    lib: ModuleType, 
) -> str:
    ...
def relative_path(
    ref_path, 
    rel_path = '.', 
    lib = path, 
):
    'Relative to the directory of `rel_path`, return the path of `file_path`.'
    curdir, pardir, sep = lib.curdir, lib.pardir, lib.sep

    if isinstance(ref_path, bytes):
        curdir, pardir, sep = curdir.encode(), pardir.encode(), sep.encode()
        if isinstance(rel_path, str):
            rel_path = rel_path.encode()
    elif isinstance(rel_path, bytes):
        rel_path = rel_path.decode()

    if not ref_path:
        return rel_path

    dir_path = lib.dirname(rel_path)
    if not dir_path or dir_path == curdir or lib.isabs(ref_path):
        return ref_path

    drive, dir_path = lib.splitdrive(dir_path)
    dir_path_isabs = bool(drive or dir_path.startswith(sep))
    dir_parts = split(dir_path, sep, start=1)
    ref_parts = ref_path.split(sep)
    try:
        for i, p in enumerate(ref_parts):
            if p == curdir:
                continue
            elif p == pardir and dir_parts[-1] != pardir:
                if dir_parts.pop() == sep:
                    raise IndexError
            else:
                dir_parts.append(p)
        result_path = lib.join(drive, *dir_parts)
        if dir_path_isabs and not result_path.startswith(sep):
            return sep + result_path
        return result_path
    except IndexError:
        if dir_path_isabs:
            raise ValueError(
                f'{ref_path} relative to {rel_path} exceeded the root directory')
        return lib.join(*ref_parts[i:])


class ElementPath(NamedTuple):
    filepath: str
    path: tuple[int, ...]
    xpath: str
    csssel: str

    @classmethod
    def of(cls, el: _Element, filepath: str = '.') -> ElementPath:
        return cls(filepath, get_path(el), get_xpath(el), get_csssel(el))

    def __str__(self) -> str:
        return '%s:%s' % (self.filepath, self.xpath)

    def __eq__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        return self.filepath == other.filepath and self.path == other.path

    def __gt__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        if self.filepath != other.filepath:
            raise ValueError('Not in the same file, the size is not comparable')
        return self.path > other.path

    def __ge__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        if self.filepath != other.filepath:
            raise ValueError('Not in the same file, the size is not comparable')
        return self.path >= other.path

    def __lt__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        if self.filepath != other.filepath:
            raise ValueError('Not in the same file, the size is not comparable')
        return self.path < other.path

    def __le__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        if self.filepath != other.filepath:
            raise ValueError('Not in the same file, the size is not comparable')
        return self.path <= other.path


def get_path(el: _Element) -> tuple[int, ...]:
    ls: list[int] = []
    push = ls.append
    for parent in el.iterancestors():
        push(parent.index(el))
        el = parent
    return tuple(reversed(ls))


def get_xpath(el: _Element) -> str:
    ls: list[str] = []
    push = ls.append
    for parent in el.iterancestors():
        tag = el.tag
        push('/%s[%d]' % (
            tag, sum((e.tag == tag for e in 
                takewhile(lambda e: e is not el, parent)), start=1)))
        el = parent
    else:
        push('/' + el.tag)
    return ''.join(reversed(ls))


def get_csssel(el: _Element) -> str:
    ls: list[str] = []
    push = ls.append
    for parent in el.iterancestors():
        push('%s:nth-child(%d)' % (el.tag, parent.index(el) + 1))
        el = parent
    else:
        push(el.tag)
    return '>'.join(reversed(ls))

