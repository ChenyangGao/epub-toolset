#! /usr/bin/env python3
# coding: utf-8
__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 3, 9)

from os import path
from re import compile as re_compile, escape as re_escape
from shutil import copyfile
from typing import (
    Callable, Collection, Dict, List, Optional, Tuple, Union
)
from urllib.parse import quote, unquote
from xml.etree.ElementTree import fromstring
from zipfile import ZipFile, ZipInfo

from util.path import add_stem_suffix, replace_stem
from util.inspect import argcount


PROJECT_FOLDER = path.dirname(__file__)
SRC_FOLDER = path.join(PROJECT_FOLDER, 'src')


# TODO: 下面的方法其实是不够精确的，以后会根据 mime-type 进行判断是不是文本文件
# 忽略的文件夹，这些文件夹内的所有文件不进行文本替换
DIR_IGNORED: Tuple[str, ...] = ('Fonts/', 'fonts/', 'Images/', 'images/', 
                                'Audio/', 'audio/', 'Video/', 'video/')


def get_elnode_attrib(elnode) -> dict:
    '获取一个 xml / xhtml 标签的属性值'
    if isinstance(elnode, (bytes, str)):
        elnode = fromstring(elnode)
    return elnode.attrib


def get_opf_path(
    epubzf: ZipFile, _cre=re_compile('full-path="([^"]+)')
) -> str:
    '''获取 ePub 文件中的 OPF 文件的路径
    该路径可能位于 META-INF/container.xml 文件的这个 xpath 路径下
        /container/rootfiles/rootfile/@full-path
    所以我尝试直接根据元素的 full-path 属性来判断，但这可能不是普遍适用的
    '''
    content = unquote(
        epubzf.read('META-INF/container.xml').decode())
    match = _cre.search(content)
    if match is None:
        raise Exception('OPF file path not found')
    return match[1]


def get_opf_itemmap(
    epubzf: ZipFile, 
    opf_path: Union[str, ZipInfo, None] = None,
    _cre=re_compile('<item .*?/>'),
) -> dict:
    '读取 OPF 文件的所有 item 标签，返回 href: item 标签属性的字典'
    if opf_path is None:
        opf_path = get_opf_path(epubzf)
    opf = unquote(epubzf.read(opf_path).decode())
    return {
        attrib['href']: attrib
        for attrib in map(get_elnode_attrib, _cre.findall(opf))
        if attrib.get('href')
    }


def make_key_newname_map(
    itemmap: dict, 
    generate: Callable[..., str],
    scan_dirs: Optional[Tuple[str, ...]],
    quote_names: bool = False,
    mode: str = 'optimistic',
    _cre=re_compile(r'(?P<suffix>~[a-zA-Z]+)\.[a-zA-z]+$'),
) -> Tuple[dict, list]:
    mode_idx: int = ('optimistic', 'pessimistic').index(mode)

    key_newname_map: Dict[str, str] = {}
    key_newname_repl: List[Tuple[str, Union[str, Callable]]] = []
    stem_map: Dict[str, str] = {}
    noarg = argcount(generate) == 0

    def register(key, stem):
        newfullname: str = replace_stem(key, stem, '/')
        orgname: str = path.basename(key)
        newname: str = path.basename(newfullname)
        key_newname_map[key] = newfullname
        # 据说在多看阅读中，混淆过的文件名可能不能被识别，比如在 css 中 import 另一 css，
        # 所以可能需要对链接进行 quote 编码
        if quote_names:
            newfullname = quote(newfullname)
        if mode_idx == 0:
            key_newname_repl.append((key, newfullname))
        elif mode_idx == 1:
            repfunc: Callable = re_compile(r'\b%s\b' % re_escape(orgname)).sub
            key_newname_repl.append((
                '\b'+orgname, 
                lambda s, *, _r=repfunc, _rp=newname: _r(_rp, s)
            ))

    stem: str
    for key, attrib in itemmap.items():
        # 据说在多看阅读，封面图片可以有 2 个版本，形如 cover.jpg 和 cover~slim.jpg，
        # 其中 cover.jpg 适用于 4:3 屏，cover~slim.jpg 适用于 16:9 屏。
        # 由于遇到上面这种设计，我不知道是不是还有类似设计，所以我用一个正则表达式，
        # 匹配扩展名前的 ~[a-zA-Z]+ 部分，当成是一种特殊的后缀，我特意增加了一组逻辑，
        # 如果两个文件名只有这种后缀部分不同，那么改名后也保证只有这种后缀部分不同，
        # 比如上述的封面图片，被改名后，会变成形如 newname.jpg 和 newname~slim.jpg
        if scan_dirs is not None:
            if not key.startswith(scan_dirs):
                continue

        match = _cre.search(key)
        if match is not None:
            pstart, ptsop = match.regs[1]
            key_ = key[:pstart] + key[ptsop:]
            if key_ in stem_map:
                stem = stem_map[key_]
            else:
                stem = stem_map[key_] = generate() if noarg else generate(attrib)
            stem += match['suffix']
        elif key in stem_map:
            stem = stem_map[key]
        else:
            stem = stem_map[key] = generate() if noarg else generate(attrib)
        register(key, stem)

    return key_newname_map, key_newname_repl


