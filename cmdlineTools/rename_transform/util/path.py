from os import path, listdir, scandir, walk, PathLike
from typing import Generator, Tuple, Union


__all__ = ['get_fext', 'splitpath', 'replace_stem', 'add_stem_suffix', 
           'iter_list_files', 'iter_scan_files', 'iter_walk_files']


def get_fext(fpath: Union[str, PathLike]) -> str:
    'Return the file extension of the `fpath`, if any.'
    return path.splitext(fpath)[1]


def splitpath(fpath: Union[str, PathLike]) -> Tuple[str, str, str]:
    '''Split the path `fpath` into a tuple (dirpath, barename, extension).
    Where
        dirpath: everything leading up to the last pathname component (basename).
        barename: the last pathname component (basename) without extension.
        extension: the extension of the last pathname component (basename), if any.
    Note: extension is empty or begins with a period (.) and contains at most one period.
    '''
    dirpath, filename = path.split(fpath)
    barename, extension = path.splitext(filename)
    return dirpath, barename, extension


def replace_stem(
    fpath: Union[str, PathLike], 
    rep: str, 
    sep: str = __import__('os').sep,
) -> str:
    '''Replace the stem component of the path `fpath` with the replacement `rep`.
    Note: stem is the final path component, without its suffix (file extension).

    :param fpath: The file path
    :param rep: The replacement
    :sep: The character used to separate/join pathname components.

    :return: Return the string obtained by replacing the stem component of `fpath` with `rep`.
    '''
    p_dir, p_name = path.split(fpath)
    _, p_ext = path.splitext(p_name)
    p_name = rep + p_ext
    if p_dir == '':
        return p_name
    elif p_dir in ('/', '\\'):
        return p_dir + p_name
    else:
        return p_dir + sep + p_name


def add_stem_suffix(
    fpath: Union[str, PathLike], 
    suffix: str,
) -> str:
    '''Append a string `suffix` at the end of the stem component of the path `fpath`.
    Note: stem is the final path component, without its suffix (file extension).

    :param fpath: The file path
    :param suffix: The string will be append to fpath's stem

    :return: Return the string obtained by appending `suffix` to the stem component of `fpath`.
    '''
    base, ext = path.splitext(fpath)
    return base + suffix + ext


def iter_list_files(
    top: Union[str, PathLike], 
    recursive: bool = True,
) -> Generator:
    '''
    '''
    for name in listdir(top):
        pathname = path.join(top, name)
        if recursive and path.isdir(pathname):
            yield from iter_list_files(pathname)
        else:
            yield pathname


def iter_scan_files(
    top: Union[str, PathLike], 
    asentry: bool = False, 
    recursive: bool = True
) -> Generator:
    '''
    '''
    with scandir(top) as it:
        for entry in it:
            if recursive and entry.is_dir():
                yield from iter_scan_files(entry)
            elif asentry:
                yield entry
            else:
                yield entry.path


def iter_walk_files(
    top: Union[str, PathLike], 
    joindir: bool = True,
) -> Generator:
    '''
    '''
    for dirpath, _, filelist in walk(top):
        if joindir:
            for fname in filelist:
                yield path.join(dirpath, fname)
        else:
            yield from filelist

