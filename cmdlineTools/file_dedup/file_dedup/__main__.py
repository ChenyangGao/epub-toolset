#!/usr/bin/env python3
# coding: utf-8

# TODO: 允许过滤掉某些文件夹或文件名
# TODO: 如果文件名里面有空格呢

__author__ = "ChenyangGao <https://chenyanggao.github.io/>"
__version__ = (0, 0, 2)

import sys

if sys.version_info < (3, 10):
    raise SystemExit("⚠️ Python 版本不得低于 3.10，你的版本是\n%s" % sys.version)

from main import main

main(sys.argv)

