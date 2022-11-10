#!/usr/bin/env python3
# coding: utf-8

__author__  = "ChenyangGao <https://chenyanggao.github.io/>"
__version__ = (0, 1, 5)
__all__ = []

# Refer to the rules of [gitignore](https://git-scm.com/docs/gitignore)
IGNORES = [".DS_Store", "._*", "Thumb.store", "desktop.ini"]

if __name__ == "__main__":
    from argparse import ArgumentParser, RawTextHelpFormatter
    from util.makeid import TYPE_TO_MAKEID

    parser = ArgumentParser(
        formatter_class=RawTextHelpFormatter, 
        description="""😄 编辑 EPUB 等于编辑它的解压后文件夹 🥳

【简介】
程序会自动把指定的 EPUB 解压到临时文件夹，然后持续监控这个文件夹中的变化，并实时同步到 opf 文件中。

监控包括以下事件：
    1. 新增文件(created)
    2. 删除文件(deleted)
    3. 移动文件(moved)
    4. 改动文件(modified)
。
文件之间存在一些引用关系：
    1. .css 引用其它 .css
    2. .html/.xhtml 引用其它文件（除了 .ncx）
    3. .ncx 引用其它 .html/.xhtml
，当文件增加、删除、移动，以及 .css/.html/.xhtml/.ncx 文件改动后，引用关系就会被自动更新。
更具体的，我会尝试从下列 media-type (mimetype) 的文件中提取引用关系：
- text/html
- application/xhtml+xml
- application/x-dtbook+xml
- application/x-dtbncx+xml
- text/css

启动程序后，不要关闭命令行窗口，否则程序会强制退出，变动也会丢失。
当你想结束编辑时，在刚才打开的命令行窗口，输入 Ctrl+C ，程序会被正常终止，且生成一个改动后的 EPUB 文件。""")
    parser.add_argument("epub_path", nargs="?", 
        help="请指定一个要编辑的 EPUB 文件路径，如果文件路径不存在，则自动创建一个符合 EPUB 3 标准的新文件。")
    parser.add_argument("-i", "--inplace", action="store_true", 
        help="覆盖原来的文件。不指定此参数（默认行为）时，会生成一个新文件，而不是覆盖。")
    parser.add_argument("-d", "--debug", action="store_true", 
        help="启用调试信息。如果指定此参数，会将日志级别设置为 DEBUG（否则，默认为 INFO）。")
    makeid_default = next(iter(TYPE_TO_MAKEID))
    parser.add_argument("-m", "--makeid", default=makeid_default, choices=TYPE_TO_MAKEID, 
    help="新文件在 OPF 中的 id。可选以下值，默认为 %s：" % makeid_default + "".join(
        "\n    %s: %s" % (typ, fn.__doc__) for typ, fn in TYPE_TO_MAKEID.items()))
    # TODO: 接受一个文件或者标准输入
    parser.add_argument("-n", "--ignore-file", dest="ignore_file", 
        help="指定一个文件路径，采用类似[gitignore](https://git-scm.com/docs/gitignore)的语法规则，"
             "用于过滤文件，默认采用如下内容：\n" + "\n".join(IGNORES))
    args = parser.parse_args()
    if args.epub_path is None:
        parser.parse_args(["-h"])

if __import__("sys").version_info < (3, 10):
    raise SystemExit("Python 版本不得低于 3.10，你的版本是\n%s" % sys.version)

from typing import Optional

def ensure_module(
    module, 
    installs: Optional[tuple[str, ...]] = None, 
    index_url: str = "https://pypi.tuna.tsinghua.edu.cn/simple", 
):
    if installs is None:
        installs = module,
    try:
        __import__(module)
    except ImportError:
        choose = input("检测到缺少模块 %s，是否安装？ [y]/n" %s).strip()
        if not choose or choose.lower() in ("y", "yes"):
            from util.piputils import install

            install(*installs, index_url=index_url)
        else:
            raise SystemExit("干脆退出")

ensure_module("watchdog")
ensure_module("lxml")

import logging
import os.path as syspath

