#!/usr/bin/env python
# coding: utf-8

__author__  = "ChenyangGao <https://chenyanggao.github.io/>"
__version__ = (0, 1)
__all__ = [
    "openpath", "split", "relative_path", "to_ntpath",  "to_posixpath", 
    "ntpath_to_syspath", "posixpath_to_syspath", 
    "path_has_hidden_part", 
]

import ntpath
import posixpath

from os import fspath, path as syspath, PathLike, fsdecode
from types import ModuleType
from typing import AnyStr, List, Optional, Union


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


def split(
    path: Union[AnyStr, PathLike[AnyStr]], 
    sep: Optional[AnyStr] = None, 
    maxsplit: int = -1, 
    start: int = 0, 
) -> list[AnyStr]:
    s = fspath(path)
    if start == 0:
        return s.split(sep, maxsplit)
    prefix, remain = s[:start], s[start:]
    parts = remain.split(sep, maxsplit)
    parts[0] = prefix + parts[0]
    return parts


def relative_path(
    ref_path: Union[AnyStr, PathLike[AnyStr]], 
    rel_path: Union[None, AnyStr, PathLike[AnyStr]] = None, 
    lib: ModuleType = syspath, 
) -> AnyStr:
    'Relative to the directory of `rel_path`, return the path of `file_path`.'
    ref_path_s: AnyStr = fspath(ref_path)
    rel_path_s: AnyStr

    curdir: AnyStr
    pardir: AnyStr
    sep: AnyStr
    if isinstance(ref_path_s, str):
        if rel_path is None:
            rel_path_s = "."
        else:
            rel_path_s = fspath(rel_path)
        curdir, pardir, sep = lib.curdir, lib.pardir, lib.sep
    else:
        if rel_path is None:
            rel_path_s = b"."
        else:
            rel_path_s = fspath(rel_path)
        curdir, pardir, sep = lib.curdir.encode(), lib.pardir.encode(), lib.sep.encode()

    if not ref_path_s:
        return rel_path_s

    dir_path = lib.dirname(rel_path_s)
    if not dir_path or dir_path == curdir or lib.isabs(ref_path_s):
        return ref_path_s

    drive, dir_path = lib.splitdrive(dir_path)
    dir_path_isabs = bool(drive or dir_path.startswith(sep))
    dir_parts = split(dir_path, sep, start=1)
    ref_parts = ref_path_s.split(sep)
    try:
        for i, p in enumerate(ref_parts):
            if p == curdir:
                continue
            elif p == pardir and dir_parts[-1] != pardir:
                if dir_parts.pop() == sep:
                    raise IndexError
            else:
                dir_parts.append(p)
        result_path = lib.join(drive, *dir_parts)
        if dir_path_isabs and not result_path.startswith(sep):
            return sep + result_path
        return result_path
    except IndexError:
        if dir_path_isabs:
            raise ValueError(
                f'{ref_path_s!r} relative to {rel_path_s!r} exceeded the root directory')
        return lib.join(*ref_parts[i:])


def to_ntpath(path: Union[AnyStr, PathLike[AnyStr]]) -> AnyStr:
    s: AnyStr = fspath(path)
    if isinstance(s, str):
        return s.replace(_sep, "\\")
    else:
        return s.replace(_sepb, b"\\")


def to_posixpath(path: Union[AnyStr, PathLike[AnyStr]]) -> AnyStr:
    s: AnyStr = fspath(path)
    if isinstance(s, str):
        return s.replace(_sep, "/")
    else:
        return s.replace(_sepb, b"/")


def to_syspath(
    path: Union[AnyStr, PathLike[AnyStr]], 
    lib: ModuleType, 
) -> AnyStr:
    s: AnyStr = fspath(path)
    if isinstance(s, str):
        return s.replace(lib.sep, _sep)
    else:
        return s.replace(lib.sep.encode(), _sepb)


def ntpath_to_syspath(path: Union[AnyStr, PathLike[AnyStr]]) -> AnyStr:
    s: AnyStr = fspath(path)
    if isinstance(s, str):
        return s.replace("\\", _sep)
    else:
        return s.replace(b"\\", _sepb)


def posixpath_to_syspath(path: Union[AnyStr, PathLike[AnyStr]]) -> AnyStr:
    s: AnyStr = fspath(path)
    if isinstance(s, str):
        return s.replace("/", _sep)
    else:
        return s.replace(b"/", _sepb)


def path_has_hidden_part(
    path: Union[AnyStr, PathLike[AnyStr]], 
    lib: ModuleType = syspath, 
):
    s: AnyStr = fspath(path)
    sep: AnyStr
    if isinstance(s, str):
        sep = lib.sep
        return any(
            part != ("", ".", "..") and part.startswith(".")
            for part in fspath(path).split(sep)
        )
    else:
        sep = lib.sep.encode()
        return any(
            part != (b"", b".", b"..") and part.startswith(b".")
            for part in fspath(path).split(sep)
        )

