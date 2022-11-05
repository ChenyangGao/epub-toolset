#!/usr/bin/env python
# coding: utf-8

"""This module provides utilities for working with paths.

Other important functions:
    - os.fspath
    - os.fsencode
    - os.fsdecode
    - urllib.parse.quote
    - urllib.parse.unquote
"""

__author__  = "ChenyangGao <https://chenyanggao.github.io/>"
__version__ = (0, 4)
__all__ = [
    "openpath", "starting_dir", "longest_common_dir", "split", "separate", 
    "clean_parts", "normalize_ntpath", "normalize_posixpath", "normalize_path", 
    "relative_path", "reference_path", "path_posix_to_nt", "path_nt_to_posix", 
    "path_to_nt", "path_to_posix", "path_nt_to_sys", "path_posix_to_sys", 
    "path_nt_to_url", "path_url_to_nt", 
]

import os.path as syspath
import ntpath
import posixpath

from nturl2path import pathname2url as path_nt_to_url, url2pathname as path_url_to_nt
from os import fspath, PathLike
from re import compile as re_compile, Pattern
from typing import cast, AnyStr, Final, Optional, Union


cre_nt_seps: Final[Pattern[str]] = re_compile(r"[\\/]")
creb_nt_seps: Final[Pattern[bytes]] = re_compile(br"[\\/]")
cre_nt_name_na_chars: Final[Pattern[str]] = re_compile(r'\\:*?"<>|')
creb_nt_name_na_chars: Final[Pattern[bytes]] = re_compile(br'\\:*?"<>|')
cre_nt_name_na_chars_all: Final[Pattern[str]] = re_compile(r'/\\:*?"<>|')
creb_nt_name_na_chars_all: Final[Pattern[bytes]] = re_compile(br'/\\:*?"<>|')
cre_nt_drive: Final[Pattern[str]] = re_compile(r'^///(?P<drive>[^/\\:*?"<>|]+)[:|]')
creb_nt_drive: Final[Pattern[bytes]] = re_compile(br'^///(?P<drive>[^/\\:*?"<>|]+)[:|]')

ntsep: Final[str] = "\\"
ntsepb: Final[bytes] = b"\\"
posixsep: Final[str] = "/"
posixsepb: Final[bytes] = b"/"
syssep: Final[str]
syssepb: Final[bytes]
if syspath is ntpath:
    syssep, syssepb = ntsep, ntsepb
else:
    syssep, syssepb = posixsep, posixsepb


try:
    _startfile = __import__("os").startfile

    def openpath(path: str | PathLike) -> None:
        "Open a file or directory (For Windows)"
        _startfile(path)
except AttributeError:
    from subprocess import Popen as _Popen

    _PLATFROM_SYSTEM: str = __import__("platform").system()

    if _PLATFROM_SYSTEM == "Linux":
        def openpath(path: str | PathLike) -> None:
            "Open a file or directory (For Linux)"
            _Popen(["xdg-open", fspath(path)])
    elif _PLATFROM_SYSTEM == "Darwin":
        def openpath(path: str | PathLike) -> None:
            "Open a file or directory (For Mac OS X)"
            _Popen(["open", fspath(path)])
    else:
        def openpath(path: str | PathLike) -> None:
            "Issue an error: can not open the path."
            raise NotImplementedError("Can't open the path %r" % fspath(path))


def starting_dir(
    path: AnyStr | PathLike[AnyStr], 
    sep: Optional[AnyStr] = None, 
) -> AnyStr:
    """Return the starting directory of `path`.
    Definition:
        The *starting directory* is the longest ancestor directory of a path.

    :param path: The path.
    :param sep:  The path separator.

    :return: If it ends with `sep`, return itself; otherwise, 
        return its parent directory.
    """
    path_: AnyStr = fspath(path)

    realsep: AnyStr
    if sep is None:
        if isinstance(path_, str):
            realsep = syssep
        else:
            realsep = syssepb
    else:
        realsep = sep

    if path_.endswith(realsep):
        return path_
    try:
        return path_[:path_.rindex(realsep)+1]
    except ValueError:
        if isinstance(path_, str):
            return ""
        else:
            return b""


