#!/usr/bin/env python3
# coding: utf-8

__author__  = "ChenyangGao <https://chenyanggao.github.io/>"
__version__ = (0, 0, 1)
__all__ = [
    "SHELLS", "default_shell", "start_shell", "start_python", "start_ipython", "start_bpython", 
    "start_ptpython", "start_ptipython", "start_jupyter_console", "start_xonsh", 
]

from os import environ, isatty
from sys import executable

from plugin_util.pip_tool import ensure_install
from plugin_util.function_register import bind_function_registry
from plugin_util.run import prun, prun_module

from .function import context_wrapper


SHELL_MAP = {}
register_shell, _ = bind_function_registry(SHELL_MAP)


def default_shell(name=""):
    "Get or set the default shell when opening this plugin"
    from .function import BOOK_CONTAINER
    if not name:
        return BOOK_CONTAINER.getPrefs().get("shell", "python")
    if name not in SHELL_MAP:
        raise ValueError(f"no such shell: {name!r}, only accept: {SHELLS!r}")
    config = BOOK_CONTAINER.getPrefs()
    environ["PLUGIN_SHELL"] = name
    config["shell"] = name
    BOOK_CONTAINER.savePrefs(config)


def start_shell(name):
    """Start a shell with a specified name.

    **NOTE**: All shells can be found in `SHELL_MAP`.
    """
    if name not in SHELL_MAP:
        raise ValueError(f"no such shell: {name!r}, only accept: {SHELLS!r}")

    if not isatty(1):
        from plugin_util.terminal import start_terminal

        args = [executable, environ["PLUGIN_MAIN_FILE"], "--startup", environ["PLUGIN_STARTUP_FILE"], "--shell", name]
        with context_wrapper():
            start_terminal(args, wait=True)
        return

    SHELL_MAP[name]()


@register_shell("python")
def start_python():
    """Start an python process, and wait until it is terminated.
    Reference:
        - https://www.python.org
        - https://docs.python.org/3/
    """
    with context_wrapper():
        prun(executable)


@register_shell("ipython")
def start_ipython():
    """Start an ipython process, and wait until it is terminated.
    Reference:
        - https://ipython.org
        - https://ipython.org/documentation.html
        - https://pypi.org/project/ipython/
        - https://github.com/ipython/ipython
    """
    ensure_install("IPython")
    with context_wrapper():
        prun_module("IPython")


@register_shell("bpython")
def start_bpython():
    """Start an bpython process, and wait until it is terminated.
    Reference:
        - https://pypi.org/project/bpython/
        - https://bpython-interpreter.org
        - https://docs.bpython-interpreter.org/en/latest/
    """
    ensure_install("bpython")
    with context_wrapper():
        prun_module("bpython")


@register_shell("ptpython")
def start_ptpython():
    """Start an ptpython process, and wait until it is terminated.
    Reference:
        - https://pypi.org/project/ptpython/
        - https://github.com/prompt-toolkit/ptpython
        - https://pypi.org/project/prompt-toolkit/
        - https://www.asmeurer.com/mypython/
    """
    ensure_install("ptpython")
    with context_wrapper():
        prun_module("ptpython")


@register_shell("ptipython")
def start_ptipython():
    """Start an ptipython process, and wait until it is terminated.
    Reference:
        - https://github.com/prompt-toolkit/ptpython#ipython-support
    """
    ensure_install("IPython")
    ensure_install("ptpython")
    with context_wrapper():
        prun_module("ptpython.entry_points.run_ptipython")


@register_shell("jupyter_console")
def start_jupyter_console():
    """Start a jupyter console process, and wait until it is terminated.
    Reference:
        - https://jupyter-console.readthedocs.io/en/latest/
    """
    ensure_install("jupyter_console")
    with context_wrapper():
        prun_module("jupyter_console")


@register_shell("xonsh")
def start_xonsh():
    """Start a xonsh process, and wait until it is terminated.
    Reference:
        - https://github.com/xonsh/xonsh
        - https://xon.sh/contents.html
    """
    ensure_install("xonsh")
    with context_wrapper():
        prun_module("xonsh", ("--rc", environ["PYTHONSTARTUP"]))


SHELLS = tuple(SHELL_MAP)


class ShellStarter:

    def __init__(self, func, /):
        self.__func__ = func

    def __call__(self, /):
        self.__func__()

    def __repr__(self, /):
        self.__func__()
        return ""


globals().update(
    (k, ShellStarter(fn))
    for k, fn in SHELL_MAP.items()
)

