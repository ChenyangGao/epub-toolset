#! /usr/bin/env python3
# coding: utf-8


from common.parser import make_parser
PARSER = make_parser()


if __name__ == '__main__':
    args = PARSER.parse_args()
    if not (args.path or args.list):
        PARSER.parse_args(['-h'])


import posixpath

from argparse import Namespace
from os import path
from pkgutil import get_data
from re import compile as re_compile, Match, Pattern
from typing import (
    cast, Callable, Collection, Dict, Final, List, 
    Optional, Tuple, Union, 
)
from urllib.parse import quote, unquote, urlparse, urlunparse
from xml.etree.ElementTree import fromstring, Element
from zipfile import ZipFile, ZipInfo

from util.path import relative_path, add_stem_suffix
from common.generate_method import NAME_GENERATORS, make_generator, make_bcp_generator


ENCRYPTION_XML = cast(bytes, get_data('src', 'encryption.xml'))
METHODS_LIST = list(NAME_GENERATORS.values())

CRE_ITEM_IN_OPF: Final[Pattern] = re_compile('<item\s[^>]+?/>')
CRE_NAME: Final[Pattern] = re_compile(
    r'(?P<name>.*?)(?P<append>~[_0-9a-zA-Z]+)?(?P<suffix>\.[_0-9a-zA-z]+)')
CRE_PROT: Final[Pattern] = re_compile(r'^\w+://')
CRE_REF: Final[Pattern] = re_compile(
    r'(<[^/][^>]*?[\s:](?:href|src)=")(?P<link>[^>"]+)')
CRE_URL: Final[Pattern] = re_compile(
    r'\burl\(\s*(?:"(?P<dlink>(?:[^"]|(?<=\\)")+)"|'
    r'\'(?P<slink>(?:[^\']|(?<=\\)\')+)\'|(?P<link>[^)]+))\s*\)')
CRE_EL_STYLE: Final[Pattern] = re_compile(
    r'<style(?:\s[^>]*|)>((?s:.+?))</style>')
CRE_INLINE_STYLE: Final[Pattern] = re_compile(
    r'<[^/][^>]*?\sstyle="([^"]+)"')


def get_elnode_attrib(elnode: Union[bytes, str, Element], /) -> dict:
    '获取一个 xml/xhtml 标签的属性值'
    if not isinstance(elnode, Element):
        elnode = fromstring(elnode)
    return elnode.attrib


def get_opf_path(epub_zipfile: ZipFile, /) -> str:
    '获取 ePub 文件中的 OPF 文件的路径'
    content = epub_zipfile.read('META-INF/container.xml').decode()
    etree = fromstring(content)
    for el in etree.iter():
        if (
            (el.tag == 'rootfile' or el.tag.endswith('}rootfile')) 
            and el.attrib.get('media-type') == 'application/oebps-package+xml'
        ):
            return unquote(el.attrib['full-path'])
    raise Exception('OPF file path not found.')


def get_opf_itemmap(
    epub_zipfile: ZipFile, 
    opf_path: Union[str, ZipInfo, None] = None, 
) -> dict:
    '读取 OPF 文件的所有 item 标签，返回 href:item 标签属性的字典'
    if opf_path is None:
        opf_path = get_opf_path(epub_zipfile)
    if isinstance(opf_path, str):
        opf_dir = posixpath.dirname(opf_path)
    else:
        opf_dir = posixpath.dirname(opf_path.filename)
    if opf_dir:
        opf_dir += '/'
    opf = epub_zipfile.read(opf_path).decode()
    return {
        relative_path(
            unquote(cast(str, attrib['href'])), opf_dir, lib=posixpath
        ): attrib
        for attrib in map(get_elnode_attrib, CRE_ITEM_IN_OPF.findall(opf))
        if attrib.get('href')
    }


