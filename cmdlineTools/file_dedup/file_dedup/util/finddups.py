#!/usr/bin/env python3
# coding: utf-8

__author__ = "ChenyangGao <https://chenyanggao.github.io/>"
__version__ = (0, 0, 2)
__all__ = ["find_dup_files", "find_dup_files_by_size_md5", "FileSizeMd5"]

from functools import partial
from itertools import chain
from os import fsdecode, get_terminal_size, DirEntry, PathLike
from os.path import isdir, realpath
from sys import stdout
from typing import (
    Callable, Generator, Iterable, NamedTuple, TypeVar
)

from util.group import groupdict
from util.fileinfo import FileInfo
from util.progress import clear_lines, output


T = TypeVar("T")
K = TypeVar("K")


class FileSizeMd5(NamedTuple):
    size: int
    md5: str


# TODO: 再增加函数：1. 允许传入路径，然后计算所有的key的集合
#                   2. 允许传入2组路径，A用于获取key集合，B用于和A做比对，找出A中有的key判定为重复
def find_dup_files(
    *paths: bytes | str | PathLike | Iterable[bytes | str | PathLike], 
    key: Callable[[T], K], 
    fileinfo_iter: Callable[
        [bytes | str | PathLike], 
        Iterable[T], 
    ], 
    show_progress: bool = False, 
) -> Generator[tuple[K, list[T]], None, None]:
    """
    """
    seen: set[str] = set()

    def nondup(i, seen=seen, add=True):
        p = realpath(fsdecode(i))
        if p not in seen:
            if add:
                seen.add(p)
            return True
        return False

    def dedup(it, seen=seen):
        return (i for i in it if nondup(i, seen))

    if show_progress:
        def wrap_with_progress(paths):
            def output_skip(path):
                nonlocal last_nlines
                path = fsdecode(path)
                if last_nlines:
                    if last_nlines < 0:
                        clear_lines(4)
                    else:
                        clear_lines(last_nlines)
                write(f"SKIPPED []> {path!r}\n")
                msg = f"""
\x1b[38;5;15m\x1b[48;5;4m\x1b[5mSCANNING…\x1b[0m path \x1b[1m{dir_no}\x1b[0m of \x1b[1m{n_dirs}\x1b[0m: {dir_!r}
\x1b[38;5;15m\x1b[48;5;2m\x1b[5mPROCESSED\x1b[0m \x1b[1m{path_no}\x1b[0m files
\x1b[38;5;15m\x1b[48;5;1m\x1b[5mSKIPPED..\x1b[0m \x1b[1mPATH\x1b[0m: {path!r}"""
                last_nlines = output("-" * get_terminal_size().columns + msg)

            def filter_early(path: bytes | str | PathLike) -> bool:
                if not nondup(dir_, add=isdir(dir_)):
                    output_skip(dir_)
                    return False
                return True

            write = stdout.write
            n_dirs = len(paths)
            last_nlines = 0
            path_no = 0

            for dir_no, dir_ in enumerate(paths, 1):
                if isinstance(dir_, (bytes | str | PathLike)):
                    dirs = (dir_,)
                else:
                    dirs = dir_
                it = chain.from_iterable(map(fileinfo_iter, filter(filter_early, dirs)))
                for path_no, fi in enumerate(it, path_no+1):
                    if not nondup(fi):
                        output_skip(fi)
                        continue
                    yield fi
                    if last_nlines:
                        if last_nlines < 0:
                            clear_lines(4)
                        else:
                            clear_lines(last_nlines)
                    # NOTE: You can use the following module to generate styled string in terminal:
                    #     - https://pypi.org/project/colored/
                    k = key(fi)
                    write(f"PROCESSED [KEY {k!r}]> {fi.path!r}\n")
                    msg = f"""
\x1b[38;5;15m\x1b[48;5;4m\x1b[5mSCANNING…\x1b[0m path \x1b[1m{dir_no}\x1b[0m of \x1b[1m{n_dirs}\x1b[0m: {dir_!r}
\x1b[38;5;15m\x1b[48;5;2m\x1b[5mPROCESSED\x1b[0m \x1b[1m{path_no}\x1b[0m files: {fi.path!r}
\x1b[38;5;15m\x1b[48;5;1m\x1b[5mGENERATED\x1b[0m \x1b[1mKEY\x1b[0m: {k!r}"""
                    last_nlines = output("-" * get_terminal_size().columns + msg)
            if last_nlines:
                if last_nlines < 0:
                    clear_lines(4)
                else:
                    clear_lines(last_nlines)
        it = wrap_with_progress(paths)
    else:
        def flatten(it, ignore_types=(bytes, str)):
            for i in it:
                if isinstance(i, Iterable) and not isinstance(i, ignore_types):
                    yield from flatten(i)
                else:
                    yield i
        it = chain.from_iterable(map(fileinfo_iter, dedup(flatten(paths))))
    d: dict[K, list[T]] = groupdict(it, key=key)
    return ((k, v) for k, v in d.items() if len(v) > 1)


def find_dup_files_by_size_md5(
    *paths: bytes | str | PathLike, 
    show_progress: bool = False, 
    filterfn: None | Callable[[DirEntry], bool] = None, 
    followlinks: bool = False, 
) -> Generator[tuple[FileSizeMd5, list[FileInfo]], None, None]:
    return find_dup_files(
        *paths, 
        key=lambda p: FileSizeMd5(p.stat.st_size, p.md5), 
        fileinfo_iter=partial(
            FileInfo.walk, 
            onerror=None, 
            filterfn=filterfn, 
            followlinks=followlinks, 
        ), 
        show_progress=show_progress, 
    )