def rename_in_epub(
    epub_path: str, 
    generate_new_name: Callable[..., str] = lambda attrib: attrib['id'],
    stem_suffix: str = '-repack',
    quote_names: bool = False,
    mode: str = 'optimistic',
    remove_encrypt_file: bool = False,
    add_encrypt_file: bool = False,
    scan_dirs: Optional[Collection[str]] = None,
    ignore_dirs: Tuple[str, ...] = DIR_IGNORED,
) -> str:
    '对 ePub 内在 OPF 文件所在文件夹或子文件夹下的文件修改文件名'
    epub_path2 = add_stem_suffix(epub_path, stem_suffix)
    has_encrypt_file: bool = False
    is_empty_scan_dirs = scan_dirs == []

    def normalize_dirname(dir_: str, _cre=re_compile(r'^\.+/')) -> str:
        if dir_.startswith('.'):
            dir_ = _cre.sub('', dir_, 1)
        if not dir_.endswith('/'):
            dir_ += '/'
        return dir_

    if scan_dirs is not None:
        if '.' in scan_dirs or '' in scan_dirs:
            scan_dirs = None
        else:
            scan_dirs = tuple(map(normalize_dirname, scan_dirs))

    with ZipFile(epub_path, mode='r') as epubzf, \
            ZipFile(epub_path2, mode='w') as epubzf2:
        opf_path = get_opf_path(epubzf)
        opf_root, opf_name = path.split(opf_path)
        opf_root += '/'

        itemmap = get_opf_itemmap(epubzf, opf_path)
        key_newname_map, key_newname_repl = make_key_newname_map(
            itemmap=itemmap, 
            generate=generate_new_name,
            scan_dirs=scan_dirs,
            quote_names=quote_names,
            mode=mode,
        )

        for zipinfo in epubzf.filelist:
            if zipinfo.is_dir():
                continue # ignore directories

            zi_filename: str = zipinfo.filename

            if zi_filename == 'META-INF/encryption.xml':
                if remove_encrypt_file:
                    continue
                else:
                    has_encrypt_file = True

            if not zi_filename.startswith(opf_root):
                epubzf2.writestr(zipinfo, epubzf.read(zipinfo))
                continue

            key: str = zi_filename[len(opf_root):]  
            if key not in itemmap and key != opf_name:
                print('⚠️ 跳过文件', zi_filename, 
                      '，因为它未在 %s 内被列出' % opf_path)
                continue

            if is_empty_scan_dirs:
                content = epubzf.read(zipinfo)
                zipinfo.file_size = len(content)
                epubzf2.writestr(zipinfo, content)
                continue

            # 针对 OPF 文件专门处理，避免当 id 和 href 相等时，id 也被替换
            if key == opf_name:
                content = epubzf.read(zipinfo)
                text = unquote(content.decode())
                for key, name in key_newname_map.items():
                    text = text.replace('href="' + key, 'href="' + name)
                    text = text.replace('idref="' + key, 'idref="' + name)
                content = text.encode()
                zipinfo.file_size = len(content)
                epubzf2.writestr(zipinfo, content)
                continue

            content = epubzf.read(zipinfo)
            if key in key_newname_map:
                zipinfo.filename = opf_root + key_newname_map[key]

            if ignore_dirs and key.startswith(ignore_dirs):
                epubzf2.writestr(zipinfo, content)
                continue

            try:
                text = unquote(content.decode())
            except UnicodeDecodeError:
                epubzf2.writestr(zipinfo, content)
            else:
                for key2, replace in key_newname_repl:
                    if callable(replace):
                        text = replace(text)
                    elif type(key2) is str:
                        text = text.replace(key2, replace)
                content = text.encode()
                zipinfo.file_size = len(content)
                epubzf2.writestr(zipinfo, content)

        if add_encrypt_file and not has_encrypt_file:
            epubzf2.write(
                path.join(SRC_FOLDER, 'encryption.xml'), 
                'META-INF/encryption.xml'
            )

    return epub_path2


