#!/usr/bin/env python3
# coding: utf-8

# Reference: 
#   - https://github.com/Sigil-Ebook/Sigil/blob/master/src/Resource_Files/plugin_launchers/python/launcher.py
#   - https://github.com/Sigil-Ebook/Sigil/tree/master/docs

if __name__ != "__main__":
    raise RuntimeError("plugin_main.py can only run as a main file")

parser = __import__("argparse").ArgumentParser(description="Sigil Console: plugin_main.py")
parser.add_argument("--shell", default="python", help="shell will be started")
parser.add_argument("--startup", default="sigil_shell_startup.py", help="startup file will be executed")
args = parser.parse_args()

if __import__("platform").system() == "Linux":
    from plugin_util.terminal import _send_pid_to_server
    _send_pid_to_server()
    del _send_pid_to_server

exec(open(args.startup, encoding="utf-8").read())

__import__("plugin_help").start_shell(args.shell)
