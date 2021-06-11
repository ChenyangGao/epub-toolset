#! /usr/bin/env python3
# coding: utf-8


PARSER = __import__('parser').make_parser()


if __name__ == '__main__':
    args = PARSER.parse_args()
    if not (args.path or args.list):
        PARSER.parse_args(['-h'])


import posixpath

from argparse import Namespace
from os import path
from pkgutil import get_data
from re import compile as re_compile, Pattern
from typing import (
    Callable, Collection, Dict, Final, List, 
    Optional, Tuple, Union, 
)
from urllib.parse import quote, unquote
from xml.etree.ElementTree import fromstring
from zipfile import ZipFile, ZipInfo

from util.path import relative_path, add_stem_suffix
from generate_method import BASE4CHARS, NAME_GENERATORS, make_generator, make_bcp_generator

ENCRYPTION_XML = get_data('src', 'encryption.xml')
METHODS_LIST = list(NAME_GENERATORS.values())

CRE_NAME: Final[Pattern] = re_compile(r'(?P<name>.*?)(?P<append>~[_0-9a-zA-Z]+)?(?P<suffix>\.[_0-9a-zA-z]+)')
CRE_PROT: Final[Pattern] = re_compile(r'\w+:/')
CRE_LINK: Final[Pattern] = re_compile(r'([^#?]+)(.*)')
CRE_HREF: Final[Pattern] = re_compile(r'(<[^/][^>]+\bhref=")(?P<link>[^>"]+)')
CRE_SRC : Final[Pattern] = re_compile(r'(<[^/][^>]+\bsrc=")(?P<link>[^>"]+)')
CRE_URL : Final[Pattern] = re_compile(r'\burl\(\s*(?:"(?P<dlink>(?:[^"]|(?<=\\)")+)"|\'(?P<slink>(?:[^\']|(?<=\\)\')+)\'|(?P<link>[^)]+))\s*\)')


def get_elnode_attrib(elnode) -> dict:
    '获取一个 xml / xhtml 标签的属性值'
    if isinstance(elnode, (bytes, str)):
        elnode = fromstring(elnode)
    return elnode.attrib


def get_opf_path(
    src_epub: ZipFile, _cre=re_compile('full-path="([^"]+)')
) -> str:
    '''获取 ePub 文件中的 OPF 文件的路径
    该路径可能位于 META-INF/container.xml 文件的这个 xpath 路径下
        /container/rootfiles/rootfile/@full-path
    所以我尝试直接根据元素的 full-path 属性来判断，但这可能不是普遍适用的
    '''
    content = unquote(
        src_epub.read('META-INF/container.xml').decode())
    match = _cre.search(content)
    if match is None:
        raise Exception('OPF file path not found')
    return match[1]


def get_opf_itemmap(
    src_epub: ZipFile, 
    opf_path: Union[str, ZipInfo, None] = None,
    _cre=re_compile('<item .*?/>'),
) -> dict:
    '读取 OPF 文件的所有 item 标签，返回 href: item 标签属性的字典'
    if opf_path is None:
        opf_path = get_opf_path(src_epub)
    opf = unquote(src_epub.read(opf_path).decode())
    return {
        attrib['href']: attrib
        for attrib in map(get_elnode_attrib, _cre.findall(opf))
        if attrib.get('href')
    }


def make_repl_map(
    itemmap: dict, 
    generate: Callable[..., str], 
    scan_dirs: Optional[Tuple[str, ...]] = None, 
    quote_names: bool = False, 
) -> Tuple[dict, list]:
    '基于 OPF 文件的 href 替换映射，键是原来的 href，值是修改后的 href'
    repl_map: Dict[str, str] = {}
    key_map:  Dict[str, str] = {}

    for href, attrib in itemmap.items():
        if href == 'toc.ncx':
            continue
        if scan_dirs is not None:
            if not href.startswith(scan_dirs):
                continue

        href_dir = posixpath.dirname(href)
        parts = href.split('/')
        name = parts[-1]
        name_dict = CRE_NAME.fullmatch(name).groupdict()
        key = (href_dir, name_dict['name'], name_dict['suffix'])

        # 据说在多看阅读，封面图片可以有 2 个版本，形如 cover.jpg 和 cover~slim.jpg，
        # 其中 cover.jpg 适用于 4:3 屏，cover~slim.jpg 适用于 16:9 屏。
        # 由于遇到上面这种设计，我不知道是不是还有类似设计，所以我用一个正则表达式，
        # 匹配扩展名前的 ~[_0-9a-zA-Z]+ 部分，当成是一种特殊的后缀，为此我特意增加了一组逻辑，
        # 如果两个文件名只有这种后缀部分不同，那么改名后也保证只有这种后缀部分不同，
        # 比如上述的封面图片，被改名后，会变成形如 newname.jpg 和 newname~slim.jpg
        if key in key_map:
            generate_name = key_map[key]
        else:
            generate_name = key_map[key] = generate(attrib)

        suffix = name_dict['suffix']
        if generate_name.endswith(name_dict['suffix']):
            suffix = ''

        newname = '%s%s%s' % (generate_name, name_dict['append'] or '', suffix)
        if len(parts) > 1:
            newname = posixpath.join(parts[0], newname)
        if quote_names:
            newname = quote(newname)
        repl_map[href] = newname

    return repl_map


