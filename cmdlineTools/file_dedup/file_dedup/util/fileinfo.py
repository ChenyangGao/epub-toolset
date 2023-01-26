#!/usr/bin/env python3
# coding: utf-8

__author__ = "ChenyangGao <https://chenyanggao.github.io/>"
__version__ = (0, 0, 3)
__all__ = ["FileInfo"]

from hashlib import algorithms_available
from os import fsdecode, stat, stat_result, DirEntry, PathLike
from os.path import basename, dirname, isdir, isfile, splitext
from pathlib import Path
from typing import (
    Any, AnyStr, Callable, Generator, Iterable, Type, TypeVar
)

if __name__ == "__main__":
    from argparse import ArgumentParser, RawTextHelpFormatter
    from hashlib import algorithms_available
    from os import stat_result
    from sys import argv, stdin

    parts_available = {"dir", "name", "stem", "ext"}
    stats_available = {f.removeprefix("st_") for f in dir(stat_result) if f.startswith("st_")}

    parser = ArgumentParser(
        description="遍历文件夹获取文件信息", 
        epilog="""🤔 说明：

如果想要扫描 test 文件夹，过滤掉名字以 . 开头的文件或文件夹，输出信息 path（路径）、size（大小）、md5，并且将结果输出到 output.json，则可写作

    python fileinfo.py test -i '.*' -p name -s size -a md5 -o output.json

支持管道，即支持读取另一个程序的输出作为输入，例如可以使用 find 命令，搜索出当前工作目录下所有文件名不以 . 开头的文件

    find . \( ! -name '.*' \) -type f | python fileinfo.py
""", formatter_class=RawTextHelpFormatter)
    parser.add_argument(
        "paths", metavar="path", nargs="*", help="路径列表，如有多个请用空格隔开")
    parser.add_argument(
        "-p", "--parts", metavar="part", nargs="+", choices=parts_available, default=(), 
        help=f"罗列文件路径的某些部分，目前可选：\n{parts_available}")
    parser.add_argument(
        "-s", "--stats", metavar="stat", nargs="+", choices=stats_available, default=(), 
        help=f"罗列文件状态的某些部分，目前可选：\n{stats_available}")
    parser.add_argument(
        "-a", "--algnames", metavar="algname", nargs="+", choices=algorithms_available, default=(), 
        help=f"指定所用的 hash 算法，目前可选：\n{algorithms_available}")
    parser.add_argument(
        "-i", "--ignore-names", metavar="ignored-name", dest="ignore_names", nargs="+", default=(), 
        help="需要过滤掉的文件夹和文件的名字，具体实现会使用 fnmatch （不区分大小写）")
    parser.add_argument(
        "-o", "--outpath", help="""输出的文件路径，允许以下扩展名：
    未指定: 等同于 .txt 但是输出到终端的 stdout
    .txt: text file (utf-8 encoded, each line is a JSON object)
    .json: JSON file (utf-8 encoded)
    .csv: CSV file (utf-8 encoded)
    .pkl: pickle file (binary, list of dictionaries)
""")
    parser.add_argument("-f", "--followlinks", action="store_true", 
        help="跟进链接（Unix-like）或快捷方式（Windows）")

    args = parser.parse_args()
    if not args.paths and stdin.isatty():
        parser.parse_args(["-h"])

    from filehash import filehash, mfilehash # type: ignore
    from iterpath import path_iter, path_walk # type: ignore
    from lazyproperty import lazyproperty # type: ignore
else:
    from util.filehash import filehash
    from util.iterpath import path_iter, path_walk
    from util.lazyproperty import lazyproperty


T = TypeVar("T", bound="FileInfo")


class FileInfo:
    """
    """
    def __init__(
        self, /, 
        path: bytes | str | PathLike, 
    ):
        if isdir(path):
            raise IsADirectoryError(path)
        self.path: str = fsdecode(path)

    @lazyproperty
    def dir(self, /) -> str:
        return dirname(self.path)

    @lazyproperty
    def name(self, /) -> str:
        return basename(self.path)

    @lazyproperty
    def stem(self, /) -> str:
        return splitext(basename(self.path))[1]

    @lazyproperty
    def ext(self, /) -> str:
        return splitext(self.path)[1]

    @property
    def stat(self, /) -> stat_result:
        return stat(self.path)

    def hash(self, /, algname: str = "md5") -> str:
        attrname = algname.replace("-", "_")
        try:
            return self.__dict__[attrname]
        except:
            value = self.__dict__[attrname] = filehash(self.path, algname)
            return value
        raise ValueError(f"Hash algorithm name unavailable: {algname!r}")

    def __eq__(self, other):
        if type(self) is type(other):
            return self.path == other.path
        return False

    def __hash__(self):
        return hash(self.path)

    def __fspath__(self):
        return self.path

    def __repr__(self) -> str:
        modname = type(self).__module__
        if modname == "__main__":
            return f"{type(self).__qualname__}({self.path!r})"
        else:
            return f"{modname}.{type(self).__qualname__}({self.path!r})"

    def __getattr__(self, name: str, /):
        if name in algorithms_available:
            return self.hash(name)
        if "_" in name:
            name2 = name.replace("_", "-")
            if name2 in algorithms_available:
                return self.hash(name2)
        raise AttributeError(name)

    def __setattr__(self, name: str, value, /):
        if name in self.__dict__:
            raise AttributeError(f"Property {name!r} can only be set once")
        self.__dict__[name] = value

    @classmethod
    def iter(
        cls: Type[T], /, 
        path: AnyStr | PathLike[AnyStr] = ".", # type: ignore
        followlinks: bool = True, 
        filterfn: None | Callable[[Path], bool] = None, 
        skiperror: None | Callable[[BaseException], Any] | BaseException | tuple[BaseException] = None, 
        depth_first: bool = False, 
        lazy: bool = True, 
    ) -> Generator[T, None, None]:
        """
        """
        if not isdir(path):
            if isfile(path):
                return (yield cls(path))
            raise NotADirectoryError(path)
        paths = path_iter(
            path, 
            followlinks=followlinks, 
            filterfn=filterfn, 
            skiperror=skiperror, 
            depth_first=depth_first, 
            lazy=lazy, 
        )
        for p in filter(Path.is_file, paths):
            try:
                yield cls(p)
            except KeyboardInterrupt:
                raise
            except BaseException as exc:
                if (skiperror and callable(exc) and skiperror(exc) # type: ignore
                        or not isinstance(exc, skiperror)): # type: ignore
                    raise

    @classmethod
    def walk(
        cls: Type[T], /, 
        path: AnyStr | PathLike[AnyStr] = ".", # type: ignore
        followlinks: bool = True, 
        onerror: None | Callable[[BaseException], Any] = None, 
        topdown: bool = True, 
        filterfn: None | Callable[[AnyStr], bool] = None, 
        filter_by_name: bool = False, 
    ) -> Generator[T, None, None]:
        """
        """
        if not isdir(path):
            if isfile(path):
                return (yield cls(path))
            raise NotADirectoryError(path)
        paths = path_walk(
            path, 
            followlinks=followlinks, 
            onerror=onerror, 
            topdown=topdown, 
            filterfn=filterfn, 
            filter_by_name=filter_by_name, 
            only_files=True, 
        )
        for p in paths:
            try:
                yield cls(p)
            except KeyboardInterrupt:
                raise
            except BaseException as exc:
                if onerror and onerror(exc):
                    raise


