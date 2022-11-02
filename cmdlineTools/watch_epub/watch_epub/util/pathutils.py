#!/usr/bin/env python
# coding: utf-8

__author__  = "ChenyangGao <https://chenyanggao.github.io/>"
__version__ = (0, 2)
__all__ = [
    "openpath", "starting_dir", "longest_common_dir", "clean_parts", 
    "split", "split_all", "relative_path", "reference_path", 
    "to_ntpath",  "to_posixpath", "to_syspath", 
    "ntpath_to_syspath", "posixpath_to_syspath", 
]

import ntpath
import posixpath

from os import fspath, path as syspath, PathLike
from typing import AnyStr, Optional, Union

# TODO: 对于 Windows 的路径，还有驱动器（盘符），所以，下面对于路径的处理，还需要完善一下
#       借鉴 mingw，C:\转化为/c/

_sep: str = syspath.sep
_sepb: bytes = syspath.sep.encode()


try:
    _startfile = __import__("os").startfile

    def openpath(path: Union[str, PathLike]) -> None:
        "Open a file or directory (For Windows)"
        _startfile(path)
except AttributeError:
    from subprocess import Popen as _Popen

    _PLATFROM_SYSTEM: str = __import__("platform").system()

    if _PLATFROM_SYSTEM == "Linux":
        def openpath(path: Union[str, PathLike]) -> None:
            "Open a file or directory (For Linux)"
            _Popen(["xdg-open", fspath(path)])
    elif _PLATFROM_SYSTEM == "Darwin":
        def openpath(path: Union[str, PathLike]) -> None:
            "Open a file or directory (For Mac OS X)"
            _Popen(["open", fspath(path)])
    else:
        def openpath(path: Union[str, PathLike]) -> None:
            "Issue an error: can not open the path."
            raise NotImplementedError("Can't open the path %r" % fspath(path))


def starting_dir(
    path: Union[AnyStr, PathLike[AnyStr]], 
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
            realsep = _sep
        else:
            realsep = _sepb
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
    path: Union[AnyStr, PathLike[AnyStr]], 
    *paths: Union[AnyStr, PathLike[AnyStr]], 
    sep: Optional[AnyStr] = None, 
) -> AnyStr:
    """Return the longest common directory.
    Definition:
        The *longest common directory* is the longest common ancestor 
            directory of many paths.
 
    :param path:  The path.
    :param paths: The other paths.
    :param sep:   The path separator.

    :return: If no `paths`, that is, there is only one `path`, 
        return `starting_dir(path, sep)`. Else, return the  
        longest common ancestor directory in these paths.
    """
    if not paths:
        return starting_dir(path, realsep)

    paths = (fspath(path), *map(fspath, paths))
    p1, p2 = min(paths), max(paths)

    realsep: AnyStr
    if sep is None:
        if isinstance(p1, str):
            realsep = _sep
        else:
            realsep = _sepb
    else:
        realsep = sep

    lastest_index = 0
    for i, (c1, c2) in enumerate(zip(p1, p2), 1):
        if c1 != c2:
            break
        elif c1 == realsep:
            lastest_index = i

    return p1[:lastest_index]


