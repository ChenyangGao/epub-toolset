#! /usr/bin/env python3
# coding: utf-8


from argparse import ArgumentParser, RawTextHelpFormatter, Namespace
from .generate_method import BASE4CHARS, NAME_GENERATORS


METHODS_DOC  = '\n'.join(
    f'[{i}] {n}:\n    {m.__doc__}' 
    for i, (n, m) in enumerate(NAME_GENERATORS.items()))


def make_parser(parser=None):
    if parser is None:
        parser = ArgumentParser(
            description='对 ePub 内在 OPF 文件所在文件夹或子文件夹下的文件修改文件名',
            formatter_class=RawTextHelpFormatter,
        )

    # TODO: 添加一个命令行参数，只有在文件名满足一定的模式的情况下才进行改名
    parser.add_argument('--full', action='store_true', default=True, 
                        help='标志当前为完整命令行参数版本（此参数不需要传）')
    parser.add_argument('-rm', '--remove-encrypt-file', dest='remove_encrypt_file', action='store_true', 
                        help='移除加密文件 META-INF/encryption.xml')
    parser.add_argument('-ad', '--add-encrypt-file', dest='add_encrypt_file', action='store_true', 
                        help='添加加密文件 META-INF/encryption.xml。如果已有加密文件，但未指定'
                             '-rm 或 --remove-encrypt-file，则忽略。')
    parser.add_argument('-l', '--epub-list', dest="list", nargs='*', default=[], 
                        help='待处理的 ePub 文件（有多个用空格隔开）')
    parser.add_argument('path', nargs='*', default=[], 
                        help='待处理的 ePub 文件（有多个用空格隔开）（等价于 -l ）')
    # TODO: 以后还会加入对 OPS 文件内 item 元素的 id 值进行正则表达式筛选
    parser.add_argument('-s', '--scan-dirs', dest="scan_dirs", nargs='*', 
                        help='在 OPF 文件所在文件夹内，会对传入的这组路径内的文件夹及其子文件夹内的文件会被重命名，'
                             '如果不指定此参数（相当于传入 \'.\' 或 \'\'）则扫描 OPF 文件所在文件夹下所有文件夹，'
                             '但如果只指定，却不传任何参数，则不会对文件进行改名（这适用于只想添加或移除加密文件）。'
                             # TODO: 增加扩展语法，提供模式匹配
                             #'\n我更提供了一下扩展语法：\n'
                             #'    1) pattern      搜索和 pattern 相等的文件夹路径\n'
                             #'    2) str:pattern  等同于 1)，搜索和 pattern 相等的文件夹路径\n'
                             #'    3) glob:pattern 把 pattern 视为 glob 模式，搜索和 pattern 相等的文件夹路径\n'
                             #'    4) re:pattern   把 pattern 视为 正则表达式 模式，搜索和 pattern 相等的文件夹路径\n'
                        )
    parser.add_argument('-r', '--recursive', action='store_true', 
                        help='如果不指定，遇到文件夹时，只扫描这个文件夹内所有.epub 结尾的文件。'
                             '如果指定，遇到文件夹时，会遍历这个文件夹及其所有子文件夹（如果有的话）'
                             '下所有 .epub 结尾的文件。')
    parser.add_argument('-g', '--glob', action='store_true', 
                        help='如果指定，则把 -l 参数传入的路径当成 glob 查询模式，如果再指定-r，'
                             '** 会匹配任何文件和任意多个文件夹或子文件夹')
    parser.add_argument('-raf', '--reset-method-after-files-processed', 
                        dest='reset_method_after_files_processed', action='store_true', 
                        help='每处理完一个文件，就对产生文件名的函数进行重置')
    parser.add_argument('-m', '--method', default='0', 
                        help='产生文件名的策略 （输入数字或名字，默认值 0）\n' + METHODS_DOC)
    parser.add_argument('-n', '--encode-filenames', dest='encode_filenames', action='store_true', 
                        help='对文件名用一些字符的可重排列进行编码')
    parser.add_argument('-ch', '--chars', default=BASE4CHARS, 
                        help='用于编码的字符集（不可重复），如果你没有指定 -n 或 --encode_filenames'
                             '，此参数被忽略，默认值是 ' + BASE4CHARS)
    parser.add_argument('-q', '--quote-names', dest='quote_names', action='store_true', 
                        help='对改动的文件名进行百分号 %% 转义')
    parser.add_argument('-x', '--suffix', default='-repack', 
                        help='已处理的 ePub 文件名为在原来的 ePub 文件名的扩展名前面添加后缀，默认值是 -repack')
    return parser

