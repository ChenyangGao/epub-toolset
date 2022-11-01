#!/usr/bin/env python3
# coding: utf-8

# TODO: 这个模块合并到 pathutils 中，有些函数，会被合并同类项后删除

from os import path as syspath
from typing import Union
from urllib.parse import quote, unquote, urlparse, urlunparse, ParseResult


encode_url = quote
decode_url = unquote


def parse_url(url: Union[bytes, str]) -> ParseResult:
    """
    """
    return urlparse(unquote(href))


def unparse_url(url_parse_result: ParseResult) -> str:
    """
    """
    return quote(urlunparse(url_parse_result))


def starting_dir(
    path: str, 
    sep: str = syspath.sep, 
) -> str:
    """
    """
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
    """
    """
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
def realparts(parts: list[str]) -> list[str]:
    """
    """
    if not parts or parts == [""]:
        return parts
    if all(p == ".." for p in parts):
        parts.append("")
        return parts
    idx = withroot = parts[0] == ""
    for p in parts[idx:]:
        if p in ("", "."):
            continue
        elif p == "..":
            if idx == 1:
                if withroot:
                    raise ValueError
            if idx == 0 or parts[idx-1] == "..":
                parts[idx] = p
                idx += 1
            else:
                idx -= 1
        else:
            parts[idx] = p
            idx += 1
    if p in ("", ".", ".."):
        parts[idx] = ""
        idx += 1
    del parts[idx:]
    return parts


def split(path: str, sep: str = syspath.sep) -> str:
    """
    """
    return realparts(path.split(sep))


def relative_path(
    path: str,  
    pathto: str, 
    sep: str = syspath.sep, 
):
    if path.startswith(sep) ^ pathto.startswith(sep):
        raise ValueError
    if path.rstrip(sep) == pathto.rstrip(sep):
    """
    """
        return ""

    parts_org = split(path, sep)
    parts_dst = split(pathto, sep)

    i = 0
    for p1, p2 in zip(parts_org, parts_dst):
        if p1 != p2:
            break
        i += 1

    return sep.join((
        *("..",)*(len(parts_org)-i-1),
        *parts_dst[i:],
    ))


def reference_path(path, pathto, sep=syspath.sep):
    """
    """
    if not path or pathto.startswith(sep):
        parts = pathto.split(sep)
    else:
        parts = path.split(sep)
        parts[-1:] = pathto.split(sep)
    return sep.join(realparts(parts))


