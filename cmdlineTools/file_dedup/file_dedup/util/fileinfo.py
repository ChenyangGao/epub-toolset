#!/usr/bin/env python3
# coding: utf-8

__author__ = "ChenyangGao <https://chenyanggao.github.io/>"
__version__ = (0, 0, 2)
__all__ = ["FileInfo"]

from hashlib import algorithms_available
from os import fsdecode, stat, stat_result, DirEntry, PathLike
from os.path import basename, dirname, isdir, isfile, splitext
from pathlib import Path
from typing import (
    Any, AnyStr, Callable, Generator, Iterable, Type, TypeVar
)

if __name__ == "__main__":
    from filehash import filehash # type: ignore
    from iterpath import path_iter, path_walk # type: ignore
    from lazyproperty import lazyproperty # type: ignore
else:
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
        path: AnyStr | PathLike[AnyStr] = ".", # type: ignore
        followlinks: bool = True, 
        filterfn: None | Callable[[Path], bool] = None, 
        skiperrors: None | Callable[[BaseException], Any] | BaseException | tuple[BaseException] = None, 
        depth_first: bool = False, 
        lazy: bool = True, 
    ) -> Generator[T, None, None]:
        """
        """
        if not isdir(path):
            if isfile(path):
                return (yield cls(path))
            raise NotADirectoryError(path)
        paths = path_iter(
            path, 
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
                if (skiperrors and callable(exc) and skiperrors(exc) # type: ignore
                        or not isinstance(exc, skiperrors)): # type: ignore
                    raise

    @classmethod
    def walk(
        cls: Type[T], /, 
        path: AnyStr | PathLike[AnyStr] = ".", # type: ignore
        followlinks: bool = True, 
        onerror: None | Callable[[BaseException], Any] = None, 
        topdown: bool = True, 
        filterfn: None | Callable[[AnyStr], bool] = None, 
        filter_by_name: bool = False, 
    ) -> Generator[T, None, None]:
        """
        """
        if not isdir(path):
            if isfile(path):
                return (yield cls(path))
            raise NotADirectoryError(path)
        paths = path_walk(
            path, 
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


if __name__ == "__main__":
    from itertools import chain
    from os.path import realpath
    from sys import argv, stdin

    # TODO: 允许把结果输出为文件，支持 txt, json, csv, pickle
    key = lambda fi: (fi.stat.st_size, fi.md5)

    paths: Iterable = ()
    if not stdin.isatty():
        # NOTE: find . \( ! -name '.*' \) -type f | python fileinfo.py
        paths = (p for p in (p.removesuffix("\n") for p in stdin) if p)
    paths = chain(paths, argv[1:])

    for path in paths:
        if isdir(path):
            for fi in FileInfo.walk(
                path, 
                filter_by_name=True, 
                filterfn=lambda p: not p.startswith('.'), 
            ):
                try:
                    print("# KEY:", key(fi))
                    print(realpath(fi))
                except OSError as exc:
                    print("# FAILED %r" % realpath(fi))
                    print("#     |_ %r" % exc)
        else:
            try:
                print("# KEY:", key(FileInfo(path)))
                print(realpath(path))
            except OSError as exc:
                print("# FAILED %r" % realpath(path))
                print("#     |_ %r" % exc)

