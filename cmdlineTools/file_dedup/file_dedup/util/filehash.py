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
) -> tuple[str, ...]:
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
    return tuple(h.hexdigest() for h in hashobjs)

