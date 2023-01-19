#!/usr/bin/env python3
# coding: utf-8

__author__ = "ChenyangGao <https://chenyanggao.github.io/>"
__version__ = (0, 0, 1)
__all__ = ["find_dup_files", "find_dup_files_by_size_md5"]

from functools import partial
from itertools import chain
from os import get_terminal_size, DirEntry, PathLike
from sys import stdout
from typing import Callable, Generator, Iterable, NamedTuple, TypeVar

from util.group import groupdict
from util.fileinfo import FileInfo
from util.progress import clear_last_lines, output


T = TypeVar("T")
K = TypeVar("K")


class FileSizeMd5(NamedTuple):
    size: int
    md5: str


def find_dup_files(
    *dirs: bytes | str | PathLike, 
    key: Callable[[T], K], 
    fileinfo_iter: Callable[
        [bytes | str | PathLike], 
        Iterable[T], 
    ], 
    show_progress: bool = False, 
) -> Generator[tuple[K, list[T]], None, None]:
    """
    """
    if show_progress:
        write = stdout.write
        def wrap_with_progress(dirs):
            n_dirs = len(dirs)
            last_nlines = 0
            fi_no = 0
            for dir_no, dir_ in enumerate(dirs, 1):
                for fi_no, fi in enumerate(fileinfo_iter(dir_), fi_no+1):
                    yield fi
                    if last_nlines:
                        if last_nlines < 0:
                            clear_last_lines(3)
                        else:
                            clear_last_lines(last_nlines-1)
                    # NOTE: You can use the following module to generate styled string in terminal:
                    #     https://pypi.org/project/colored/
                    k = key(fi)
                    write(f"PROCESSED [key {k!r}]> {fi.path!r}\n")
                    msg = f"""
\x1b[38;5;15m\x1b[48;5;4m\x1b[5mSCANNING…\x1b[0m directory \x1b[1m{dir_no}\x1b[0m of \x1b[1m{n_dirs}\x1b[0m: {dir_!r}
\x1b[38;5;15m\x1b[48;5;2m\x1b[5mPROCESSED\x1b[0m \x1b[1m{fi_no}\x1b[0m files: {fi.path!r}
\x1b[38;5;15m\x1b[48;5;1m\x1b[5mGENERATED\x1b[0m \x1b[1mkey\x1b[0m: {k!r}"""
                    last_nlines = output("-" * get_terminal_size().columns + msg)
            if last_nlines:
                if last_nlines < 0:
                    clear_last_lines(3)
                else:
                    clear_last_lines(last_nlines-1)
        it = wrap_with_progress(dirs)
    else:
        it = chain.from_iterable(map(fileinfo_iter, dirs))
    d: dict[K, list[T]] = groupdict(it, key=key)
    return ((k, v) for k, v in d.items() if len(v) > 1)


def find_dup_files_by_size_md5(
    *dirs: bytes | str | PathLike, 
    show_progress: bool = False, 
    filter_func: None | Callable[[DirEntry], bool] = None, 
    follow_symlinks: bool = False, 
) -> Generator[tuple[FileSizeMd5, list[FileInfo]], None, None]:
    return find_dup_files(
        *dirs, 
        key=lambda p: FileSizeMd5(p.size, p.md5), 
        fileinfo_iter=partial(
            FileInfo.iter, 
            skip_oserror=True, 
            filter_func=filter_func, 
            follow_symlinks=follow_symlinks, 
        ), 
        show_progress=show_progress, 
    )