from contextlib import contextmanager
from datetime import datetime
from io import BytesIO
from os import chdir, getcwd, remove, PathLike
from pkgutil import get_data
from tempfile import TemporaryDirectory
from re import sub as re_sub
from string import Template
from typing import AnyStr, Callable, Union
from time import time_ns
from uuid import uuid4
from warnings import warn
from zipfile import ZipFile

from util.ignore import make_ignore, read_file
from util.makeid import set_makeid
from util.opfwrapper import OpfWrapper
from util.pathutils import openpath
from util.watch import watch
from util.ziputils import zip as makezip


@contextmanager
def ctx_epub_tempdir(
    path: Union[AnyStr, PathLike[AnyStr]], 
    inplace: bool = False, 
    ignore: Optional[Callable[[str], bool]] = None, 
):
    """"""
    need_make_new = not syspath.exists(path)
    if need_make_new:
        def init_dir(dir_):
            data = get_data("src", "init.epub")
            bio = BytesIO()
            bio.write(data)
            bio.seek(0)
            with ZipFile(bio) as zf:
                zf.extractall(dir_)
                opf_content = zf.read("OEBPS/content.opf")
            opf_updated = Template(opf_content.decode("utf-8")).substitute(
                uuid=str(uuid4()), 
                modified=datetime.now().strftime("%FT%XZ"), 
            )
            opf_file = syspath.join(dir_, "OEBPS", "content.opf")
            open(opf_file, "w", encoding="utf-8").write(opf_updated)
    else:
        def init_dir(dir_):
            with ZipFile(path) as zf:
                zf.extractall(dir_)
  
    td = TemporaryDirectory()
    try:
        tempdir = td.name
        init_dir(tempdir)
        yield tempdir
        if inplace:
            target_path = path
            try:
                remove(path)
            except (FileNotFoundError, PermissionError) as exc:
                warn("Failed to delete file: %r, because of: %r" % (path, exc))
        elif syspath.isfile(path):
            dirname, basename = syspath.split(path)
            if basename.endswith(".epub"):
                stem = basename[:-5]
            else:
                stem = basename
            stem = re_sub("_\d{18,}$", "", stem)
            target_path = syspath.join(dirname, "%s_%.0f.epub" % (stem, time_ns()))
        else:
            target_path = path
        while True:
            try:
                makezip(tempdir, target_path, ignore=ignore)
                print("Generated file:", target_path)
                break
            except (PermissionError, FileNotFoundError, FileExistsError) as exc:
                print("创建文件 %r 失败，因为 %r" % (target_path, exc))
                target_path = input(
                    "请输入一个可用的保存路径后回车（不输入直接回车），则放弃保存！\n路径：")
                if not target_path:
                    print("放弃保存")
                    break
                if not syspath.isabs(target_path):
                    target_path = syspath.join(dirname, target_path)
    finally:
        try:
            td.cleanup()
        except RecursionError:
            pass


def main(args):
    """"""
    epub_path: str = args.epub_path # type: ignore
    inplace: bool = args.inplace
    debug: bool = args.debug
    makeid: str = args.makeid
    ignore_file: Optional[str] = args.ignore_file

    set_makeid(args.makeid)

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    handler = logging.StreamHandler()
    logger.addHandler(handler)
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s ➜ %(message)s")
    formatter.datefmt = "%Y-%m-%d %H:%M:%S"
    handler.setFormatter(formatter)

    ignores: list[str]
    if ignore_file is None:
        ignores = IGNORES
    else:
        ignores = read_file(ignore_file)

    main_ignore = make_ignore("/META-INF/", "/mimetype")
    ignore = make_ignore("/META-INF/", "/mimetype", *ignores)

    with ctx_epub_tempdir(
        epub_path, 
        inplace=inplace, 
        ignore=lambda p: not main_ignore(p) or p not in opfwrapper.bookpath_to_id
    ) as tempdir:
        oldwd = getcwd()
        opfwrapper = OpfWrapper(tempdir)
        chdir(tempdir)
        opf_dir = opfwrapper.bookpath_to_path(opfwrapper.opf_dir)
        if not opf_dir:
            opf_dir = "."
        openpath(opf_dir)
        chdir(opf_dir)
        watch(opfwrapper, logger=logger, ignore=ignore)
        chdir(oldwd)


if __name__ == "__main__":
    main(args)

