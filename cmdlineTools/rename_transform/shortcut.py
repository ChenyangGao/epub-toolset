#! /usr/bin/env python3
# coding: utf-8

from argparse import ArgumentParser, RawTextHelpFormatter

ap = ArgumentParser(
    description='对 ePub 内在 OPF 文件所在文件夹或子文件夹下的文件修改文件名',
    formatter_class=RawTextHelpFormatter,
)
ap.add_argument('-c', '--confound', action='store_true', 
                help='如果不指定这个参数，那么对文件名去除混淆；如果指定这个参数，那么就对文件名进行混淆')
ap.add_argument('pathes', nargs='+', help='ePub 所在的文件或文件夹')
args = ap.parse_args()

import subprocess
import sys

from os import path
from platform import system

PROJECT_FOLDER = path.dirname(__file__)
MAIN_MODULE_FILE = path.join(PROJECT_FOLDER, 'main.py')


if args.confound:
    subprocess.run(
        [sys.executable, MAIN_MODULE_FILE, '-ad', '-r', 
        '-m', '6', '-n', '-q', '-l', *args.pathes], 
        shell=system()=='Windows')
else:
    subprocess.run(
        [sys.executable, MAIN_MODULE_FILE, '-m', '3', '-rm', '-l', *args.pathes], 
        shell=system()=='Windows')