def longest_common_dir(
    path: AnyStr | PathLike[AnyStr], 
    *paths: AnyStr | PathLike[AnyStr], 
    sep: Optional[AnyStr] = None, 
) -> AnyStr:
    """Return the longest common directory.
    Definition:
        The *longest common directory* is the longest common ancestor 
            directory of many paths.
    😄 Tips: You can use
        - `os.path.commonpath`, `os.path.commonprefix`
        - `ntpath.commonpath`, `ntpath.commonprefix`
        - `posixpath.commonpath`, `posixpath.commonprefix`
    instead.
 
    :param path:  The path.
    :param paths: The other paths.
    :param sep:   The path separator.

    :return: If no `paths`, that is, there is only one `path`, 
        return `starting_dir(path, sep)`. Else, return the  
        longest common ancestor directory in these paths.
    """
    if not paths:
        return starting_dir(path, realsep)

    paths_: tuple[AnyStr, ...] = (fspath(path), *(fspath(p) for p in paths))
    p1, p2 = min(paths_), max(paths_)

    realsep: AnyStr
    if sep is None:
        if isinstance(p1, str):
            realsep = syssep
        else:
            realsep = syssepb
    else:
        realsep = sep

    lastest_index = 0
    for i, (c1, c2) in enumerate(zip(p1, p2), 1):
        if c1 != c2:
            break
        elif c1 == realsep:
            lastest_index = i

    return p1[:lastest_index]


def separate(
    path: AnyStr | PathLike[AnyStr], 
    sep: None | AnyStr | Pattern[AnyStr] = None, 
    maxsplit: int = -1, 
    from_left: bool = False, 
) -> list[AnyStr]:
    ""
    path_ = fspath(path)

    if isinstance(sep, Pattern):
        if maxsplit == 0:
            return [path_]
        else:
            ls_pos = [m.end() for m in sep.finditer(path_)]
            if maxsplit > 0:
                if from_left:
                    ls_pos = ls_pos[:maxsplit]
                else:
                    ls_pos = ls_pos[-maxsplit:]
            parts = []
            start = 0
            for stop in ls_pos:
                parts.append(path_[start:stop])
                start = stop
            parts.append(path_[start:])
            return parts
    else:
        realsep: AnyStr
        if sep is None:
            if isinstance(path_, str):
                realsep = syssep
            else:
                realsep = syssepb
        else:
            realsep = sep

        if from_left:
            parts = path_.split(realsep, maxsplit)
        else:
            parts = path_.rsplit(realsep, maxsplit)

        if len(parts) > 1:
            for i, p in enumerate(parts[:-1]):
                parts[i] += realsep

        return parts


def split(
    path: AnyStr | PathLike[AnyStr], 
    sep: None | AnyStr | Pattern[AnyStr] = None, 
    maxsplit: int = -1, 
    from_left: bool = False, 
) -> list[AnyStr]:
    """Split `path` into a list of parts, using `sep` as the delimiter string.

    :param path: A path to be splitted.
    :param sep:  The delimiter according which to split the `path`.
    :param maxsplit: Maximum number of splits to do.
        -1 (the default value) means no limit.
    :param from_left: If False (the default), divide from right to left, 
        otherwise from left to right.

    :return: A list of the path parts.
    """
    path_ = fspath(path)

    if isinstance(sep, Pattern):
        if maxsplit < 0:
            return sep.split(path_)
        elif maxsplit == 0:
            return [path_]
        elif from_left:
            return sep.split(path_, maxsplit)
        else:
            ls_span = [m.span() for m in sep.finditer(path_)]
            parts = []
            start = 0
            for l, r in ls_span[-maxsplit:]:
                parts.append(path_[start:l])
                start = r
            parts.append(path_[start:])
            return parts
    else:
        realsep: AnyStr
        if sep is None:
            if isinstance(path_, str):
                realsep = syssep
            else:
                realsep = syssepb
        else:
            realsep = sep

        if from_left:
            return path_.split(realsep, maxsplit)
        else:
            return path_.rsplit(realsep, maxsplit)


