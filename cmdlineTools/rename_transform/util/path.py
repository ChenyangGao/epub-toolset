#! /usr/bin/env python3
# coding: utf-8

__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 2)
__all__ = ['get_fext', 'get_stem', 'split_components', 'split3', 'relative_path', 
           'replace_stem', 'add_stem_preffix', 'add_stem_suffix', 'iter_list_files', 
           'iter_scan_files', 'iter_walk_files']


from os import path
from os import fspath, listdir, scandir, walk, DirEntry, PathLike
from typing import cast, Any, AnyStr, Generator, List, Optional, Tuple, Union


PathType = Union[AnyStr, PathLike[AnyStr]]


def get_fext(
    fpath: PathType, 
    lib: Any = path, 
) -> AnyStr:
    'Return the file extension of the `fpath`, if any.'
    return lib.splitext(fpath)[1]


def get_stem(
    fpath: PathType, 
    lib: Any = path, 
) -> AnyStr:
    '''Return the stem component of the `fpath`.
    Note: stem is the final path component, without its suffix (file extension).
    '''
    return lib.dirname(lib.splitext(fpath)[0])


def split_components(
    fpath: PathType, 
    sep: Union[bytes, str] = '/', 
) -> Union[List[bytes], List[str]]:
    fpath = cast(Union[bytes, str], fspath(fpath))
    if isinstance(fpath, bytes):
        if isinstance(sep, str):
            sep = sep.encode()
        return fpath.split(cast(bytes, sep))
    else:
        if isinstance(sep, bytes):
            sep = sep.decode()
        return fpath.split(cast(str, sep))


def split3(
    fpath: PathType, 
    lib: Any = path, 
) -> Union[Tuple[bytes, bytes, bytes], Tuple[str, str, str]]:
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


def relative_path(
    ref_path: PathType, 
    rel_path: PathType = '.', 
    lib: Any = path, 
) -> AnyStr:
    'Relative to the directory of `rel_path`, return the path of `file_path`.'
    sep: AnyStr
    curdir: AnyStr
    ref_path = cast(AnyStr, fspath(ref_path))
    rel_path = cast(AnyStr, fspath(rel_path))

    if isinstance(ref_path, bytes):
        sep = cast(bytes, lib.sep.encode())
        curdir = cast(bytes, lib.curdir.encode())
        ref_path = cast(bytes, ref_path)
        if isinstance(rel_path, str):
            rel_path = rel_path.encode()
        rel_path = cast(bytes, rel_path)
    else:
        sep = cast(str, lib.sep)
        curdir = cast(str, lib.curdir)
        ref_path = cast(str, ref_path)
        if isinstance(rel_path, bytes):
            rel_path = rel_path.decode()
        rel_path = cast(str, rel_path)

    if not rel_path or rel_path == curdir or lib.isabs(ref_path):
        return ref_path

    if rel_path.endswith(sep):
        dir_path = rel_path[:-1]
    else:
        dir_path = lib.dirname(rel_path)

    if not ref_path.startswith(curdir):
        return lib.join(dir_path, ref_path)

    dir_parts = dir_path.split(sep)
    if not dir_parts[0]:
        dir_parts[0] = sep

    ref_parts = ref_path.split(sep)
    advance_count = 0
    for i, p in enumerate(ref_parts):
        if p and not p.strip(curdir):
            advance_count += len(p) - 1
            continue
        break
    else:
        i += 1

    ref_parts = ref_parts[i:]
    if advance_count:
        dir_parts = dir_parts[:-advance_count]

    return lib.join(*dir_parts, *ref_parts)


def replace_stem(
    fpath: PathType, 
    stem: AnyStr, 
    lib: Any = path, 
) -> AnyStr:
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


def add_stem_preffix(
    fpath: PathType, 
    preffix: AnyStr, 
    lib: Any = path, 
) -> AnyStr:
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


def add_stem_suffix(
    fpath: PathType, 
    suffix: AnyStr, 
    lib: Any = path, 
) -> AnyStr:
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


def iter_list_files(
    top: PathType = '.', 
    use_fullname: bool = True, 
    recursive: bool = True, 
    lib: Any = path, 
) -> Union[Generator[bytes, None, None], 
           Generator[str, None, None]]:
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


def iter_scan_files(
    top: PathType = '.', 
    use_fullname: bool = True, 
    recursive: bool = True, 
    as_entry: bool = False, 
    lib: Any = path, 
) -> Union[Generator[DirEntry, None, None], 
           Generator[bytes, None, None], 
           Generator[str, None, None]]:
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


def iter_walk_files(
    top: PathType = '.', 
    use_fullname: bool = True, 
    recursive: bool = True, 
    lib: Any = path, 
) -> Union[Generator[bytes, None, None], 
           Generator[str, None, None]]:
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

