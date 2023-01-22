#!/usr/bin/env python3
# coding: utf-8

__author__ = "ChenyangGao <https://chenyanggao.github.io/>"
__version__ = (0, 0, 2)
__all__ = ["path_iter", "path_scan", "path_recur", "path_walk"]

from collections import deque
from functools import update_wrapper
from os import fsdecode, listdir, scandir, walk, DirEntry, PathLike
from os.path import isdir, islink, join
from typing import cast, Any, AnyStr, Callable, Generator, Iterable
from pathlib import Path


def _check_dir(fn, /):
    def wrapper(dir_, *args, **kwds):
        if not isdir(dir_):
            raise NotADirectoryError(dir_)
        return fn(dir_, *args, **kwds)
    return update_wrapper(wrapper, fn)


@_check_dir
def path_iter(
    dir_: AnyStr | PathLike[AnyStr] = ".", # type: ignore
    /, 
    filter_func: None | Callable[[Path], bool] = None, 
    followlinks: bool = True, 
    onerror: None | Callable[[BaseException], Any] = None, 
    lazy: bool = True, 
    depth_first: bool = False, 
) -> Generator[Path, None, None]:
    """
    """
    if isinstance(dir_, Path):
        dir2 = dir_
    else:
        dir2 = Path(fsdecode(dir_))

    def iterdir(dir_: Path) -> Iterable[Path]:
        paths: Iterable[Path]
        try:
            paths = dir_.iterdir()
        except BaseException as exc:
            if not (onerror is None or onerror(exc) is None):
                raise
        else:
            if filter_func:
                paths = filter(filter_func, paths)
            if not lazy:
                paths = tuple(paths)
            yield from paths

    if depth_first:
        for p in iterdir(dir2):
            yield p
            if p.is_dir() and (not p.is_symlink() or followlinks):
                yield from path_iter(
                    p, 
                    filter_func=filter_func, 
                    followlinks=followlinks, 
                    onerror=onerror, 
                    lazy=lazy, 
                    depth_first=depth_first, 
                )
    else:
        dq = deque((dir2,))
        get, put = dq.popleft, dq.append
        while dq:
            dir2 = get()
            for p in iterdir(dir2):
                yield p
                if p.is_dir() and (not p.is_symlink() or followlinks):
                    put(p)


@_check_dir
def path_scan(
    dir_: AnyStr | PathLike[AnyStr] = ".", # type: ignore
    /, 
    filter_func: None | Callable[[DirEntry[AnyStr]], bool] = None, 
    followlinks: bool = True, 
    onerror: None | Callable[[BaseException], Any] = None, 
    lazy: bool = True, 
    depth_first: bool = False, 
) -> Generator[DirEntry[AnyStr], None, None]:
    """
    """
    def iterdir(dir_: AnyStr | PathLike[AnyStr]) -> Iterable[DirEntry[AnyStr]]:
        paths: Iterable[DirEntry[AnyStr]]
        try:
            paths = scandir(dir_)
        except BaseException as exc:
            if not (onerror is None or onerror(exc) is None):
                raise
        else:
            if filter_func:
                paths = filter(filter_func, paths)
            if not lazy:
                paths = tuple(paths)
            yield from paths

    if depth_first:
        for p in iterdir(dir_):
            yield p
            if p.is_dir() and (not p.is_symlink() or followlinks):
                yield from path_scan(
                    p, 
                    filter_func=filter_func, 
                    followlinks=followlinks, 
                    onerror=onerror, 
                    lazy=lazy, 
                    depth_first=depth_first, 
                )
    else:
        dq = deque((dir_,))
        get, put = dq.popleft, dq.append
        while dq:
            dir_ = get()
            for p in iterdir(dir_):
                yield p
                if p.is_dir() and (not p.is_symlink() or followlinks):
                    put(p)


@_check_dir
def path_recur(
    dir_: AnyStr | PathLike[AnyStr] = ".", # type: ignore
    /, 
    filter_func: None | Callable[[AnyStr], bool] = None, 
    filter_by_name: bool = False, 
    followlinks: bool = True, 
    onerror: None | Callable[[BaseException], Any] = None, 
    depth_first: bool = False, 
) -> Generator[AnyStr, None, None]:
    """
    """
    def iterdir(dir_: AnyStr | PathLike[AnyStr]) -> Iterable[AnyStr]:
        paths: Iterable[AnyStr]
        try:
            paths = listdir(dir_)
        except BaseException as exc:
            if not (onerror is None or onerror(exc) is None):
                raise
        else:
            if filter_by_name:
                if filter_func:
                    paths = filter(filter_func, paths)
                for p in paths:
                    yield join(dir_, p)
            else:
                paths = (join(dir_, p) for p in paths)
                if filter_func:
                    paths = filter(filter_func, paths)
                yield from paths

    if depth_first:
        for p in iterdir(dir_):
            yield p
            if isdir(p) and (not islink(p) or followlinks):
                yield from path_scan(
                    p, 
                    filter_func=filter_func, 
                    followlinks=followlinks, 
                    onerror=onerror, 
                    depth_first=depth_first, 
                )
    else:
        dq = deque((dir_,))
        get, put = dq.popleft, dq.append
        while dq:
            dir_ = get()
            for p in iterdir(dir_):
                yield p
                if isdir(p) and (not islink(p) or followlinks):
                    put(p)


@_check_dir
def path_walk(
    dir_: AnyStr | PathLike[AnyStr] = ".", # type: ignore
    /, 
    filter_func: None | Callable[[AnyStr], bool] = None, 
    filter_by_name: bool = False, 
    followlinks: bool = True, 
    onerror: None | Callable[[BaseException], Any] = None, 
    topdown: bool = True, 
    only_files: bool = False, 
) -> Generator[AnyStr, None, None]:
    """
    """
    it = walk(
        dir_, 
        topdown=topdown, 
        onerror=onerror, 
        followlinks=followlinks, 
    )
    if filter_func is None:
        for dirpath, dirnames, filenames in it:
            if not only_files:
                yield from (join(dirpath, name) for name in dirnames)
            yield from (join(dirpath, name) for name in filenames)
    elif filter_by_name:
        for dirpath, dirnames, filenames in it:
            if not only_files:
                yield from (join(dirpath, name) 
                    for name in dirnames if filter_func(name))
            yield from (join(dirpath, name) 
                for name in filenames if filter_func(name))
    else:
        for dirpath, dirnames, filenames in it:
            if not only_files:
                yield from filter(filter_func, 
                    (join(dirpath, name) for name in dirnames))
            yield from filter(filter_func, 
                (join(dirpath, name) for name in filenames))


if __name__ == "__main__":
    from sys import argv

    for path in argv[1:]:
        if isdir(path):
            for subpath in path_walk(
                path, 
                filter_func=lambda x: not x.startswith('.'), 
                filter_by_name=True, 
                only_files=True, 
            ):
                print(subpath)
        else:
            print(path)

