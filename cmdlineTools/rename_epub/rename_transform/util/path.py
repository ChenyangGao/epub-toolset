#! /usr/bin/env python3
# coding: utf-8

__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 2)
__all__ = [
    'split', 'rsplit', 'split3', 'get_fext', 'get_stem', 'split_components', 
    'relative_path', 'replace_stem', 'add_stem_preffix', 'add_stem_suffix', 
    'iter_list_files', 'iter_scan_files', 'iter_walk_files', 
]


from os import path
from os import fspath, listdir, scandir, walk, DirEntry, PathLike
from typing import (
    overload, Any, Generator, List, Optional, Tuple, Union
)


@overload
def split(
    s: bytes, 
    sep: Optional[bytes], 
    maxsplit: int, 
    start: Optional[int], 
    stop: Optional[int], 
) -> List[bytes]:
    ...
@overload
def split(
    s: str, 
    sep: Optional[str], 
    maxsplit: int, 
    start: Optional[int], 
    stop: Optional[int], 
) -> List[str]:
    ...
def split(
    s, 
    sep=None, 
    maxsplit=-1, 
    start=0, 
    stop=None, 
):
    if start in (0, None) and stop is None:
        return s.split(sep, maxsplit)

    if start in (0, None):
        prefix = ''
        remain, suffix = s[:stop], s[stop:]
    elif stop is None:
        prefix, remain = s[:start], s[start:]
        suffix = ''
    else:
        prefix, remain, suffix = s[:start], s[start:stop], s[stop:]

    parts = remain.split(sep, maxsplit)
    if prefix:
        parts[0] = prefix + parts[0]
    if suffix:
        parts[-1] = parts[-1] + suffix
    return parts


@overload
def rsplit(
    s: bytes, 
    sep: Optional[bytes], 
    maxsplit: int, 
    start: Optional[int], 
    stop: Optional[int], 
) -> List[bytes]:
    ...
@overload
def rsplit(
    s: str, 
    sep: Optional[str], 
    maxsplit: int, 
    start: Optional[int], 
    stop: Optional[int], 
) -> List[str]:
    ...
def rsplit(
    s, 
    sep=None, 
    maxsplit=-1, 
    start=0, 
    stop=None, 
):
    if start in (0, None) and stop is None:
        return s.rsplit(sep, maxsplit)

    if start in (0, None):
        prefix = ''
        remain, suffix = s[:stop], s[stop:]
    elif stop is None:
        prefix, remain = s[:start], s[start:]
        suffix = ''
    else:
        prefix, remain, suffix = s[:start], s[start:stop], s[stop:]

    parts = remain.rsplit(sep, maxsplit)
    if prefix:
        parts[0] = prefix + parts[0]
    if suffix:
        parts[-1] = parts[-1] + suffix
    return parts


@overload
def split3(fpath: bytes, lib: Any = ...) -> Tuple[bytes, bytes, bytes]:
    ...
@overload
def split3(fpath: str, lib: Any = ...) -> Tuple[str, str, str]:
    ...
def split3(fpath, lib=path):
    '''Split the path `fpath` into a tuple (dirpath, barename, extension).
    Where
        dirpath: Everything leading up to the last pathname component (basename).
        barename: The last pathname component (basename) without extension, also called stem.
        extension: The extension of the last pathname component (basename), if any.
    Note: Extension is empty or begins with a period (.) and contains at most one period.
    '''
    dirpath, filename = lib.split(fpath)
    barename, extension = lib.splitext(filename)
    return dirpath, barename, extension


@overload
def get_fext(fpath: bytes, lib: Any = ...) -> bytes:
    ...
@overload
def get_fext(fpath: str, lib: Any = ...) -> str:
    ...
def get_fext(fpath, lib=path):
    'Return the file extension of the `fpath`, if any.'
    return lib.splitext(fpath)[1]


@overload
def get_stem(fpath: bytes, lib: Any = ...) -> bytes:
    ...
@overload
def get_stem(fpath: str, lib: Any = ...) -> str:
    ...
def get_stem(fpath, lib=path):
    '''Return the stem component of the `fpath`.
    Note: stem is the final path component, without its suffix (file extension).
    '''
    return lib.dirname(lib.splitext(fpath)[0])


@overload
def split_components(fpath: bytes, lib: Any = ...) -> List[bytes]:
    ...
@overload
def split_components(fpath: str, lib: Any = ...) -> List[str]:
    ...
def split_components(fpath, lib=path):
    sep = lib.sep
    if isinstance(fpath, bytes):
        sep = sep.encode()
    return split(fpath, sep)


