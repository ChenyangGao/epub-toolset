#!/usr/bin/env python3
# coding: utf-8

__author__ = "ChenyangGao <https://chenyanggao.github.io/>"
__version__ = (0, 0, 1)
__all__ = ["ctx_stdin_tty", "input2"]

import sys

from platform import system
from contextlib import contextmanager


@contextmanager
def ctx_stdin_tty():
    stdin = sys.stdin
    if system() == "Windows":
        # See:
        #     - https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file#naming-conventions
        #     - https://help.interfaceware.com/v6/windows-reserved-file-names
        stdin_new = open("CON")
    else:
        # See:
        #     - https://www.kernel.org/doc/html/latest/admin-guide/serial-console.html
        #     - https://www.kernel.org/doc/html/latest/driver-api/tty/
        #     - https://man7.org/linux/man-pages/man4/tty.4.html
        #     - https://docs.python.org/3/library/unix.html
        #     - https://www.baeldung.com/linux/monitor-keyboard-drivers
        stdin_new = open("/dev/tty")
    try:
        sys.stdin = stdin_new
        yield stdin_new
    finally:
        sys.stdin = stdin
        stdin_new.close()


def input2(prompt=None) -> str:
    try:
        return input(prompt)
    except EOFError:
        with ctx_stdin_tty():
            return input()

