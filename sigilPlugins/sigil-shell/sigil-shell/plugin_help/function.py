#!/usr/bin/env python3
# coding: utf-8

__author__  = "ChenyangGao <https://chenyanggao.github.io/>"
__version__ = (0, 0, 1)
__all__ = ["abort", "exit", "dump_wrapper", "load_wrapper", "context_wrapper"]

from contextlib import contextmanager
from os import _exit, environ
from pickle import load as pickle_load, dump as pickle_dump


_SYSTEM_IS_WINDOWS = __import__("platform").system() == "Windows"


def abort():
    "Abort console to discard all changes."
    open(environ["PLUGIN_ABORT_FILE"], "wb").close()
    _exit(1)


def exit():
    "Exit console for no more operations."
    dump_wrapper()
    _exit(0)


def dump_wrapper():
    "Dump wrapper to file."
    pickle_dump(WRAPPER, open(environ["PLUGIN_DUMP_FILE"], "wb"))


def load_wrapper():
    "Load wrapper from file."
    global WRAPPER
    wrapper = pickle_load(open(environ["PLUGIN_DUMP_FILE"], "rb"))
    try:
        WRAPPER.__dict__ = wrapper.__dict__
    except NameError:
        WRAPPER = wrapper


@contextmanager
def context_wrapper():
    dump_wrapper()
    yield
    load_wrapper()

