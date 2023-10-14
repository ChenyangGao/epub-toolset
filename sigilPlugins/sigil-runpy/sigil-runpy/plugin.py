#!/usr/bin/env python3
# coding: utf-8

__author__  = "ChenyangGao <https://chenyanggao.github.io/>"

from json import load
from os import path as os_path
from runpy import run_path

def run(bc):
    prefs_path = os_path.join(bc._w.usrsupdir, "plugins_prefs", "sigil-runpy-config", "sigil-runpy-config.json")
    try:
        prefs = load(open(prefs_path, encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError("please run the plugin 'sigil-runpy-config' first") from exc
    for path in prefs["config"]["path"]:
        run_path(path, {"bc": bc, "bk": bc})
    return 0
