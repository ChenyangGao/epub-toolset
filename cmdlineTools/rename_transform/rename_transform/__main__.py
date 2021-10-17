#! /usr/bin/env python3
# coding: utf-8

__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 4, 4)


from argparse import ArgumentParser, RawTextHelpFormatter

from common.parser import make_parser


PARSER = ArgumentParser(
    description='对 ePub 内在 OPF 文件所在文件夹或子文件夹下的文件修改文件名',
    formatter_class=RawTextHelpFormatter,
)
PARSER.add_argument('-c', '--confuse', action='store_true', 
                    help='如果不指定这个参数，那么对文件名去除混淆；'
                         '如果指定这个参数，那么对文件名进行混淆')
PARSER.add_argument('-l', '--epub-list', dest="list", nargs='*', default=[], 
                    help='待处理的 ePub 文件（有多个用空格隔开）')
PARSER.add_argument('path', nargs='*', default=[], 
                    help='待处理的 ePub 文件（有多个用空格隔开）（等价于 -l ）')

subparsers = PARSER.add_subparsers(help='sub-command help')
subparser_full = subparsers.add_parser('full', help='使用完整版命令行参数')
make_parser(subparser_full)


args = PARSER.parse_args()

is_full_parser = 'full' in args

if not (args.path or args.list):
    if is_full_parser:
        PARSER.parse_args(['full', '-h'])
    PARSER.parse_args(['-h'])


from main import main


if is_full_parser:
    # 使用完整版
    main(args=args)
elif args.confuse:
    # 混淆文件名
    main(['-ad', '-r', '-m', '6', '-raf', '-n', 
          '-q', '-l', *args.path, *args.list])
else:
    # 去除混淆文件名
    main(['-m', '3', '-raf', '-rm', '-l', 
          *args.path, *args.list])