def rename_in_epub(
    epub_path: str, 
    generate: Callable[..., str] = lambda attrib: attrib['id'],
    stem_suffix: str = '-repack',
    quote_names: bool = False,
    remove_encrypt_file: bool = False,
    add_encrypt_file: bool = False,
    scan_dirs: Optional[Collection[str]] = None,
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

    def css_repl(m):
        md = m.groupdict()
        if md['dlink']:
            link = unquote(md['dlink'])
        elif md['slink']:
            link = unquote(md['slink'])
        elif md['link']:
            link = unquote(md['link'])
        else:
            return m[0]

        if link.startswith(('#', '/')) or CRE_PROT.match(link) is not None:
            return m[0]

        uri, suf = CRE_LINK.fullmatch(link).groups()
        full_uri = relative_path(uri, opf_href, lib=posixpath)
        if full_uri in repl_map:
            return 'url("%s%s%s")' % (advance_str, repl_map[full_uri], suf)
        else:
            return m[0]

    def hxml_repl(m):
        link = unquote(m['link'])
        if link.startswith(('#', '/')) or CRE_PROT.match(link) is not None:
            return m[0]

        uri, suf = CRE_LINK.fullmatch(link).groups()
        full_uri = relative_path(uri, opf_href, lib=posixpath)
        if full_uri in repl_map:
            return m[1] + advance_str + repl_map[full_uri] + suf
        else:
            return m[0]

    if scan_dirs is not None:
        if '.' in scan_dirs or '' in scan_dirs:
            scan_dirs = None
        else:
            scan_dirs = tuple(map(normalize_dirname, scan_dirs))

    with ZipFile(epub_path, mode='r') as src_epub, \
            ZipFile(epub_path2, mode='w') as tgt_epub:
        opf_path = get_opf_path(src_epub)
        opf_root, opf_name = posixpath.split(opf_path)
        opf_root += '/'
        opf_root_len = len(opf_root)

        itemmap = get_opf_itemmap(src_epub, opf_path)
        repl_map = make_repl_map(
            itemmap=itemmap, 
            generate=generate,
            scan_dirs=scan_dirs,
            quote_names=quote_names,
        )

        for zipinfo in src_epub.filelist:
            if zipinfo.is_dir():
                continue # ignore directories

            zi_filename: str = zipinfo.filename

            if zi_filename == 'META-INF/encryption.xml':
                if remove_encrypt_file:
                    continue
                else:
                    has_encrypt_file = True

            if not zi_filename.startswith(opf_root):
                tgt_epub.writestr(zipinfo, src_epub.read(zipinfo))
                continue

            opf_href: str = zi_filename[opf_root_len:]  
            if opf_href not in itemmap and opf_href != opf_name:
                print('⚠️ 跳过文件', zi_filename, 
                      '，因为它未在 %s 内被列出' % opf_path)
                continue

            if is_empty_scan_dirs:
                content = src_epub.read(zipinfo)
                zipinfo.file_size = len(content)
                tgt_epub.writestr(zipinfo, content)
                continue

            is_opf_file = opf_href == opf_name

            advance_str = ''
            mimetype = None
            if opf_href in itemmap:
                item_attrib = itemmap[opf_href]
                mimetype = item_attrib['media-type']
                if opf_href in repl_map:
                    advance_str = '../' * (len(repl_map[opf_href].split('/')) - 1)

            content = src_epub.read(zipinfo)

            if is_opf_file or mimetype in ('text/css', 'text/html', 'application/xml', 
                                        'application/xhtml+xml', 'application/x-dtbncx+xml'):
                text = content.decode('utf-8')
                if is_opf_file or mimetype != 'text/css':
                    text_new = CRE_HREF.sub(hxml_repl, text)
                    text_new = CRE_SRC.sub(hxml_repl, text_new)
                else:
                    text_new = CRE_URL.sub(css_repl, text)
                if text != text_new:
                    content = text_new.encode('utf-8')
                    zipinfo.file_size = len(content)

            zipinfo.filename = opf_root + unquote(repl_map.get(opf_href, opf_href))
            tgt_epub.writestr(zipinfo, content)

        if add_encrypt_file and not has_encrypt_file:
            tgt_epub.writestr('META-INF/encryption.xml', ENCRYPTION_XML)

    return epub_path2


def main(
    argv: Optional[List[str]] = None, 
    args: Optional[Namespace] = None
):
    '主函数'
    if args is None:
        args = PARSER.parse_args(argv)

    epub_list = args.path + args.list

    try:
        method = NAME_GENERATORS[args.method]
    except KeyError:
        method_index = int(args.method)
        method = METHODS_LIST[method_index]

    reset = None
    if args.reset_method_after_files_processed:
        reset = getattr(method, 'reset', None)

    if args.encode_filenames:
        method = make_bcp_generator(method, args.chars)
    else:
        method = make_generator(method)

    def process_file(epub):
        try:
            newfilename = rename_in_epub(
                epub, 
                scan_dirs=args.scan_dirs,
                stem_suffix=args.suffix, 
                quote_names=args.quote_names,
                generate=method,
                remove_encrypt_file=args.remove_encrypt_file,
                add_encrypt_file=args.add_encrypt_file,
            )
            print('产生文件：', newfilename)
        finally:
            if reset:
                reset()

    print('【接收参数】\n', args, '\n')
    print('【采用方法】\n', method.__name__, '\n')
    print('【方法说明】\n', method.__doc__, '\n')
    print('【处理结果】')
    if args.glob:
        from glob import iglob

        for epub_glob in epub_list:
            for fpath in iglob(epub_glob, recursive=args.recursive):
                if path.isfile(fpath):
                    process_file(fpath)
    else:
        from util.path import iter_scan_files

        for epub in epub_list:
            if not path.exists(epub):
                print('🚨 跳过不存在的文件或文件夹：', epub)
            elif path.isdir(epub):
                for fpath in iter_scan_files(epub, recursive=args.recursive):
                    if fpath.endswith('.epub'):
                        process_file(fpath)
            else:
                process_file(epub)


if __name__ == '__main__':
    main(args=args)

