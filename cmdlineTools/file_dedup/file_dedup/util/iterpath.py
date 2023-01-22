#!/usr/bin/env python3
# coding: utf-8

__author__ = "ChenyangGao <https://chenyanggao.github.io/>"
__version__ = (0, 0, 2)
__all__ = ["path_iter", "path_scan", "path_recur", "path_walk"]

from collections import deque
from functools import update_wrapper
from os import (
    fsdecode, listdir, scandir, walk, DirEntry, PathLike
)
from os.path import isdir, isfile, islink, join
from typing import (
    cast, Any, AnyStr, Callable, Generator, Iterable, 
    Sequence, TypeVar, 
)
from pathlib import Path


P = TypeVar("P", bytes, str, PathLike[bytes], PathLike[str])


def _check_dir(fn, /):
    def wrapper(dir_, *args, **kwds):
        if not isdir(dir_):
            raise NotADirectoryError(dir_)
        return fn(dir_, *args, **kwds)
    return update_wrapper(wrapper, fn)


@_check_dir
def path_iterate(
    iterate: Callable[[AnyStr | PathLike[AnyStr]], Iterable[P]], 
    dir_: AnyStr | PathLike[AnyStr] = ".", # type: ignore
    /, 
    followlinks: bool = True, 
    filterfn: None | Callable[[P], bool] = None, 
    skiperrors: None | Callable[[BaseException], Any] | BaseException | tuple[BaseException] = None, 
    depth_first: bool = False, 
    lazy: bool = True, 
) -> Generator[P, None, None]:
    """
    """
    def iterdir(dir_: AnyStr | PathLike[AnyStr]) -> Iterable[P]:
        paths: Iterable[P]
        try:
            paths = iterate(dir_)
        except BaseException as exc:
            if skiperrors and callable(exc) and skiperrors(exc) or not isinstance(exc, skiperrors): # type: ignore
                raise
            return ()
        else:
            if not lazy and not isinstance(paths, Sequence):
                paths = tuple(paths)
            if not followlinks:
                paths = (p for p in paths if not islink(p))
            if filterfn:
                paths = filter(filterfn, paths)
            return paths

    if depth_first:
        for p in iterdir(dir_):
            yield p
            if isdir(p):
                yield from path_iterate(
                    iterate, p, 
                    followlinks=followlinks, 
                    filterfn=filterfn, 
                    skiperrors=skiperrors, 
                    depth_first=depth_first, 
                    lazy=lazy, 
                )
    else:
        dq: deque[Any] = deque((dir_,))
        get, put = dq.popleft, dq.append
        while dq:
            dir_ = get()
            for p in iterdir(dir_):
                yield p
                if isdir(p):
                    put(p)


@_check_dir
def path_iter(
    dir_: AnyStr | PathLike[AnyStr] = ".", # type: ignore
    /, 
    followlinks: bool = True, 
    filterfn: None | Callable[[AnyStr], bool] = None, 
    skiperrors: None | Callable[[BaseException], Any] | BaseException | tuple[BaseException] = None, 
    depth_first: bool = False, 
    lazy: bool = True, 
) -> Generator[Path, None, None]:
    """
    """
    return path_iterate.__wrapped__(
        Path.iterdir, 
        Path(fsdecode(dir_)), 
        followlinks=followlinks, 
        filterfn=filterfn, 
        skiperrors=skiperrors, 
        depth_first=depth_first, 
        lazy=lazy, 
    )


@_check_dir
def path_scan(
    dir_: AnyStr | PathLike[AnyStr] = ".", # type: ignore
    /, 
    followlinks: bool = True, 
    filterfn: None | Callable[[AnyStr], bool] = None, 
    skiperrors: None | Callable[[BaseException], Any] | BaseException | tuple[BaseException] = None, 
    depth_first: bool = False, 
    lazy: bool = True, 
) -> Generator[DirEntry[AnyStr], None, None]:
    """
    """
    return path_iterate.__wrapped__(
        scandir, 
        dir_, 
        followlinks=followlinks, 
        filterfn=filterfn, 
        skiperrors=skiperrors, 
        depth_first=depth_first, 
        lazy=lazy, 
    )


@_check_dir
def path_recur(
    dir_: AnyStr | PathLike[AnyStr] = ".", # type: ignore
    /, 
    followlinks: bool = True, 
    filterfn: None | Callable[[AnyStr], bool] = None, 
    skiperrors: None | Callable[[BaseException], Any] | BaseException | tuple[BaseException] = None, 
    depth_first: bool = False, 
    lazy: bool = True, 
) -> Generator[DirEntry[AnyStr], None, None]:
    """
    """
    return path_iterate.__wrapped__(
        lambda dir_: (join(dir_, p) for p in listdir(dir_)), 
        dir_, 
        followlinks=followlinks, 
        filterfn=filterfn, 
        skiperrors=skiperrors, 
        depth_first=depth_first, 
        lazy=lazy, 
    )


@_check_dir
def path_walk(
    dir_: AnyStr | PathLike[AnyStr] = ".", # type: ignore
    /, 
    followlinks: bool = True, 
    onerror: None | Callable[[BaseException], Any] = None, 
    topdown: bool = True, 
    filterfn: None | Callable[[AnyStr], bool] = None, 
    filter_by_name: bool = False, 
    only_files: bool = False, 
) -> Generator[AnyStr, None, None]:
    """
    """
    it = walk(
        dir_, 
        followlinks=followlinks, 
        onerror=onerror, 
        topdown=topdown, 
    )
    if filterfn is None:
        for dirpath, dirnames, filenames in it:
            if not only_files:
                yield from (join(dirpath, name) for name in dirnames)
            yield from (join(dirpath, name) for name in filenames)
    elif filter_by_name:
        for dirpath, dirnames, filenames in it:
            if not only_files:
                yield from (join(dirpath, name) 
                    for name in dirnames if filterfn(name))
            yield from (join(dirpath, name) 
                for name in filenames if filterfn(name))
    else:
        for dirpath, dirnames, filenames in it:
            if not only_files:
                yield from filter(filterfn, 
                    (join(dirpath, name) for name in dirnames))
            yield from filter(filterfn, 
                (join(dirpath, name) for name in filenames))


if __name__ == "__main__":
    from sys import argv

    for path in argv[1:]:
        if isdir(path):
            for subpath in path_walk(
                path, 
                filterfn=lambda x: not x.startswith('.'), 
                filter_by_name=True, 
                only_files=True, 
            ):
                print(subpath)
        else:
            print(path)

