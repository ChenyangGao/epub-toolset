#!/usr/bin/env python3
# coding: utf-8

# TODO: 允许过滤掉某些文件夹或文件名
# TODO: 如果文件名里面有空格呢

__author__ = "ChenyangGao <https://chenyanggao.github.io/>"
__version__ = (0, 0, 2)

import sys

if sys.version_info < (3, 10):
    raise SystemExit("⚠️ Python 版本不得低于 3.10，你的版本是\n%s" % sys.version)

from argparse import ArgumentParser, RawTextHelpFormatter
from sys import stdin

parser = ArgumentParser(description="""\
文件去重程序
    |_ by ChenyangGao <https://chenyanggao.github.io/>
""", epilog="""🤔 说明：

支持管道，即支持读取另一个程序的输出作为输入，例如可以使用 find 命令，搜索出当前工作目录下所有文件名不以 . 开头的文件

    find . \( ! -name '.*' \) -type f | python file_dedup

更具体的，执行如下命令

    find . \( ! -name '.*' \) -type f | %(executable)r %(script)r
""" % dict(executable=sys.executable, script=sys.argv[0]), formatter_class=RawTextHelpFormatter)
parser.add_argument("paths", metavar="path", nargs="*", help="路径列表，如有多个请用空格隔开")

args = parser.parse_args()
if not args.paths and stdin.isatty():
    parser.parse_args(["-h"])

from itertools import chain
from main import main

paths = args.paths
if not stdin.isatty():
    paths = chain((p for p in (p.removesuffix("\n") for p in stdin) if p), paths)
main(paths)

