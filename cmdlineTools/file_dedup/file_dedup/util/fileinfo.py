#!/usr/bin/env python3
# coding: utf-8

__author__ = "ChenyangGao <https://chenyanggao.github.io/>"
__version__ = (0, 0, 2)
__all__ = ["FileInfo"]

from hashlib import algorithms_available
from os import fsdecode, stat, stat_result, DirEntry, PathLike
from os.path import basename, dirname, splitext, isdir
from pathlib import Path
from typing import Any, AnyStr, Callable, Generator, Type, TypeVar

from util.filehash import filehash
from util.iterpath import path_iter, path_walk
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

    def __eq__(self, other):
        if type(self) is type(other):
            return self.path == other.path
        return False

    def __hash__(self):
        return hash(self.path)

    def __fspath__(self):
        return self.path

    def __repr__(self) -> str:
        modname = type(self).__module__
        if modname == "__main__":
            return f"{type(self).__qualname__}({self.path!r})"
        else:
            return f"{modname}.{type(self).__qualname__}({self.path!r})"

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
        dir_: AnyStr | PathLike[AnyStr] = ".", # type: ignore
        followlinks: bool = True, 
        filterfn: None | Callable[[Path], bool] = None, 
        skiperrors: None | Callable[[BaseException], Any] | BaseException | tuple[BaseException] = None, 
        depth_first: bool = False, 
        lazy: bool = True, 
    ) -> Generator[T, None, None]:
        """
        """
        if not isdir(dir_):
            raise NotADirectoryError(dir_)
        paths = path_iter(
            dir_, 
            followlinks=followlinks, 
            filterfn=filterfn, 
            skiperrors=skiperrors, 
            depth_first=depth_first, 
            lazy=lazy, 
        )
        for p in filter(Path.is_file, paths):
            try:
                yield cls(p)
            except KeyboardInterrupt:
                raise
            except BaseException as exc:
                if skiperrors and callable(exc) and skiperrors(exc) or not isinstance(exc, skiperrors): # type: ignore
                    raise

    @classmethod
    def walk(
        cls: Type[T], /, 
        dir_: AnyStr | PathLike[AnyStr] = ".", # type: ignore
        followlinks: bool = True, 
        onerror: None | Callable[[BaseException], Any] = None, 
        topdown: bool = True, 
        filterfn: None | Callable[[AnyStr], bool] = None, 
        filter_by_name: bool = False, 
    ) -> Generator[T, None, None]:
        """
        """
        if not isdir(dir_):
            raise NotADirectoryError(dir_)
        paths = path_walk(
            dir_, 
            followlinks=followlinks, 
            onerror=onerror, 
            topdown=topdown, 
            filterfn=filterfn, 
            filter_by_name=filter_by_name, 
            only_files=True, 
        )
        for p in paths:
            try:
                yield cls(p)
            except KeyboardInterrupt:
                raise
            except BaseException as exc:
                if onerror and onerror(exc):
                    raise