def clean_parts(parts: list[AnyStr]) -> list[AnyStr]:
    """Cleaning parts (get from `split`) in place: 
        by removing '' and '.', and reducing '..'.
    😄 Tips: You can use
        - os.path.normpath
        - ntpath.normpath
        - posixpath.normpath
    instead.

    :param parts: The list of path parts.

    :return: The cleaned list of path parts.
    """
    # It's an empty path.
    if not parts or len(parts) == 1 and not parts[0]:
        return parts

    empty: AnyStr
    curdir: AnyStr
    pardir: AnyStr
    if isinstance(parts[0], str):
        empty, curdir, pardir = "", ".", ".."
    else:
        empty, curdir, pardir = b"", b".", b".."

    # It's a path like .., ../.., ../../.., and so on.
    if all(p == pardir for p in parts):
        parts.append(empty)
        return parts
    # Determine if it is an absolute path.
    withroot: bool = parts[0] == empty
    idx: int = withroot
    # Clean parts: by removing '' and '.', and reducing '..'.
    for p in parts[idx:]:
        if p in (empty, curdir):
            continue
        elif p == pardir:
            if idx == 1:
                if withroot:
                    raise ValueError("Exceeded the root directory!")
            if idx == 0 or parts[idx-1] == pardir:
                parts[idx] = p
                idx += 1
            else:
                idx -= 1
        else:
            parts[idx] = p
            idx += 1
    if p in (empty, curdir, pardir):
        parts[idx] = empty
        idx += 1
    # Clean up the surplus at the tail.
    del parts[idx:]

    return parts


def normalize_ntpath(path: AnyStr | PathLike[AnyStr]) -> AnyStr:
    ""
    path_: AnyStr = fspath(path)
    drive: AnyStr
    drive, path_ = ntpath.splitdrive(path_)
    if isinstance(path_, str):
        return drive + ntsep.join(clean_parts(split(path_, cre_nt_seps)))
    else:
        return drive + ntsepb.join(clean_parts(split(path_, creb_nt_seps)))


def normalize_posixpath(path: AnyStr | PathLike[AnyStr]) -> AnyStr:
    ""
    path_: AnyStr = fspath(path)
    if isinstance(path_, str):
        return posixsep.join(clean_parts(split(path_, posixsep)))
    else:
        return posixsepb.join(clean_parts(split(path_, posixsepb)))


def normalize_path(path: AnyStr | PathLike[AnyStr]) -> AnyStr:
    ""
    if syspath is ntpath:
        return normalize_ntpath(path)
    elif syspath is posixpath:
        return normalize_posixpath(path)
    else:
        raise NotImplementedError


def relative_path(
    path: AnyStr | PathLike[AnyStr], 
    pathto: AnyStr | PathLike[AnyStr], 
    sep: Optional[AnyStr] = None, 
) -> AnyStr:
    """Return the relative path from `path` to `pathto`.
    Definition:
        The *relative path from path1 to path2* is that, under the same 
        working directory, the relative path from path1 to path2.
    😄 Tips: You can use 
        - `os.path.relpath`
        - `ntpath.relpath`
        - `posixpath.relpath` 
    instead.

    :param path:   The start path. 
    :param pathto: The end path.
    :param sep:    The path separator.

    :return: The relative path from `path` to `pathto`.
    """
    path1: AnyStr = fspath(path)
    path2: AnyStr = fspath(pathto)

    realsep: AnyStr
    if sep is None:
        if isinstance(path1, str):
            realsep = syssep
        else:
            realsep = syssepb
    else:
        realsep = sep

    if path1.startswith(realsep) ^ path2.startswith(realsep):
        raise ValueError("`path` and `pathto`, either all absolute paths "
                         "or all relative paths")
    if path1.rstrip(realsep) == path2.rstrip(realsep):
        if isinstance(path1, str):
            return ""
        else:
            return b""

    parts_org: list[AnyStr] = clean_parts(split(path1, realsep))
    parts_dst: list[AnyStr] = clean_parts(split(path2, realsep))

    i: int = 0
    for p1, p2 in zip(parts_org, parts_dst):
        if p1 != p2:
            break
        i += 1

    pardir: AnyStr
    if isinstance(path1, str):
        pardir = ".."
    else:
        pardir = b".."

    parts: tuple = (
        *((pardir,) * (len(parts_org)-i-1)), 
        *parts_dst[i:]
    )
    return realsep.join(parts)


