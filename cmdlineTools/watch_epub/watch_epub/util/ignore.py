#!/usr/bin/env python3
# coding: utf-8

"""https://git-scm.com/docs/gitignore
"""

__author__  = "ChenyangGao <https://chenyanggao.github.io/>"
__version__ = (0, 1, 1)
__all__ = ["escape", "translate", "make_ignore", "ignore", "read_file"]

from os import PathLike
from re import compile as re_compile, escape as re_escape, Match, Pattern
from typing import AnyStr, Callable, Final, Sequence


cre_stars: Final[Pattern] = re_compile("\*{2,}")
cre_magic_check: Final[Pattern] = re_compile("([*?[])")
creb_magic_check: Final[Pattern] = re_compile(b"([*?[])")
cre_magic_group: Final[Pattern] = re_compile(
    r"(?P<chars>\*)"           # *
    r"|(?P<char>\?)"           # ?
    r"|(?P<exs>\[[!^][^]]+\])" # [^...] or [!...]
    r"|(?P<ins>\[[^]]+\])"     # [...]
)


def escape(pat: AnyStr) -> AnyStr:
    "Escape all special characters. Act like `glob.escape`."
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
                    return "(?!/)" + s
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
                    return b"(?!/)" + s
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
    star2: AnyStr
    star2_to_v1: AnyStr
    star2_to_v2: AnyStr
    if isinstance(pat, str):
        sep = "/"
        empty = ""
        star = "*"
        star2 = "**"
        star2_to_v1 = "(?:[^/]*/)*"
        star2_to_v2 = "[\s\S]*"
    else:
        sep = b"/"
        empty = b""
        star = b"*"
        star2 = b"**"
        star2_to_v1 = b"(?:[^/]*/)*"
        star2_to_v2 = b"[\s\S]*"
    parts = pat.split(sep)
    # p -> **/p, p/ -> **/p/
    match parts:
        case [e]:
            parts = [star2, e]
        case [e, e2] if e2 == empty:
            parts = [star2, e, e2]
    parts_: list[AnyStr] = []
    parts_append = parts_.append
    prev = empty
    n = len(parts)
    for i, p in enumerate(parts, 1):
        if cre_stars.fullmatch(p):
            p = star2
            if prev != star2:
                parts_append(star2_to_v1)
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
        parts_append(star2_to_v2)
    return empty.join(parts_)


def make_ignore(
    pat: AnyStr, 
    *pats: AnyStr, 
) -> Callable[[AnyStr], bool]:
    ""
    re_pat: AnyStr
    def get_ignore(pat: AnyStr) -> Callable[[AnyStr], bool]:
        if pat.startswith("!"):
            match = re_compile(translate(pat[1:])).fullmatch
            return lambda path: match(path) is None
        else:
            match = re_compile(translate(pat)).fullmatch
            return lambda path: match(path) is not None
    ignore = get_ignore(pat)
    if not pats:
        return ignore
    ignores = (ignore, *(map(get_ignore, pats)))
    return lambda path: all(ignore(path) for ignore in ignores)


def ignore(
    pats: AnyStr | Sequence[AnyStr] | Callable[[AnyStr], bool], 
    path: AnyStr, 
) -> bool:
    """

    Description:
        See: https://git-scm.com/docs/gitignore#_pattern_format

    Examples::
        >>> ignore("hello.*", "hello.py")
        True
        >>> ignore("hello.*", "foo/hello.py")
        True
        >>> ignore("/hello.*", "hello.py")
        True
        >>> not ignore("/hello.*", "foo/hello.py")
        True
        >>> not ignore("foo/", "foo")
        True
        >>> ignore("foo/", "foo/")
        True
        >>> ignore("foo/", "bar/foo/")
        True
        >>> not ignore("foo/", "bar/foo")
        True
        >>> ignore("foo/", "bar/foo/baz")
        True
        >>> ignore("/foo/", "foo/")
        True
        >>> not ignore("/foo/", "bar/foo/")
        True
        >>> ignore("foo/*", "foo/hello.py")
        True
        >>> not ignore("foo/*", "bar/foo/hello.py")
        True
        >>> ignore("foo/**/bar/hello.py", "foo/bar/hello.py")
        True
        >>> ignore("foo/**/bar/hello.py", "foo/fop/foq/bar/hello.py")
        True
        >>> ignore("h?llo.py", "hello.py")
        True
        >>> ignore("h[a-g]llo.py", "hello.py")
        True
        >>> not ignore("h[^a-g]llo.py", "hello.py")
        True
        >>> not ignore("h[!a-g]llo.py", "hello.py")
        True
        >>> not ignore("!hello.py", "hello.py")
        True
    """
    if callable(pats):
        fn = pats
    elif isinstance(pats, tuple):
        fn = make_ignore(*pats)
    else:
        fn = make_ignore(pats)
    return fn(path)


def read_file(
    path: AnyStr | PathLike[AnyStr], 
) -> list[str]:
    ""
    return [l for l in open(path, encoding="utf-8") 
              if l.strip() and not l.startswith("#")]


if __name__ == "__main__":
    import doctest
    doctest.testmod()

