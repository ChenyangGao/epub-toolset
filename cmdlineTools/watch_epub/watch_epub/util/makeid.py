#!/usr/bin/env python3
# coding: utf-8

__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 1, 1)
__all__ = ["TYPE_TO_MAKEID", "register", "makeid", "set_makeid"]


from itertools import count
from functools import update_wrapper
from os import urandom
from posixpath import basename
from time import time, time_ns
from typing import Callable
from uuid import uuid4


TYPE_TO_MAKEID: dict[str, Callable] = {}

_countfrom0 = count(0)
_countfrom1 = count(1)


def register(type, final=False):
    def wrapper(fn):
        if final:
            TYPE_TO_MAKEID.setdefault(type, fn)
        else:
            TYPE_TO_MAKEID[type] = fn
        return fn
    return wrapper


@register("name")
def makeid_name(href, bookpath=None):
    "文件名"
    return basename(href)


@register("href")
def makeid_href(href, bookpath=None):
    "相对于 opf 文件所在目录的相对路径"
    return href


@register("bookpath")
def makeid_bookpath(href, bookpath):
    "相对于 epub 根目录的相对路径"
    return bookpath


@register("uuid")
def makeid_uuid(href=None, bookpath=None):
    "4 位 UUID"
    return str(uuid4())


@register("timestamp")
def makeid_timestamp(href=None, bookpath=None):
    "时间戳（单位是秒，值是浮点数）"
    return str(time())


@register("timestamp_ns")
def makeid_timestamp_ns(href=None, bookpath=None):
    "时间戳（单位是纳秒，值是整数）"
    return str(time_ns())


@register("randomhex64")
def makeid_randomhex64(href=None, bookpath=None):
    "64 位随机 hex 字符串（只包含 0-9a-z）"
    # 可用：os.urandom, random.randbytes, secrets.token_bytes
    return urandom(32).hex()


@register("countfrom0")
def makeid_countfrom0(href=None, bookpath=None):
    "从 0 开始计数的 id"
    return next(_countfrom0)


@register("countfrom1")
def makeid_countfrom1(href=None, bookpath=None):
    "从 1 开始计数的 id"
    return next(_countfrom1)


def makeid(href, bookpath, na_id_set=None):
    ""
    newid = _makeid(href, bookpath)
    if na_id_set:
        while newid in na_id_set:
            newid2 = _makeid(href, bookpath)
            if newid == newid2:
                raise ValueError("Failed to makeid!")
            newid = newid2
    return newid


def set_makeid(fn):
    ""
    global _makeid
    if callable(fn):
        _makeid = fn
    else:
        _makeid = TYPE_TO_MAKEID[fn]
    update_wrapper(makeid, _makeid)

set_makeid(makeid_name)

