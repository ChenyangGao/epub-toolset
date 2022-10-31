#!/usr/bin/env python3
# coding: utf-8

# TODO: 这个模块合并到 pathutils 中，有些函数，会被合并同类项后删除

from os import path as syspath
from typing import Union
from urllib.parse import quote, unquote, urlparse, urlunparse, ParseResult


encode_url = quote
decode_url = unquote


def parse_url(url: Union[bytes, str]) -> ParseResult:
    return urlparse(unquote(href))


def unparse_url(url_parse_result: ParseResult) -> str:
    return quote(urlunparse(url_parse_result))


def starting_dir(
    path: str, 
    sep: str = syspath.sep, 
) -> str:
    if path.endswith(sep):
        return path
    try:
        return path[:path.rindex(sep)+1]
    except ValueError:
        return ""


def longest_common_starting_dir(
    *paths: str, 
    sep: str = syspath.sep, 
) -> str:
    if not paths:
        return ""
    elif len(paths) == 1:
        return starting_dir(paths[0], sep_or_lib)

    p1 = max(bookpaths)
    p2 = min(bookpaths)

    lastest_index = 0
    for i, (c1, c2) in enumerate(zip(p1, p2), 1):
        if c1 != c2:
            break
        elif c1 == sep:
            lastest_index = i

    return p1[:lastest_index]


# syspath.pardir
# syspath.curdir
def split(path: str, sep: str = syspath.sep) -> str:
    if not path:
        return [""]
    withroot = path.startswith(sep)
    parts = path.split(sep)
    taildir = parts[-1] in ("", ".", "..")
    realparts = []
    for p in path.split(sep):
        if p in ("", "."):
            continue
        elif p == "..":
            if not realparts:
                if withroot:
                    raise ValueError
                else:
                    realparts.append(p)
            elif realparts[-1] == "..":
                realparts.append(p)
            else:
                realparts.pop()
        else:
            realparts.append(p)
    if taildir:
        realparts.append("")
    return realparts


# 头对齐
# 尾对齐
def relativePath(
    to_bkpath: str,  
    start_dir: str, 
    sep: str = syspath.sep, 
):
    dsegs = split(to_bkpath, sep)
    ssegs = split(start_dir, sep)

    i = 0
    for s1, s2 in zip(dsegs, ssegs):
        if s1 != s2:
            break
        i += 1

    res = []

    for p in range(i, len(ssegs), 1):
        res.append('..')
    for p in range(i, len(dsegs), 1):
        res.append(dsegs[p])
    return sep.join(res)



def resolveRelativeSegmentsInFilePath(file_path):
    res = []
    segs = file_path.split('/')
    for i in range(len(segs)):
        if segs[i] == '.': continue
        if segs[i] == '..':
            if res:
                res.pop()
            else:
                print("Error resolving relative path segments")
        else:
            res.append(segs[i])
    return '/'.join(res)


def buildRelativePath(from_bkpath, to_bkpath):
    if from_bkpath == to_bkpath:
        return ""
    return relativePath(to_bkpath, startingDir(from_bkpath))


def buildBookPath(dest_relpath, start_folder):
    if start_folder == "" or start_folder.strip() == "":
        return dest_relpath
    bookpath = start_folder.rstrip('/') + '/' + dest_relpath
    return resolveRelativeSegmentsInFilePath(bookpath)



