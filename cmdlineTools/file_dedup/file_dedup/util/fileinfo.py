#!/usr/bin/env python3
# coding: utf-8

__author__ = "ChenyangGao <https://chenyanggao.github.io/>"
__version__ = (0, 0, 2)
__all__ = ["FileInfo"]

from hashlib import algorithms_available
from os import fsdecode, stat, stat_result, DirEntry, PathLike
from os.path import basename, dirname, splitext, isdir
from typing import Any, Callable, Generator, Type, TypeVar

from util.filehash import filehash
from util.iterpath import path_scan
from util.lazyproperty import lazyproperty


T = TypeVar("T", bound="FileInfo")


class FileInfo:
    """
    """
    def __init__(
        self, /, 
        path: bytes | str | PathLike, 
    ):
        if isdir(path):
            raise IsADirectoryError(path)
        self.path: str = fsdecode(path)

    @lazyproperty
    def dir(self, /) -> str:
        return dirname(self.path)

    @lazyproperty
    def name(self, /) -> str:
        return basename(self.path)

    @lazyproperty
    def stem(self, /) -> str:
        return splitext(basename(self.path))[1]

    @lazyproperty
    def ext(self, /) -> str:
        return splitext(self.path)[1]

    @property
    def stat(self, /) -> stat_result:
        return stat(self.path)

    def hash(self, /, algname: str = "md5") -> str:
        attrname = algname.replace("-", "_")
        try:
            return self.__dict__[attrname]
        except:
            value = self.__dict__[attrname] = filehash(self.path, algname)
            return value
        raise ValueError(f"Hash algorithm name unavailable: {algname!r}")

    def __fspath__(self):
        return self.path

    def __repr__(self) -> str:
        return f"{type(self).__module__}.{type(self).__qualname__}({self.path!r})"

    def __getattr__(self, name: str, /):
        if name in algorithms_available:
            return self.hash(name)
        if "_" in name:
            name2 = name.replace("_", "-")
            if name2 in algorithms_available:
                return self.hash(name2)
        raise AttributeError(name)

    def __setattr__(self, name: str, value, /):
        if name in self.__dict__:
            raise AttributeError(f"Property {name!r} can only be set once")
        self.__dict__[name] = value

    @classmethod
    def iter(
        cls: Type[T], /, 
        path: bytes | str | PathLike = ".", 
        filter_func: None | Callable[[DirEntry], bool] = None, 
        followlinks: bool = False, 
        onerror: None | Callable[[BaseException], Any] = None, 
    ) -> Generator[T, None, None]:
        """
        """
        if not isdir(path):
            raise NotADirectoryError(path)
        paths = path_scan(
            path, # type: ignore
            filter_func=filter_func, 
            followlinks=followlinks, 
            onerror=onerror, 
        )
        for p in paths:
            if p.is_file(followlinks=followlinks):
                try:
                    yield cls(p)
                except KeyboardInterrupt:
                    raise
                except BaseException as exc:
                    if not (onerror is None or onerror(exc) is None):
                        raise

