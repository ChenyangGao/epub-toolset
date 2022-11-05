#!/usr/bin/env python
# coding: utf-8

__author__  = "ChenyangGao <https://chenyanggao.github.io/>"
__version__ = (0, 0, 1)
__all__ = ["zip", "unzip", "filter_zip_file"]


import os
import os.path as syspath

from os import makedirs, walk
from zipfile import ZipFile

from util.pathutils import path_to_posix

# OR you can use shutil.make_archive
# shutil.get_archive_formats() 可以查看支持的格式
# shutil.make_archive(target_path, 'zip', source_path)
def zip(path, destpath=None, makerootdir=False, ignore=None, **zipfilekwds):
    if not syspath.exists(path):
        raise FileNotFoundError(
            f"No such file or directory: path={path!r}")
    if destpath is None:
        destpath = path + ".zip"
    elif syspath.isdir(destpath):
        destpath = syspath.join(destpath, syspath.basename(path) + ".zip")
    if syspath.exists(destpath):
        raise FileExistsError(f"File exists: destpath={destpath!r}")
    path, destpath = syspath.realpath(path), syspath.realpath(destpath)
    # TODO: 先获取文件列表，然后多线程读取本地文件，先读好的再写入zip（ZipFile.writestr），写入加锁
    with ZipFile(destpath, "w", **zipfilekwds) as zf:
        if syspath.isdir(path):
            if makerootdir:
                rel_index = len(syspath.dirname(path))
            else:
                rel_index = len(path)
            for dirpath, _, filenames in walk(path):
                fpath = dirpath[rel_index:]
                for filename in filenames:
                    src = syspath.join(dirpath, filename)
                    tgt = path_to_posix(syspath.join(fpath, filename))
                    if not ignore or ignore(tgt):
                        zf.write(src, tgt)
        else:
            zf.write(path, syspath.basename(path))


# OR you can use shutil.unpack_archive to unpack more formats
# shutil.get_unpack_formats() 可以查看支持的格式
# shutil.unpack_archive(zipped_file)
def unzip(path, destdir=None, makerootdir=False, **zipfilekwds):
    with ZipFile(path, **zipfilekwds) as zf:
        dirname, basename = syspath.split(path)
        stem, ext = syspath.splitext(basename)
        if destdir is None:
            destdir = dirname
        if makerootdir:
            destdir = syspath.join(destdir, stem)
        makedirs(destdir, exist_ok=True)
        zf.extractall(path=destdir)


def filter_zip_file(source, target, predicate):
    with zipfile.ZipFile(source, 'r') as source, \
        zipfile.ZipFile(target, 'w') as target:
        for fileinfo in source.filelist:
            if predicate(fileinfo):
                target.writestr(fileinfo, source.read(fileinfo))

