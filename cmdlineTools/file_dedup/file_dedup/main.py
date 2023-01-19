#!/usr/bin/env python3
# coding: utf-8

# TODO: 允许过滤掉某些文件夹或文件名
# TODO: 如果文件名里面有空格呢

__author__ = "ChenyangGao <https://chenyanggao.github.io/>"
__version__ = (0, 0, 1)
__all__ = ["main"]


from io import StringIO, TextIOBase
from os import remove, PathLike
from os.path import join
from sys import argv, stdout
from tempfile import gettempdir
from typing import Generator
from uuid import uuid4

from util.fileinfo import FileInfo
from util.finddups import find_dup_files_by_size_md5, FileSizeMd5
from util.openpath import openpath
from util.progress import output, clear_last_lines


write = stdout.write


def dumps_duplicate_files_to_be_deleted(
    *dirs: bytes | str | PathLike, 
) -> str:
    it = find_dup_files_by_size_md5(*dirs, show_progress=True)
    f = StringIO()
    write = f.write
    for k, v in it:
        write(f"#key: {k!r}\n")
        for i, d in enumerate(v):
            if i:
                write(f"{d.path}\n")
            else:
                write(f"#{d.path}\n")
        write("\n")
    return f.getvalue()


def parse_duplicate_files_to_be_deleted(
    dumps: str | TextIOBase, /
) -> Generator[str, None, None]:
    f: TextIOBase
    if isinstance(dumps, str):
        f = StringIO(dumps)
    else:
        f = dumps
    for line in f:
        if line.startswith("#") or not line.strip():
            continue
        yield line.removesuffix("\n")


def main(argv: list[str]):
    dumps = dumps_duplicate_files_to_be_deleted(*argv[1:])
    if not dumps:
        #print("😄 There are no duplicate files")
        write("😄 没有重复文件\n")
        return
    temppath = join(gettempdir(), f"{uuid4()}.txt")
    open(temppath, "w", encoding="utf-8").write(dumps)
    try:
        write(f"""
已生成文件列表，写入文本文件
{temppath!r}
请编辑上面的文本文件，对于不需要删除的文件，请用#注释掉路径
""")
        try:
            openpath(temppath)
        except:
            pass
        resp = input("需要进行删除吗？[Y]/n ").strip()
        n_succ = n_fail = 0
        last_nlines = 0
        if resp in ("y", "Y", ""):
            paths = tuple(parse_duplicate_files_to_be_deleted(
                open(temppath, encoding="utf-8")))
            total = len(paths)
            for path in paths:
                if last_nlines:
                    clear_last_lines(last_nlines-1)
                try:
                    remove(path)
                    n_succ += 1
                    write(f"DELETED {path!r}\n")
                except OSError:
                    n_fail += 1
                    write(f"?FAILED {path!r}\n")
                last_nlines = output(f"""
\x1b[38;5;15m\x1b[48;5;1m\x1b[5mPROCESSING\x1b[0m success: \x1b[1m{n_succ}\x1b[0m / failed: \x1b[1m{n_fail}\x1b[0m / total: \x1b[1m{total}\x1b[0m
""")
            if last_nlines:
                clear_last_lines(last_nlines-1)
            output(f"""
\x1b[38;5;15m\x1b[48;5;2m\x1b[5mRESULT\x1b[0m success: \x1b[1m{n_succ}\x1b[0m / failed: \x1b[1m{n_fail}\x1b[0m / total: \x1b[1m{total}\x1b[0m
""")
    finally:
        try:
            remove(temppath)
        except OSError:
            pass


if __name__ == "__main__":
    main(argv)

