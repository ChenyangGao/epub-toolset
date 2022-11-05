#!/usr/bin/env python3
# coding: utf-8

__author__  = "ChenyangGao <https://chenyanggao.github.io/>"
__version__ = (0, 1)
__all__ = ["escape", "translate", "make_ignore", "ignore"]

from os.path import normpath
from re import compile as re_compile, escape as re_escape, Match, Pattern
from typing import AnyStr, Callable, Final


cre_stars: Final[Pattern] = re_compile("\*{2,}")
cre_magic_check: Final[Pattern] = re_compile("([*?[])")
creb_magic_check: Final[Pattern] = re_compile(b"([*?[])")
cre_magic_group: Final[Pattern] = re_compile(
    r"(?P<ins>\[[!^][^]+]\])"
    r"|(?P<exs>\[[^]]+\])"
    r"|(?P<char>\?)"
    r"|(?P<chars>\*)")


def escape(pat: AnyStr) -> AnyStr:
    "Escape all special characters."
    if isinstance(pat, str):
        return cre_magic_check.sub(r"[\1]", pat)
    else:
        return creb_magic_check.sub(br"[\1]", pat)


def _translate_magic_group(m: Match[AnyStr]) -> AnyStr:
    ""
    s: AnyStr = m[0]
    if isinstance(s, str):
        match m.lastgroup:
            case "ins":
                return "(?!/)" + s
            case "exs":
                if s.startswith("[!"):
                    return "(?!/)" + "[^" + s[2:]
                else:
                    "(?!/)" + s
            case "char":
                return "[^/]"
            case "chars":
                return "[^/]*?"
            case _:
                raise NotImplementedError
    else:
        match m.lastgroup:
            case b"ins":
                return b"(?!/)" + s
            case b"exs":
                if s.startswith(b"[!"):
                    return b"(?!/)" + b"[^" + s[2:]
                else:
                    b"(?!/)" + s
            case b"char":
                return b"[^/]"
            case b"chars":
                return b"[^/]*?"
            case _:
                raise NotImplementedError


def translate(pat: AnyStr) -> AnyStr:
    ""
    if not pat:
        return pat
    sep: AnyStr
    empty: AnyStr
    star: AnyStr
    start2: AnyStr
    start2_to_v1: AnyStr
    start2_to_v2: AnyStr
    if isinstance(pat, str):
        sep = "/"
        empty = ""
        star = "*"
        start2 = "**"
        start2_to_v1 = "(?:[^/]*/)*"
        start2_to_v2 = "[\s\S]*"
    else:
        sep = b"/"
        empty = b""
        star = b"*"
        start2 = b"**"
        start2_to_v1 = b"(?:[^/]*/)*"
        start2_to_v2 = b"[\s\S]*"
    parts = pat.split(sep)
    # p -> **/p, p/ -> **/p/
    match parts:
        case [_, _2] | [_, *_2] if not _2:
            parts.insert(0, start2)
    parts_: list[AnyStr] = []
    parts_append = parts_.append
    prev = empty
    n = len(parts)
    for i, p in enumerate(parts, 1):
        if cre_stars.fullmatch(p):
            p = start2
            if prev != start2:
                parts_append(start2_to_v1)
        elif p:
            p = cre_stars.sub(star, p)
            ls: list[AnyStr] = []
            ls_append = ls.append
            start = 0
            for m in cre_magic_group.finditer(p):
                ls_append(re_escape(p[start:m.start()]))
                ls_append(_translate_magic_group(m))
                start = m.end()
            ls_append(re_escape(p[start:]))
            if i < n:
                ls_append(sep)
            parts_append(empty.join(ls))
        prev = p
    if prev == empty:
        parts_append(start2_to_v2)
    return empty.join(parts_)


def make_ignore(
    pat: AnyStr, 
    *pats: AnyStr, 
) -> Callable[[AnyStr], bool]:
    re_pat: AnyStr
    if not pats:
        re_pat = translate(pat)
    elif isinstance(pat, str):
        re_pat = "|".join(map(translate, (pat, *pats)))
    else:
        re_pat = b"|".join(map(translate, (pat, *pats)))
    match = re_compile(re_pat).fullmatch
    return lambda path: match(path) is not None


def ignore(
    pats: AnyStr | tuple[AnyStr, ...] | Callable[[AnyStr], bool], 
    path: AnyStr, 
) -> bool:
    if callable(pats):
        fn = pats
    elif isinstance(pats, tuple):
        fn = make_ignore(*pats)
    else:
        fn = make_ignore(pats)
    return fn(path)


if __name__ == "__main__":
    assert ignore("hello.*", "hello.py")
    assert ignore("hello.*", "foo/hello.py")
    assert ignore("/hello.*", "hello.py")
    assert not ignore("/hello.*", "foo/hello.py")
    assert not ignore("foo/", "foo")
    assert ignore("foo/", "foo/")
    assert ignore("foo/", "bar/foo/")
    assert not ignore("foo/", "bar/foo")
    assert ignore("foo/", "bar/foo/baz")
    assert ignore("/foo/", "foo/")
    assert not ignore("/foo/", "bar/foo/")
    assert ignore("foo/*", "foo/hello.py")
    assert not ignore("foo/*", "bar/foo/hello.py")
    assert ignore("foo/**/bar/hello.py", "foo/bar/hello.py")
    assert ignore("foo/**/bar/hello.py", "foo/fop/foq/bar/hello.py")