@overload
def relative_path(ref_path: bytes, rel_path: bytes, lib: Any = ...) -> bytes:
    ...
@overload
def relative_path(ref_path: str, rel_path: str, lib: Any = ...) -> str:
    ...
def relative_path(ref_path, rel_path, lib=path):
    'Relative to the directory of `rel_path`, return the path of `file_path`.'
    curdir, pardir, sep = lib.curdir, lib.pardir, lib.sep

    if isinstance(ref_path, bytes):
        curdir, pardir, sep = curdir.encode(), pardir.encode(), sep.encode()

    if not ref_path:
        return rel_path

    dir_path = lib.dirname(rel_path)
    if not dir_path or dir_path == curdir or lib.isabs(ref_path):
        return ref_path

    drive, dir_path = lib.splitdrive(dir_path)
    dir_path_isabs = bool(drive or dir_path.startswith(sep))
    dir_parts = split(dir_path, sep, start=1)
    ref_parts = ref_path.split(sep)
    try:
        for i, p in enumerate(ref_parts):
            if p == curdir:
                continue
            elif p == pardir and dir_parts[-1] != pardir:
                if dir_parts.pop() == sep:
                    raise IndexError
            else:
                dir_parts.append(p)
        result_path = lib.join(drive, *dir_parts)
        if dir_path_isabs and not result_path.startswith(sep):
            return sep + result_path
        return result_path
    except IndexError:
        if dir_path_isabs:
            raise ValueError(
                f'{ref_path} relative to {rel_path} exceeded the root directory')
        return lib.join(*ref_parts[i:])


@overload
def replace_stem(fpath: bytes, stem: bytes, lib: Any = ...) -> bytes:
    ...
@overload
def replace_stem(fpath: str, stem: str, lib: Any = ...) -> str:
    ...
def replace_stem(fpath, stem, lib=path):
    '''Replace the stem component of the path `fpath` with the replacement `rep`.
    Note: stem is the final path component, without its suffix (file extension).

    :param fpath: The file path.
    :param stem: String to replace the stem of `fpath`.
    :sep: The character used to separate/join pathname components.

    :return: Return the string obtained by replacing the 
             stem component of `fpath` with `stem`.
    '''
    p_dir, p_name = lib.split(fpath)
    p_ext = lib.splitext(p_name)[1]
    return lib.join(p_dir, stem + p_ext)


@overload
def add_stem_preffix(fpath: bytes, preffix: bytes, lib: Any = ...) -> bytes:
    ...
@overload
def add_stem_preffix(fpath: str, preffix: str, lib: Any = ...) -> str:
    ...
def add_stem_preffix(fpath, preffix, lib=path):
    '''Append a string `preffix` at the start of the stem component of the path `fpath`.
    Note: stem is the final path component, without its suffix (file extension).

    :param fpath: The file path.
    :param preffix: The string will be append to left side of fpath's stem.
    :param lib: The path module used, can be selected in `ntpath` and `posixpath`.

    :return: Return the string obtained by appending `preffix` to left side 
             the stem component of `fpath`.
    '''
    base, name = lib.split(fpath)
    return lib.join(base, preffix + name)


@overload
def add_stem_suffix(fpath: bytes, preffix: bytes, lib: Any = ...) -> bytes:
    ...
@overload
def add_stem_suffix(fpath: str, preffix: str, lib: Any = ...) -> str:
    ...
def add_stem_suffix(fpath, suffix, lib=path):
    '''Append a string `suffix` at the end of the stem component of the path `fpath`.
    Note: stem is the final path component, without its suffix (file extension).

    :param fpath: The file path.
    :param suffix: The string will be append to fpath's stem.
    :param lib: The path module used, can be selected in `ntpath` and `posixpath`.

    :return: Return the string obtained by appending `suffix` to 
             the stem component of `fpath`.
    '''
    base, ext = lib.splitext(fpath)
    return base + suffix + ext


@overload
def iter_list_files(
    top: bytes, 
    use_fullname: bool = ..., 
    recursive: bool = ..., 
    lib: Any = ..., 
) -> Generator[bytes, None, None]:
    ...
@overload
def iter_list_files(
    top: str, 
    use_fullname: bool = ..., 
    recursive: bool = ..., 
    lib: Any = ..., 
) -> Generator[str, None, None]:
    ...
