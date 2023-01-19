#!/usr/bin/env python3
# coding: utf-8

__author__ = "ChenyangGao <https://chenyanggao.github.io/>"
__version__ = (0, 0, 1)
__all__ = ["path_iter", "path_scan", "path_recur"]

from collections import deque
from os import access, fsdecode, listdir, scandir, DirEntry, PathLike, R_OK
from os.path import isdir, islink, join
from typing import AnyStr, Callable, Generator, Iterable
from pathlib import Path


def path_iter(
    path: AnyStr | PathLike[AnyStr] = ".", # type: ignore
    filter_func: None | Callable[[Path], bool] = None, 
    follow_symlinks: bool = True, 
    lazy: bool = True, 
) -> Generator[Path, None, None]:
    """
    """
    if not isdir(path):
        raise NotADirectoryError(path)
    dq: deque[Path] = deque()
    get, put = dq.popleft, dq.append
    dir_: Path = Path(fsdecode(path))
    try:
        paths: Iterable[Path]
        while True:
            if access(dir_, R_OK):
                paths = dir_.iterdir()
                if filter_func:
                    paths = filter(filter_func, paths)
                if not lazy:
                    paths = tuple(paths)
                for p in paths:
                    yield p
                    if p.is_dir() and (not p.is_symlink() or follow_symlinks):
                        put(p)
            dir_ = get()
    except IndexError:
        pass


def path_scan(
    path: AnyStr | PathLike[AnyStr] = ".", # type: ignore
    filter_func: None | Callable[[DirEntry[AnyStr]], bool] = None, 
    follow_symlinks: bool = True, 
    lazy: bool = True, 
) -> Generator[DirEntry[AnyStr], None, None]:
    """
    """
    if not isdir(path):
        raise NotADirectoryError(path)
    dq: deque[DirEntry] = deque()
    get, put = dq.popleft, dq.append
    try:
        paths: Iterable[DirEntry[AnyStr]]
        while True:
            if access(path, R_OK):
                paths = scandir(path)
                if filter_func:
                    paths = filter(filter_func, paths)
                if not lazy:
                    paths = tuple(paths)
                for p in paths:
                    yield p
                    if p.is_dir() and (not p.is_symlink() or follow_symlinks):
                        put(p)
            path = get()
    except IndexError:
        pass


def path_recur(
    path: AnyStr | PathLike[AnyStr] = ".", # type: ignore
    filter_func: None | Callable[[AnyStr], bool] = None, 
    follow_symlinks: bool = True, 
) -> Generator[AnyStr, None, None]:
    """
    """
    if not isdir(path):
        raise NotADirectoryError(path)
    dq: deque[AnyStr] = deque()
    get, put = dq.popleft, dq.append
    try:
        paths: Iterable[AnyStr]
        while True:
            if access(path, R_OK):
                paths = (join(path, p) for p in listdir(path))
                if filter_func:
                    paths = filter(filter_func, paths)
                for p in paths:
                    yield p
                    if isdir(p) and (not islink(p) or follow_symlinks):
                        put(p)
            path = get()
    except IndexError:
        pass