def reference_path(
    path: AnyStr | PathLike[AnyStr], 
    pathto: AnyStr | PathLike[AnyStr], 
    sep: Optional[AnyStr] = None, 
) -> AnyStr:
    """Return the reference path from `path` to `pathto`.
    Definition:
        The *reference path from path1 to path2* is that
            1. If path2 is an absolute path, it is path2 itself;
            2. If path2 is a relative path, the starting directory of 
                path1 is used as the working directory of path2,
                2.1. If path1 is an absolute path, it is the absolute path of path2;
                2.2. If path1 is a relative path, it is the relative path of path2 
                    to the working directory of path1;
        .

    :param path:   The start path. 
    :param pathto: The end path.
    :param sep:    The path separator.

    :return: The reference path from `path` to `pathto`.
    """
    path1: AnyStr = fspath(path)
    path2: AnyStr = fspath(pathto)

    realsep: AnyStr
    if sep is None:
        if isinstance(path1, str):
            realsep = syssep
        else:
            realsep = syssepb
    else:
        realsep = sep

    parts = path1.split(realsep)
    parts[-1:] = path2.split(realsep)

    return realsep.join(clean_parts(parts))


def path_posix_to_nt(path: AnyStr | PathLike[AnyStr]) -> AnyStr:
    ""
    path_: AnyStr = fspath(path)
    drive: AnyStr
    if isinstance(path_, str):
        match_drive = cre_nt_drive.match(path_)
        if match_drive:
            drive = match_drive["drive"] + ":"
            path_ = path_[match_drive.end():]
        else:
            drive = ""
        if cre_nt_name_na_chars.search(path_):
            raise ValueError("Unable convert path to nt: %r" % path)
        return drive + path_.replace(posixsep, ntsep)
    else:
        match_drive = creb_nt_drive.match(path_)
        if match_drive:
            drive = match_drive["drive"] + b":"
            path_ = path_[match_drive.end():]
        else:
            drive = b""
        if creb_nt_name_na_chars.search(path_):
            raise ValueError("Unable convert path to nt: %r" % path)
        return drive + path_.replace(posixsepb, ntsepb)


def path_nt_to_posix(path: AnyStr | PathLike[AnyStr]) -> AnyStr:
    ""
    path_: AnyStr = fspath(path)
    drive: AnyStr
    drive, path_ = ntpath.splitdrive(path_)
    if isinstance(path_, str):
        prefix = "///" + drive if drive else ""
        return prefix + path_.replace(ntsep, posixsep)
    else:
        prefix = b"///" + drive if drive else b""
        return prefix + path_.replace(ntsepb, posixsepb)


def path_to_nt(path: AnyStr | PathLike[AnyStr]) -> AnyStr:
    ""
    if syspath is ntpath:
        return fspath(path)
    elif syspath is posixpath:
        return path_posix_to_nt(path)
    else:
        raise NotImplementedError


def path_to_posix(path: AnyStr | PathLike[AnyStr]) -> AnyStr:
    ""
    if syspath is posixpath:
        return fspath(path)
    elif syspath is ntpath:
        return path_nt_to_posix(path)
    else:
        raise NotImplementedError


def path_nt_to_sys(path: AnyStr | PathLike[AnyStr]) -> AnyStr:
    ""
    if syspath is ntpath:
        return fspath(path)
    elif syspath is posixpath:
        return path_nt_to_posix(path)
    else:
        raise NotImplementedError


def path_posix_to_sys(path: AnyStr | PathLike[AnyStr]) -> AnyStr:
    ""
    if syspath is posixpath:
        return fspath(path)
    elif syspath is ntpath:
        return path_posix_to_nt(path)
    else:
        raise NotImplementedError