if __name__ == '__main__':
    from argparse import ArgumentParser, RawTextHelpFormatter

    from generate_method import (
        BASE4CHARS, NAME_GENERATORS, make_generator, make_bcp_generator
    )

    methods_list = list(NAME_GENERATORS.values())
    doc = '\n'.join(f'[{i}] {n}:\n    {m.__doc__}' 
                    for i, (n, m) in enumerate(NAME_GENERATORS.items()))

    ap = ArgumentParser(
        description='对 ePub 内在 OPF 文件所在文件夹或子文件夹下的文件修改文件名',
        formatter_class=RawTextHelpFormatter,
    )
    ap.add_argument('-rm', '--remove-encrypt-file', dest='remove_encrypt_file', action='store_true', 
                    help='移除加密文件 META-INF/encryption.xml')
    ap.add_argument('-ad', '--add-encrypt-file', dest='add_encrypt_file', action='store_true', 
                    help='添加加密文件 META-INF/encryption.xml。如果已有加密文件，但未指定'
                         '-rm 或 --remove-encrypt-file，则忽略。')
    ap.add_argument('-l', '--epub-list', dest="list", nargs='+', 
                    help='待处理的 ePub 文件（有多个用空格隔开）')
    # TODO: 以后还会加入对 OPS 文件内 item 元素的 id 值进行正则表达式筛选
    ap.add_argument('-s', '--scan-dirs', dest="scan_dirs", nargs='*', 
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
    ap.add_argument('-r', '--recursive', action='store_true', 
                    help='如果不指定，遇到文件夹时，只扫描这个文件夹内所有.epub 结尾的文件。'
                         '如果指定，遇到文件夹时，会遍历这个文件夹及其所有子文件夹（如果有的话）'
                         '下所有 .epub 结尾的文件。')
    ap.add_argument('-g', '--glob', action='store_true', 
                    help='如果指定，则把 -l 参数传入的路径当成 glob 查询模式，如果再指定-r，'
                         '** 会匹配任何文件和任意多个文件夹或子文件夹')
    ap.add_argument('-m', '--method', default='0', 
                    help='产生文件名的策略 （输入数字或名字，默认值 0）\n' + doc)
    ap.add_argument('-n', '--encode-filenames', dest='encode_filenames', action='store_true', 
                    help='对文件名用一些字符的可重排列进行编码')
    ap.add_argument('-ch', '--chars', default=BASE4CHARS, 
                    help='用于编码的字符集（不可重复，字符集大小应该是2、4、16、256之一），'
                         '如果你没有指定 -n 或 --encode_filenames，此参数被略，默认值是 '
                         + BASE4CHARS)
    ap.add_argument('-q', '--quote-names', dest='quote_names', action='store_true', 
                    help='对改动的文件名进行百分号 %% 转义')
    ap.add_argument('-md', '--mode', choices=('1', 'o', 'optimistic', '2', 'p', 'pessimistic'), 
                    default='1', type={
                        '1': 'optimistic',
                        'o': 'optimistic',
                        'optimistic': 'optimistic',
                        '2': 'pessimistic',
                        'p': 'pessimistic',
                        'pessimistic': 'pessimistic',
                    }.__getitem__, help='改名模式：\n'
                        '    1 | o | optimistic:  乐观模式（默认）。所有文件的引用路径都相对于 OPF 文件所在的文件夹\n'
                        '    2 | p | pessimistic: 悲观模式。有些文件的引用路径不相对于 OPF 文件所在的文件夹，比如引用同一文件夹内的文件只需要直接写文件名\n'
                    )
    ap.add_argument('-x', '--suffix', default='-repack', 
                    help='已处理的 ePub 文件名为在原来的 ePub 文件名的扩展名前面添加后缀，默认值是 -repack')
    args = ap.parse_args()
    try:
        method = NAME_GENERATORS[args.method]
    except KeyError:
        method_index = int(args.method)
        method = methods_list[method_index]

    if args.encode_filenames:
        method = make_bcp_generator(method, args.chars)
    else:
        method = make_generator(method)

    def process_file(epub):
        newfilename = rename_in_epub(
            epub, 
            scan_dirs=args.scan_dirs,
            stem_suffix=args.suffix, 
            quote_names=args.quote_names,
            mode=args.mode,
            generate_new_name=method,
            remove_encrypt_file=args.remove_encrypt_file,
            add_encrypt_file=args.add_encrypt_file,
        )
        print('产生文件：', newfilename)

    print('【接收参数】\n', args, '\n')
    print('【采用方法】\n', method.__name__, '\n')
    print('【方法说明】\n', method.__doc__, '\n')
    print('【处理结果】')
    if args.glob:
        from glob import iglob

        for epub_glob in args.list:
            for fpath in iglob(epub_glob, recursive=args.recursive):
                if path.isfile(fpath):
                    process_file(fpath)
    else:
        from util.path import iter_scan_files

        for epub in args.list:
            if not path.exists(epub):
                print('🚨 跳过不存在的文件或文件夹：', epub)
            elif path.isdir(epub):
                for fpath in iter_scan_files(epub, recursive=args.recursive):
                    if fpath.endswith('.epub'):
                        process_file(fpath)
            else:
                process_file(epub)

