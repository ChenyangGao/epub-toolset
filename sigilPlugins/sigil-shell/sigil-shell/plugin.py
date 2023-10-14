#!/usr/bin/env python3
# coding: utf-8

__author__  = "ChenyangGao <https://chenyanggao.github.io/>"
__all__ = ["run"]

from os import chdir, environ, path as os_path
from types import MappingProxyType


def run(bc):
    """
    """
    config = bc.getPrefs()
    shell = config.get("shell", "python")

    laucher_file, ebook_root, outdir, _, target_file = __import__("sys").argv
    this_plugin_dir = os_path.dirname(target_file)
    sigil_package_dir = os_path.dirname(laucher_file)

    paths = dict(
        laucher_file      = laucher_file, 
        sigil_package_dir = sigil_package_dir, 
        this_plugin_dir   = this_plugin_dir, 
        plugins_dir       = os_path.dirname(this_plugin_dir), 
        ebook_root        = ebook_root, 
        outdir            = outdir, 
    )

    env = {}
    env["PLUGIN_SHELL"]        = shell
    env["PLUGIN_OUTDIR"]       = outdir
    env["PLUGIN_DUMP_FILE"]    = os_path.join(outdir, "sigil_console.dump.pkl")
    env["PLUGIN_ABORT_FILE"]   = abort_file   = os_path.join(outdir, "sigil_console.abort")
    env["PLUGIN_STARTUP_FILE"] = startup_file = os_path.join(outdir, "sigil_console_startup.py")
    env["PLUGIN_MAIN_FILE"]    = os_path.join(this_plugin_dir, "plugin_main.py")
    env["PYTHONSTARTUP"]       = startup_file
    environ.update(env)

    __import__("builtins").PLUGIN_SETTING = MappingProxyType({
        "path": MappingProxyType(paths), 
        "env": MappingProxyType(env), 
    })

    chdir(outdir)

    open(startup_file, "w", encoding="utf-8").write(f"""\
#!/usr/bin/env python3
# coding: utf-8

import builtins

__import__("warnings").filterwarnings("ignore", category=DeprecationWarning)

if not hasattr(builtins, "PLUGIN_SETTING"):
    # Changing working directory
    __import__("os").chdir({outdir!r})

    # Setting os.environ
    __import__("os").environ.update({env!r})

    # Injecting module paths
    if {sigil_package_dir!r} not in __import__("sys").path:
        __import__("sys").path[:0] = [{sigil_package_dir!r}, {this_plugin_dir!r}]

    # Introducing global variables
    import plugin_help as plugin
    plugin.load_wrapper()
    plugin.function.BOOK_CONTAINER = bc = bk = __import__("bookcontainer").BookContainer(plugin.function.WRAPPER)
    shell = plugin.shell

    # Injecting builtins variable: PLUGIN_SETTING
    from types import MappingProxyType
    PLUGIN_SETTING = builtins.PLUGIN_SETTING = MappingProxyType({{
        "path": MappingProxyType({paths!r}), 
        "env": MappingProxyType({env!r}), 
    }})
    del MappingProxyType

    # Callback at exit
    __import__("atexit").register(plugin.dump_wrapper)

del builtins
""")

    import plugin_help as plugin

    plugin.function.BOOK_CONTAINER = bc
    plugin.function.WRAPPER = bc._w
    plugin.start_shell(shell)

    # check whether the console was aborted.
    if os_path.exists(abort_file):
        return 1

    return 0