def iter_list_files(
    top='.', 
    use_fullname=True, 
    recursive=True, 
    lib=path, 
):
    '''Based on `os.listdir`, traversing the top directory (or even its subdirectories), 
    returning an iterator of files (not directories) in these directories.

    :param top: The top directory to be traversed.
    :param use_fullname: Use the full name (begin with '/' (UNIX-like) or Drive:/ (Windows)).
    :param recursive: If recursive is true (default), traverses subdirectories recursively.
    :param lib: The path module used, can be selected in `ntpath` and `posixpath`.

    :return: If the type of `top` is `bytes` or `Pathlike[bytes]`, then
                Generator[bytes, None, None] is returned,
             else if the type is `str` or `Pathlike[str]`, then
                Generator[str, None, None]] is returned.
    '''
    if use_fullname:
        top = lib.abspath(top)
    for name in listdir(top):
        pathname = lib.join(top, name)
        if lib.isdir(pathname) and recursive:
            yield from iter_list_files(
                pathname, use_fullname, recursive, lib)
        else:
            yield pathname if use_fullname else name


@overload
def iter_scan_files(
    top: bytes, 
    use_fullname: bool = ..., 
    recursive: bool = ..., 
    as_entry: bool = ..., 
    lib: Any = ..., 
) -> Union[Generator[DirEntry, None, None], Generator[bytes, None, None]]:
    ...
@overload
def iter_scan_files(
    top: str, 
    use_fullname: bool = ..., 
    recursive: bool = ..., 
    as_entry: bool = ..., 
    lib: Any = ..., 
) -> Union[Generator[DirEntry, None, None], Generator[str, None, None]]:
    ...
def iter_scan_files(
    top='.', 
    use_fullname=True, 
    recursive=True, 
    as_entry=False, 
    lib=path, 
):
    '''Based on `os.scandir`, traversing the top directory (or even its subdirectories), 
    returning an iterator of files (not directories) in these directories.

    :param top: The top directory to be traversed.
    :param use_fullname: Use the full name (begin with '/' (UNIX-like) or Drive:/ (Windows)).
    :param recursive: If recursive is true (default), traverses subdirectories recursively.
    :param as_entry: The returned generator, which yields os.DirEntry 
                     (neither bytes nor str) at each time.
    :param lib: The path module used, can be selected in `ntpath` and `posixpath`.

    :return: If `as_entry` is true, then
                Generator[os.DirEntry, None, None] is returned, 
             else if the type of `top` is `bytes` or `Pathlike[bytes]`, then
                Generator[bytes, None, None] is returned,
             else if the type is `str` or `Pathlike[str]`, then
                Generator[str, None, None]] is returned.
    '''
    if use_fullname:
        top = lib.abspath(top)
    with scandir(top) as it:
        for entry in it:
            if entry.is_dir() and recursive:
                yield from iter_scan_files(entry)
            elif as_entry:
                yield entry
            elif use_fullname:
                yield entry.path
            else:
                yield entry.name


@overload
def iter_walk_files(
    top: bytes, 
    use_fullname: bool = ..., 
    recursive: bool = ..., 
    lib: Any = ..., 
) -> Generator[bytes, None, None]:
    ...
@overload
def iter_walk_files(
    top: str, 
    use_fullname: bool = ..., 
    recursive: bool = ..., 
    lib: Any = ..., 
) -> Generator[str, None, None]:
    ...
def iter_walk_files(
    top='.', 
    use_fullname=True, 
    recursive=True, 
    lib=path, 
):
    '''Based on `os.walk`, traversing the top directory (or even its subdirectories), 
    returning an iterator of files (not directories) in these directories.

    :param top: The top directory to be traversed.
    :param use_fullname: Use the full name (begin with '/' (UNIX-like) or Drive:/ (Windows)).
    :param recursive: If recursive is true (default), traverses subdirectories recursively.
    :param lib: The path module used, can be selected in `ntpath` and `posixpath`.

    :return: If the type of `top` is `bytes` or `Pathlike[bytes]`, then
                Generator[bytes, None, None] is returned,
             else if the type is `str` or `Pathlike[str]`, then
                Generator[str, None, None]] is returned.
    '''
    if use_fullname:
        top = lib.abspath(top)
    if recursive:
        for dirpath, _, filelist in walk(top):
            if use_fullname:
                for fname in filelist:
                    yield lib.join(dirpath, fname)
            else:
                yield from filelist
    else:
        dirinfo = next(walk(top), None)
        if dirinfo is not None:
            dirpath, _, filelist = dirinfo
            if use_fullname:
                for fname in filelist:
                    yield lib.join(dirpath, fname)
            else:
                yield from filelist