def make_repl_map(
    itemmap: dict, 
    generate: Callable[..., str], 
    scan_dirs: Optional[Tuple[str, ...]] = None, 
    quote_names: bool = False, 
) -> Dict[str, str]:
    '基于 OPF 文件的 href 替换映射，键是原来的 href，值是修改后的 href'
    repl_map: Dict[str, str] = {}
    key_map:  Dict[Tuple[str, str, str], str] = {}

    for href, attrib in itemmap.items():
        if attrib['media-type'] == 'application/x-dtbncx+xml':
            continue
        if scan_dirs is not None:
            if not href.startswith(scan_dirs):
                continue

        href_dir = posixpath.dirname(href)
        parts = href.split('/')
        name = parts[-1]
        match = cast(Match, CRE_NAME.fullmatch(name))
        name_dict = match.groupdict()
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

        append = name_dict['append']
        suffix = name_dict['suffix']
        stem, sffx = posixpath.splitext(generate_name)
        if append:
            if sffx == suffix:
                newname = '%s%s%s' % (stem, append, suffix)
            else:
                newname = '%s%s%s' % (generate_name, append, suffix)
        elif sffx == suffix:
            newname = generate_name
        else:
            newname = generate_name + suffix

        # 最多 2 级文件夹，超过则直接移动文件到 2 级文件夹内
        if len(parts) > 2:
            newname = posixpath.join(*parts[:2], newname)
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

    def normalize_dirname(dir_: str) -> str:
        if dir_.endswith('/'):
            return dir_
        return dir_ + '/'

    def rel_ref(src, ref):
        # NOTE: ca means common ancestors
        ca = posixpath.commonprefix((src, ref)).count('/')
        return '../' * (src.count('/') - ca) + '/'.join(ref.split('/')[ca:])

    def url_repl(m):
        try:
            link = next(filter(None, m.groups()))
        except StopIteration:
            return m[0]
        urlparts = urlparse(link)
        link = unquote(urlparts.path)
        if link in ('', '.') or CRE_PROT.match(link) is not None:
            return m[0]
        full_link = relative_path(link, srcpath, lib=posixpath)
        if full_link in repl_map:
            dest_href = rel_ref(srcpath, repl_map[full_link])
            return 'url("%s")' % urlunparse(urlparts._replace(path=dest_href))
        else:
            return m[0]

    def ref_repl(m):
        link = m['link']
        urlparts = urlparse(link)
        link = unquote(urlparts.path)
        if link in ('', '.') or CRE_PROT.match(link) is not None:
            return m[0]
        full_link = relative_path(link, srcpath, lib=posixpath)
        if full_link in repl_map:
            dest_href = rel_ref(srcpath, repl_map[full_link])
            return m[1] + urlunparse(urlparts._replace(path=dest_href))
        else:
            return m[0]

    def sub_url_in_html(text, cre=CRE_EL_STYLE):
        ls_repl_part = []
        for match in cre.finditer(text):
            repl_part, n = CRE_URL.subn(url_repl, match[0])
            if n > 0:
                ls_repl_part.append((match.span(), repl_part))
        if ls_repl_part:
            text_parts = []
            last_stop = 0
            for (start, stop), repl_part in ls_repl_part:
                text_parts.append(text[last_stop:start])
                text_parts.append(repl_part)
                last_stop = stop
            else:
                text_parts.append(text[last_stop:])
            return ''.join(text_parts)
        return text

    if scan_dirs is not None:
        if '.' in scan_dirs or '' in scan_dirs:
            scan_dirs = None
        else:
            scan_dirs = tuple(map(normalize_dirname, scan_dirs))

    with ZipFile(epub_path, mode='r') as src_epub, \
            ZipFile(epub_path2, mode='w') as tgt_epub:
        opf_path = get_opf_path(src_epub)
        itemmap = get_opf_itemmap(src_epub, opf_path)
        repl_map = make_repl_map(
            itemmap=itemmap, 
            generate=generate,
            scan_dirs=scan_dirs,
            quote_names=quote_names,
        )

        for zipinfo in src_epub.filelist:
            if zipinfo.is_dir():
                continue

            srcpath: str = zipinfo.filename
            is_opf: bool = srcpath == opf_path

            if not is_opf and srcpath not in itemmap:
                if srcpath.startswith('META-INF/'):
                    if srcpath == 'META-INF/encryption.xml':
                        if remove_encrypt_file:
                            continue
                        else:
                            has_encrypt_file = True
                elif srcpath != 'mimetype':
                    print('⚠️ 跳过文件', srcpath, 
                        '，因为它未在 %s 内被列出' % opf_path)
                    continue
                tgt_epub.writestr(zipinfo, src_epub.read(zipinfo))
                continue

            if is_empty_scan_dirs:
                tgt_epub.writestr(zipinfo, src_epub.read(zipinfo))
                continue

            if not is_opf:
                item_attrib = itemmap[srcpath]
                mimetype = item_attrib['media-type']

            content = src_epub.read(zipinfo)

            if is_opf or mimetype in ('text/css', 'text/html', 
                    'application/xhtml+xml', 'application/x-dtbncx+xml'):
                text = content.decode('utf-8')
                if is_opf or mimetype == 'application/x-dtbncx+xml':
                    text_new = CRE_REF.sub(ref_repl, text)
                elif mimetype == 'text/css':
                    text_new = CRE_URL.sub(url_repl, text)
                else:
                    text_new = CRE_REF.sub(ref_repl, text)
                    text_new = sub_url_in_html(text_new, CRE_EL_STYLE)
                    text_new = sub_url_in_html(text_new, CRE_INLINE_STYLE)  
                if text != text_new:
                    content = text_new.encode('utf-8')
                    zipinfo.file_size = len(content)

            zipinfo.filename = unquote(repl_map.get(srcpath, srcpath))
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

    epub_list: List[str] = args.path + args.list

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

    recursive: bool = args.recursive
    if args.glob:
        from glob import iglob

        for epub_glob in epub_list:
            for fpath in iglob(epub_glob, recursive=recursive):
                if path.isfile(fpath):
                    process_file(fpath)
    else:
        from util.path import iter_scan_files

        for epub in epub_list:
            if not path.exists(epub):
                print('🚨 跳过不存在的文件或文件夹：', epub)
            elif path.isdir(epub):
                for fpath in iter_scan_files(epub, recursive=recursive): # type: ignore
                    if fpath.endswith('.epub'):
                        process_file(fpath)
            else:
                process_file(epub)


if __name__ == '__main__':
    main(args=args)

