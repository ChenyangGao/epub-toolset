#!/usr/bin/env python3
# coding: utf-8

__author__  = "ChenyangGao <https://chenyanggao.github.io/>"

from os import path as os_path
from pickle import dump, load
from subprocess import run as sprun
from sys import argv, executable

def run(bc):
    laucher_file, ebook_root, outdir, _, target_file = __import__("sys").argv
    sigil_package_dir = os_path.dirname(laucher_file)
    this_plugin_dir = os_path.dirname(target_file)

    dump_path = os_path.join(outdir, ".sigil.dump")
    dump(bc._w, open(dump_path, "wb"))

    startup_code = f"""\
__import__("os").chdir({outdir!r})
__import__("sys").path[:0] = [{sigil_package_dir!r}, {this_plugin_dir!r}]
bc = bk = __import__("bookcontainer").BookContainer(
    __import__("pickle").load(open({dump_path!r}, "rb"))
)
__import__("atexit").register(
    lambda _w=bc._w: __import__("pickle").dump(_w, open({dump_path!r}, "wb"))
)
class Exit:
    @staticmethod
    @__import__("functools").wraps(exit)
    def __call__(*args, _exit=exit, _w=bc._w):
        __import__("pickle").dump(_w, open({dump_path!r}, "wb"))
        _exit()
    def __repr__(self):
        frame = __import__("sys")._getframe(2)
        if frame.f_locals is frame.f_globals and frame.f_globals.get("__name__") == "__main__":
            self()
            return ""
        else:
            return "Use exit or exit() to exit"
__import__("builtins").exit = Exit()
del Exit
"""

    sprun(
        [executable, "-m", "idlelib", "-t", "Sigil IDLE Console", "-c", startup_code], 
        check=True, 
        shell=__import__("platform") == "Windows", 
    )

    bc._w = load(open(dump_path, "rb"))

    return 0