if __name__ == "__main__":
    from fnmatch import fnmatch
    from itertools import chain
    from os import remove
    from os.path import realpath
    from sys import stderr

    def filter_names(ignore_pats):
        if not ignore_pats:
            return None
        return lambda p: not any(fnmatch(basename(p), pat) for pat in ignore_pats)

    def stdout_writer(path, fields):
        from json import dumps
        from sys import stdout
        write = stdout.write
        while True:
            row = yield
            if type(row) is dict:
                write(dumps(row, ensure_ascii=False))
            else:
                write(dumps(dict(zip(fields, row)), ensure_ascii=False))
            write("\n")

    def text_writer(path, fields):
        from json import dumps
        try:
            with open(path, "w", encoding="utf-8") as textfile:
                write = textfile.write
                while True:
                    row = yield
                    if type(row) is dict:
                        write(dumps(row, ensure_ascii=False))
                    else:
                        write(dumps(dict(zip(fields, row)), ensure_ascii=False))
                    write("\n")
        except GeneratorExit:
            pass
        except BaseException:
            try:
                remove(path)
            except OSError:
                pass
            raise

    def csv_writer(path, fields):
        import csv
        try:
            with open(path, "w", encoding="utf-8_sig") as csvfile:
                writer = csv.writer(csvfile)
                write = writer.writerow
                write(fields)
                while True:
                    row = yield
                    if type(row) is dict:
                        write(row.get(f, '') for f in fields)
                    else:
                        write(row)
        except GeneratorExit:
            pass
        except BaseException:
            try:
                remove(path)
            except OSError:
                pass
            raise

    def json_writer(path, fields):
        from json import dump
        ls = []
        write = ls.append
        try:
            while True:
                row = yield
                if type(row) is dict:
                    write(row)
                else:
                    write(dict(zip(fields, row)))
        except GeneratorExit:
            dump(ls, open(path, "w", encoding="utf-8"), ensure_ascii=False)

    def pickle_writer(path, fields):
        from pickle import dump
        ls = []
        write = ls.append
        try:
            while True:
                row = yield
                if type(row) is dict:
                    write(row)
                else:
                    write(dict(zip(fields, row)))
        except GeneratorExit:
            dump(ls, open(path, "wb"))

    def choose_writer(path, fields):
        if path is None:
            writer = stdout_writer(path, fields)
        else:
            _, ext = splitext(path)
            if ext == ".txt":
                writer = text_writer(path, fields)
            elif ext == ".json":
                writer = json_writer(path, fields)
            elif ext == ".csv":
                writer = csv_writer(path, fields)
            elif ext == ".pkl":
                writer = pickle_writer(path, fields)
            else:
                raise NotImplementedError(ext)
        next(writer)
        return writer

    paths: Iterable = args.paths
    if not stdin.isatty():
        chain((p for p in (p.removesuffix("\n") for p in stdin) if p), paths)
    parts = args.parts
    stats = args.stats
    algnames = args.algnames
    ignore_names = args.ignore_names
    outpath = args.outpath
    followlinks = args.followlinks

    fields = ["path", *parts, *stats, *algnames]
    if stats:
        stats_full = ["st_" + s for s in stats]
    writer = choose_writer(outpath, fields)
    write = writer.send
    write_err = stderr.write
    filterfn = filter_names(ignore_names)
    try:
        for path in paths:
            if filterfn and not filterfn(basename(path)):
                continue
            for fi in FileInfo.iter(path, filterfn=filterfn, followlinks=followlinks):
                rpath = realpath(fi)
                info = {"path": rpath}
                if parts:
                    info.update((p, getattr(fi, p)) for p in parts)
                if stats:
                    fstat = fi.stat
                    info.update((f, getattr(fstat, s)) for f, s in zip(stats, stats_full))
                if algnames:
                    info.update(mfilehash(rpath, algnames))
                try:
                    write(info)
                except OSError as exc:
                    write_err("# FAILED %r\n" % rpath)
                    write_err("#     |_ %r\n" % exc)
    finally:
        writer.close()

