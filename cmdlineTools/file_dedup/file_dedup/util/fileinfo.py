#!/usr/bin/env python3
# coding: utf-8

from __future__ import annotations

__author__ = "ChenyangGao <https://chenyanggao.github.io/>"
__version__ = (0, 0, 1)
__all__ = ["BaseFileInfo", "FileInfo"]

from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from os import fsdecode, stat, DirEntry, PathLike
from os.path import isdir
from typing import Annotated, Callable, Generator, Iterable, NamedTuple

from util.filehash import filehash
from util.iterpath import path_scan


class BaseFileInfo(ABC):
    path: str

    @abstractmethod
    def from_path(
        cls, /, 
        path: bytes | str | PathLike, 
    ) -> BaseFileInfo:
        ...

    @classmethod
    @abstractmethod
    def iter(
        cls, /, 
        path: bytes | str | PathLike, 
    ) -> Iterable[BaseFileInfo]:
        ...


@BaseFileInfo.register
class FileInfo(NamedTuple):
    path: str
    size: int
    mtime_ns: int
    md5: str

    @classmethod
    def from_path(
        cls, /, 
        path: bytes | str | PathLike, 
    ) -> FileInfo:
        if isdir(path):
            raise IsADirectoryError(path)
        path_ = fsdecode(path)
        fstat = stat(path_)
        return cls(
            path     = path_, 
            size     = fstat.st_size, 
            mtime_ns = fstat.st_mtime_ns, 
            md5      = filehash(path_), 
        )

    @classmethod
    def iter(
        cls, /, 
        path: bytes | str | PathLike = ".", 
        max_workers: int = 1, 
        skip_oserror: bool = False, 
        filter_func: None | Callable[[DirEntry], bool] = None, 
        follow_symlinks: bool = False, 
    ) -> Generator[FileInfo, None, None]:
        """
        """
        paths = (p for p in path_scan(
            path, # type: ignore
            filter_func=filter_func, 
            follow_symlinks=follow_symlinks, 
        ) if p.is_file(follow_symlinks=follow_symlinks))
        make_fileinfo = cls.from_path
        if max_workers == 1:
            for p in paths:
                try:
                    yield make_fileinfo(p)
                except OSError:
                    if not skip_oserror:
                        raise
        else:
            ex = ThreadPoolExecutor(max_workers)
            submit = ex.submit
            try:
                futures = [submit(make_fileinfo, p) for p in paths]
                for fu in futures:
                    try:
                        yield fu.result()
                    except OSError:
                        if not skip_oserror:
                            raise
            finally:
                ex.shutdown(False, cancel_futures=True)