def clean_parts(parts: list[AnyStr]) -> list[AnyStr]:
    """Cleaning parts (get from `split`) in place: 
        by removing '' and '.', and reducing '..'.

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


def split(
    path: Union[AnyStr, PathLike[AnyStr]], 
    sep: Optional[AnyStr] = None, 
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

    realsep: AnyStr
    if sep is None:
        if isinstance(path_, str):
            realsep = _sep
        else:
            realsep = _sepb
    else:
        realsep = sep

    if from_left:
        return path_.split(realsep, maxsplit)
    else:
        return path_.rsplit(realsep, maxsplit)


def split_all(
    path: Union[AnyStr, PathLike[AnyStr]], 
    sep: Optional[AnyStr] = None, 
) -> list[AnyStr]:
    """Split `path` into a list of parts, using `sep` as the delimiter string.

    :param path: A path to be splitted.
    :param sep:  The delimiter according which to split the `path`.

    :return: A list of the path parts (cleaned, using `clean_parts`).
    """
    path_: AnyStr = fspath(path)

    realsep: AnyStr
    if sep is None:
        if isinstance(path_, str):
            realsep = _sep
        else:
            realsep = _sepb
    else:
        realsep = sep

    return clean_parts(path_.split(realsep))


def relative_path(
    path: Union[AnyStr, PathLike[AnyStr]], 
    pathto: Union[AnyStr, PathLike[AnyStr]], 
    sep: Optional[AnyStr] = None, 
):
    """Return the relative path from `path` to `pathto`.

    Definition:
        The *relative path from path1 to path2* is that, under the same 
        working directory, the relative path from path1 to path2.

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
            realsep = _sep
        else:
            realsep = _sepb
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

    parts_org = split_all(path1, realsep)
    parts_dst = split_all(path2, realsep)

    i = 0
    for p1, p2 in zip(parts_org, parts_dst):
        if p1 != p2:
            break
        i += 1

    pardir: AnyStr
    if isinstance(path1, str):
        pardir = ".."
    else:
        pardir = b".."

    return realsep.join((
        *(pardir,)*(len(parts_org)-i-1),
        *parts_dst[i:],
    ))


def reference_path(
    path: Union[AnyStr, PathLike[AnyStr]], 
    pathto: Union[AnyStr, PathLike[AnyStr]], 
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
            realsep = _sep
        else:
            realsep = _sepb
    else:
        realsep = sep

    parts = path1.split(realsep)
    parts[-1:] = path2.split(realsep)

    return realsep.join(clean_parts(parts))


def to_ntpath(
    path: Union[AnyStr, PathLike[AnyStr]], 
    sep: Optional[AnyStr] = None, 
) -> AnyStr:
    "Replace the path separator `sep` with '\\' in `path`."
    path_: AnyStr = fspath(path)

    realsep: AnyStr
    if sep is None:
        if syspath is ntpath:
            return path_
        if isinstance(path_, str):
            realsep = _sep
        else:
            realsep = _sepb
    else:
        realsep = sep

    if isinstance(path_, str):
        return path_.replace(realsep, "\\")
    else:
        return path_.replace(realsep, b"\\")


def to_posixpath(
    path: Union[AnyStr, PathLike[AnyStr]], 
    sep: Optional[AnyStr] = None, 
) -> AnyStr:
    "Replace the path separator `sep` with '/' in `path`."
    path_: AnyStr = fspath(path)

    realsep: AnyStr
    if sep is None:
        if syspath is posixpath:
            return path_
        if isinstance(path_, str):
            realsep = _sep
        else:
            realsep = _sepb
    else:
        realsep = sep

    if isinstance(path_, str):
        return path_.replace(realsep, "/")
    else:
        return path_.replace(realsep, b"/")


def to_syspath(
    path: Union[AnyStr, PathLike[AnyStr]], 
    sep: AnyStr, 
) -> AnyStr:
    "Replace the path separator `sep` with `os.path.sep` in `path`."
    path_: AnyStr = fspath(path)
    if isinstance(path_, str):
        return path_.replace(sep, _sep)
    else:
        return path_.replace(sep, _sepb)


def ntpath_to_syspath(path: Union[AnyStr, PathLike[AnyStr]]) -> AnyStr:
    "Replace the path separator `\\` with `os.path.sep` in `path`."
    path_: AnyStr = fspath(path)
    if isinstance(path_, str):
        return path_.replace("\\", _sep)
    else:
        return path_.replace(b"\\", _sepb)


def posixpath_to_syspath(path: Union[AnyStr, PathLike[AnyStr]]) -> AnyStr:
    "Replace the path separator `/` with `os.path.sep` in `path`."
    path_: AnyStr = fspath(path)
    if isinstance(path_, str):
        return path_.replace("/", _sep)
    else:
        return path_.replace(b"/", _sepb)

