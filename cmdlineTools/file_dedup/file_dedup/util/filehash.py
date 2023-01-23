#!/usr/bin/env python3
# coding: utf-8

__author__ = "ChenyangGao <https://chenyanggao.github.io/>"
__version__ = (0, 0, 1)
__all__ = ["filehash", "mfilehash"]

from hashlib import new as hash_new
from io import DEFAULT_BUFFER_SIZE
from os import PathLike
from os.path import getsize


def filehash(
    path: bytes | str | PathLike, 
    algname: str = "md5", 
    salt: bytes = b"", 
    buffsize: int = DEFAULT_BUFFER_SIZE, 
) -> str:
    """Calculate the hash value of the file.

    :param path: The file path.
    :param algname: The hash algorithm name, default to "md5".
        All available algorithms can be found at:
            `hashlib.algorithms_available`.
    :param salt: Salt, if the file data is `content`, 
        then we will finally calculate:
            `hashlib.new(algname, salt+content)`.
    :param buffsize: When we read the file iterately, it is the size 
        of each read data block, the unit is Byte, if it is <= 0, 
        the file will be read at once (large memory consumption).

    :return: The digest value calculated by hash algorithm.
    """
    hashobj = hash_new(algname, salt)
    file = open(path, "rb", buffering=0)
    if buffsize <= 0 or getsize(path) <= buffsize:
        hashobj.update(file.read())
    else:
        readinto = file.readinto
        update = hashobj.update
        buf = bytearray(buffsize)
        while (n := readinto(buf)):
            if n < buffsize:
                update(buf[:n])
                break
            update(buf)
    return hashobj.hexdigest()


def mfilehash(
    path: bytes | str | PathLike, 
    algnames_may_with_salt: tuple[str | tuple[str, bytes], ...] = ("md5",), 
    buffsize: int = DEFAULT_BUFFER_SIZE, 
) -> list[tuple[str, str]]:
    """Calculate multiple hash values of the file.

    :param path: The file path.
    :param algnames_may_with_salt: A tuple of hash algorithms. 
        Every item can be a separate algorithm name, 
        or a 2-tuple of algorithm name and salt.
        Then it will calculate the hash value of `salt`+`content`
            for each hash algorithm.
        All available algorithms can be found at:
            `hashlib.algorithms_available`.
    :param buffsize: When we read the file iterately, it is the size 
        of each read data block, the unit is Byte, if it is <= 0, 
        the file will be read at once (large memory consumption).

    :return: A tuple of digest values calculated by multiple hash algorithms.
    """
    hashobjs = [
        hash_new(args) if isinstance(args, str) else hash_new(*args)
        for args in algnames_may_with_salt 
    ]
    hashalgs = [
        args if isinstance(args, str) else args[0]
        for args in algnames_may_with_salt 
    ]
    file = open(path, "rb", buffering=0)
    if buffsize <= 0 or getsize(path) <= buffsize:
        for hashobj in hashobjs:
            hashobj.update(file.read())
    else:
        readinto = file.readinto
        updates = [h.update for h in hashobjs]
        buf = bytearray(buffsize)
        while (n := readinto(buf)):
            if n < buffsize:
                buf = buf[:n]
                for update in updates:
                    update(buf)
                break
            for update in updates:
                update(buf)
    return list(zip(hashalgs, (h.hexdigest() for h in hashobjs)))


if __name__ == "__main__":
    from argparse import ArgumentParser, RawTextHelpFormatter
    from hashlib import algorithms_available
    from itertools import chain
    from os.path import isdir
    from sys import stdin

    from iterpath import path_walk # type: ignore

    parser = ArgumentParser(description="计算文件 hash", formatter_class=RawTextHelpFormatter)
    parser.add_argument(
        "paths", metavar="path", nargs="*", 
        help="路径列表，如有多个请用空格隔开")
    parser.add_argument(
        "-v", "--verbose", "--show-filenames", dest="show_filenames", action="store_true", 
        help="输出文件名")
    parser.add_argument(
        "-vv", "--super_verbose", "--show-algnames", dest="show_algnames", action="store_true", 
        help="输出文件名和算法名")
    parser.add_argument(
        "-a", "--algnames", nargs="+", default=["md5"], 
        help=f"指定所用的 hash 算法，默认为 md5，目前可选：\n{algorithms_available}")

    args = parser.parse_args()
    if not args.paths and stdin.isatty():
        parser.parse_args(["-h"])

    paths = args.paths
    show_filenames = args.show_filenames
    show_algnames = args.show_algnames
    algnames = args.algnames
    algorithms_unavailable = set(algnames) - algorithms_available

    if algorithms_unavailable:
        raise SystemExit(f"⚠️ 这些 hash 算法不可用：{algorithms_unavailable}")

    paths = args.paths
    if not stdin.isatty():
        paths = chain((p for p in (p.removesuffix("\n") for p in stdin) if p), paths)
    paths = chain.from_iterable(path_walk(p, only_files=True) if isdir(p) else (p,) for p in paths)

    if len(algnames) == 1:
        algname = algnames[0]
        for p in paths:
            try:
                if show_filenames or show_algnames:
                    print(f"# {p!r}")
                if show_algnames:
                    print(f"{algname}: {filehash(p, algname)}")
                else:
                    print(filehash(p, algname))
            except OSError as exc:
                print(f"# 😢 SKIPPED: {p}\n#    |_ {exc!r}")
    else:
        for p in paths:
            try:
                if show_filenames or show_algnames:
                    print(f"# {p!r}")
                if show_algnames:
                    for algname, hash_s in mfilehash(p, algnames):
                        print(f"{algname}: {hash_s}")
                else:
                    for _, hash_s in mfilehash(p, algnames):
                        print(hash_s)
            except OSError as exc:
                print(f"# 😢 SKIPPED: {p}\n#    |_ {exc!r}")

