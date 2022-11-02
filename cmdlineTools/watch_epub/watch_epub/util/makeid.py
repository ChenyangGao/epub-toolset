#!/usr/bin/env python3
# coding: utf-8

__version__ = (0, 1)
__all__ = ["TYPE_TO_MAKEID", "register", "makeid", "set_makeid"]


from functools import update_wrapper
from posixpath import basename
from time import time, time_ns
from uuid import uuid4


TYPE_TO_MAKEID = {}


def register(type, final=False):
    def wrapper(fn):
        if final:
            TYPE_TO_MAKEID.setdefault(type, fn)
        else:
            TYPE_TO_MAKEID[type] = fn
        return fn
    return wrapper


@register("basename")
def makeid_basename(bookpath, bookhref=None):
    return basename(bookpath)


@register("bookpath")
def makeid_bookpath(bookpath, bookhref=None):
    return bookpath


@register("bookhref")
def makeid_bookhref(bookpath, bookhref):
    return bookhref


@register("uuid")
def makeid_uuid(bookpath=None, bookhref=None):
    return str(uuid4())


@register("timestamp")
def makeid_timestamp(bookpath=None, bookhref=None):
    return str(time())


@register("timestamp_ns")
def makeid_timestamp_ns(bookpath=None, bookhref=None):
    return str(time_ns())


def makeid(bookpath, bookhref):
    return _makeid(bookpath, bookhref)


def set_makeid(fn):
    global _makeid
    if callable(fn):
        _makeid = fn
    else:
        _makeid = TYPE_TO_MAKEID[fn]
    update_wrapper(makeid, _makeid)

set_makeid(makeid_basename)

