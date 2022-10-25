#!/usr/bin/env python3
# coding: utf-8

__author__  = "ChenyangGao <https://chenyanggao.github.io/>"
__version__ = (0, 1, 2)

if __name__ == "__main__":
    from argparse import ArgumentParser, RawTextHelpFormatter

    parser = ArgumentParser(
        formatter_class=RawTextHelpFormatter, 
        description="""🫡 编辑 EPUB 文件等于编辑它的解压后文件夹 🥳

【简介】
程序会自动把指定的 EPUB 解压到临时文件夹，然后持续监控这个文件夹中的变化，包括这些事件：
    1. 新增文件 
    2. 删除文件 
    3. 改动文件名 
    4. 改动文件内容
，上面这些变动，会被实时同步到 opf 文件中，另外如果是改动文件名，就会导致引用它的位置发生改变，
😊 不用担心，这也会被自动跟进。
启动程序后，不要关闭命令行窗口（除非你并不想保留修改）。
🚀 当你想结束编辑时，在刚才打开的命令行窗口，输入 Ctrl+C ，程序就可以被正常终止了。
正常结束的程序，会生成一个改动后的 EPUB 文件。""")
    parser.add_argument("epub_path", nargs="?", help="请指定一个要编辑的 EPUB 文件路径，"
        "如果文件路径不存在，则自动创建一个 EPUB 3 标准的新文件")
    parser.add_argument("-i", "--inplace", action="store_true", help="覆盖原来的文件。"
        "不指定此参数（默认行为）时，会生成一个新文件，而不是覆盖。")
    args = parser.parse_args()
    if args.epub_path is None:
        parser.parse_args(["-h"])

try:
    import watchdog # type: ignore
except ImportError:
    choose = input("检测到缺少模块 watchdog，是否安装？ [y]/n").strip()
    if not choose or choose.lower() == "y":
        from util.usepip import install

        install("watchdog", index_url="https://pypi.tuna.tsinghua.edu.cn/simple")
    else:
        raise SystemExit("干脆退出")

from contextlib import contextmanager
from datetime import datetime
from fnmatch import fnmatch
from io import BytesIO
from os import path as syspath, remove
from pkgutil import get_data
from tempfile import TemporaryDirectory
from re import sub as re_sub
from string import Template
from time import time
from typing import Callable
from uuid import uuid4
from zipfile import ZipFile

from util.pathutils import openpath
from util.watch import watch
from util.wrapper import Wrapper
from util.ziputils import zip as makezip


@contextmanager
def ctx_epub_tempdir(path: str, is_inplace: bool = False):
    def filter_filename(srcpath, _):
        basename = syspath.basename(srcpath)
        return not (
            basename in (".DS_store", "Thumb.store", "desktop.ini")
            or fnmatch(basename, ".*")
        )

    init: Callable
    need_make_new = not syspath.exists(path)
    if need_make_new:
        def init_dir(dir_):
            from pkgutil import get_data

            data = get_data("src", "init.epub")
            bio = BytesIO()
            bio.write(data)
            bio.seek(0)
            with ZipFile(bio) as zf:
                zf.extractall(dir_)
                opffile = zf.read('OEBPS/content.opf')
            opf_updated = Template(opffile.decode("utf-8")).substitute(
                uuid=str(uuid4()), 
                modified=datetime.now().strftime("%FT%XZ"), 
            )
            open(syspath.join(dir_, 'OEBPS/content.opf'), "w").write(opf_updated)
    else:
        def init_dir(dir_):
            with ZipFile(path) as init:
                zf.extractall(dir_)

    dirname, basename = syspath.split(path)
    if basename.endswith(".epub"):
        stem = basename[:-len(".epub")]
    else:
        stem = basename
    stem = re_sub("_\d{10,}$", "", stem)

    with TemporaryDirectory() as tempdir:
        init_dir(tempdir)
        yield tempdir
        if need_make_new:
            target_path = path
        elif is_inplace:
            target_path = path
            try:
                remove(path)
            except FileNotFoundError:
                pass
        else:
            target_path = syspath.join(dirname, f"{stem}_{time():.0f}.epub")
        makezip(tempdir, target_path, predicate=filter_filename)

        print("Generated file:", target_path)


if __name__ == "__main__":
    from os import chdir, getcwd

    epub_path = args.epub_path
    is_inplace = args.inplace
    with ctx_epub_tempdir(epub_path, is_inplace) as tempdir:
        oldwd = getcwd()
        wrapper = Wrapper(tempdir)
        chdir(tempdir)
        opf_dir = wrapper.opf_dir
        openpath(opf_dir)
        chdir(opf_dir)
        watch(tempdir, wrapper)
        chdir(oldwd) 

