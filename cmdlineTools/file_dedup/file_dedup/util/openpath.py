#!/usr/bin/env python3
# coding: utf-8

__author__ = "ChenyangGao <https://chenyanggao.github.io/>"
__version__ = (0, 0, 1)
__all__ = ["openpath"]

from os import fsdecode, PathLike


try:
    _startfile = __import__("os").startfile

    def openpath(path: bytes | str | PathLike) -> None:
        "Open a file or directory (For Windows)"
        _startfile(path)
except AttributeError:
    from subprocess import Popen as _Popen

    _PLATFROM_SYSTEM: str = __import__("platform").system()

    if _PLATFROM_SYSTEM == "Linux":
        def openpath(path: bytes | str | PathLike) -> None:
            "Open a file or directory (For Linux)"
            _Popen(["xdg-open", fsdecode(path)])
    elif _PLATFROM_SYSTEM == "Darwin":
        def openpath(path: bytes | str | PathLike) -> None:
            "Open a file or directory (For Mac OS X)"
            _Popen(["open", fsdecode(path)])
    else:
        def openpath(path: bytes | str | PathLike) -> None:
            "Issue an error: can not open the path."
            raise NotImplementedError("Can't open the path %r" % path)

