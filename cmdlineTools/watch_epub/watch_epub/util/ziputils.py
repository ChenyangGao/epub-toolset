#!/usr/bin/env python
# coding: utf-8

__author__  = "ChenyangGao <https://chenyanggao.github.io/>"
__version__ = (0, 1)
__all__ = ["zip", "unzip", "filter_zip_file"]


import os
from os import makedirs, path as syspath, walk
from zipfile import ZipFile


# OR you can use shutil.make_archive
# shutil.get_archive_formats() 可以查看支持的格式
# shutil.make_archive(target_path, 'zip', source_path)
def zip(path, destpath=None, makerootdir=False, predicate=None, **zipfilekwds):
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
    with ZipFile(destpath, "w", **zipfilekwds) as zf:
        if syspath.isdir(path):
            if makerootdir:
                relative_index = len(syspath.dirname(path))
            else:
                relative_index = len(path)
            for dirpath, _, filenames in walk(path):
                fpath = dirpath[relative_index:]
                for filename in filenames:
                    src = syspath.join(dirpath, filename)
                    tgt = syspath.join(fpath, filename)
                    if not predicate or predicate(src, tgt):
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

