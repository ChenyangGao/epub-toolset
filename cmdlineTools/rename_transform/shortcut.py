#! /usr/bin/env python3
# coding: utf-8

from argparse import ArgumentParser, RawTextHelpFormatter

ap = ArgumentParser(
    description='对 ePub 内在 OPF 文件所在文件夹或子文件夹下的文件修改文件名',
    formatter_class=RawTextHelpFormatter,
)
ap.add_argument('-c', '--confuse', action='store_true', 
                help='如果不指定这个参数，那么对文件名去除混淆；如果指定这个参数，那么就对文件名进行混淆')
ap.add_argument('path', nargs='+', help='ePub 所在的文件或文件夹')
args = ap.parse_args()

import subprocess
import sys

from os import path
from platform import system

from main import main

if args.confuse:
    # 混淆文件名
    main(['-ad', '-r', '-m', '6', '-raf', '-n', '-q', '-l', *args.path])
else:
    # 去除混淆文件名
    main(['-m', '3', '-raf', '-rm', '-l', *args.path])

