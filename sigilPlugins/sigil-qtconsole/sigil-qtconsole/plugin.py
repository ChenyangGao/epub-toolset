#!/usr/bin/env python3
# coding: utf-8

__author__  = "ChenyangGao <https://chenyanggao.github.io/>"

from os import path as os_path
from pickle import dump, load
from subprocess import run as sprun
from sys import argv, executable
from tempfile import NamedTemporaryFile

def run(bc):
    laucher_file, ebook_root, outdir, _, target_file = __import__("sys").argv
    sigil_package_dir = os_path.dirname(laucher_file)
    this_plugin_dir = os_path.dirname(target_file)

    dump_path = os_path.join(outdir, ".sigil.dump")
    dump(bc._w, open(dump_path, "wb"))

    startup_code = f"""\
#!/usr/bin/env python3
# coding: utf-8
__import__("os").chdir({outdir!r})
__import__("sys").path[:0] = [{sigil_package_dir!r}, {this_plugin_dir!r}]
bc = bk = __import__("bookcontainer").BookContainer(
    __import__("pickle").load(open({dump_path!r}, "rb"))
)
__import__("atexit").register(
    lambda _w=bc._w: __import__("pickle").dump(_w, open({dump_path!r}, "wb"))
)
"""

    with NamedTemporaryFile(suffix=".py", mode="w", encoding="utf-8") as f:
        f.write(startup_code)
        f.flush()
        sprun(
            [executable, "-m", "qtconsole"], 
            env={"PYTHONSTARTUP": f.name}, 
            check=True, 
            shell=__import__("platform") == "Windows", 
        )

    bc._w = load(open(dump_path, "rb"))

    return 0

