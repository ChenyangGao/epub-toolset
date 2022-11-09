#!/usr/bin/env python
# coding: utf-8

__author__  = "ChenyangGao <https://chenyanggao.github.io/>"
__version__ = (0, 1, 1)
__all__ = ["watch"]

# TODO: 移动文件到其他文件夹，那么这个文件所引用的那些文件，相对位置也会改变
# TODO: created 事件时，文件不存在，则文件可能是被移动或删除，则应该注册一个回调，因为事件没有被正确处理
# TODO: 是否需要忽略那些所在的祖先目录也是隐藏（以'.'为前缀）的文件？
# TODO: 对于自己引用自己的，如果写出自己文件名的，要更新，但是如果路径是 ""，则忽略
# TODO: 应该专门写一个类，用来增删改查文件的引用和被引用关系，解除和 EpubFileEventHandler 的耦合
# TODO: 在 windows 下文件被占用时，因为 PermissionError 不可打开，是否需要等会再去尝试打开，以及尝试多少次？
# TODO: 新增多线程或协程处理机制，加快效率，以及防止主线程崩溃
# TODO: 对于某些需要同步的文件，由于它们是不规范的，导致崩溃，这时就要跳过

import logging
import os.path as syspath
import posixpath

from collections import defaultdict, Counter
from functools import partial
from os import stat, fsdecode
from os.path import basename, dirname, realpath, sep
from re import compile as re_compile, Pattern
from time import sleep
from typing import Callable, Final, Optional
from urllib.parse import quote, unquote, urlparse, urlunparse

from watchdog.events import ( # type: ignore
    FileDeletedEvent, FileCreatedEvent, FileModifiedEvent, FileSystemEventHandler
)
from watchdog.observers import Observer # type: ignore

from util.mimetype import guess_mimetype
from util.pathutils import reference_path, relative_path, path_posix_to_sys, path_to_posix
from util.opfwrapper import OpfWrapper


PROTECTED_FILES = ["META-INF/", "mimetype"]
MIMES_OF_TEXT = ("text/html", "application/xhtml+xml", "application/x-dtbncx+xml")
MIMES_OF_STYLES = ("text/css",)

#
CRE_PROT: Final[Pattern] = re_compile(r'^\w+://')
#
CRE_REF: Final[Pattern] = re_compile(
    r'(<[^/][^>]*?[\s:](?:href|src)=")(?P<link>[^>"]+)')
#
CRE_URL: Final[Pattern] = re_compile(
    r'\burl\(\s*(?:"(?P<dlink>(?:[^"]|(?<=\\)")+)"|'
    r'\'(?P<slink>(?:[^\']|(?<=\\)\')+)\'|(?P<link>[^)]+))\s*\)')
#
CRE_EL_STYLE: Final[Pattern] = re_compile(
    r'<style(?:\s[^>]*|)>((?s:.+?))</style>')
#
CRE_INLINE_STYLE: Final[Pattern] = re_compile(
    r'<[^/][^>]*?\sstyle="([^"]+)"')


# TODO: 使用策略模式，而不是像现在这样一大块
def analyze_one(bookpath, data, mime=None):
    """"""
    def gen_filtered_links(links):
        for link in links:
            link = unquote(link.partition('#')[0])
            if link in ('', '.') or CRE_PROT.match(link) is not None:
                continue
            ref_path = reference_path(bookpath, link, "/")
            yield ref_path
    if mime is None:
        mime = guess_mimetype(bookpath)
    if mime in MIMES_OF_STYLES:
        return Counter(gen_filtered_links(
            next(filter(None, m.groups())) 
            for m in CRE_URL.finditer(data)))
    elif mime in MIMES_OF_TEXT:
        return {
            'ref': Counter(gen_filtered_links(
                m['link'] 
                for m in CRE_REF.finditer(data))), 
            'inline': Counter(gen_filtered_links(
                next(filter(None, m.groups()))
                for m0 in CRE_INLINE_STYLE.finditer(data)
                for m in CRE_URL.finditer(m0[0]))), 
            'style': Counter(gen_filtered_links(
                next(filter(None, m.groups()))
                for m0 in CRE_EL_STYLE.finditer(data)
                for m in CRE_URL.finditer(m0[0]))), 
        }


def analyze(opfwrapper):
    """"""
    map_path_refset = {}
    map_ref_pathset = defaultdict(set)

    for fid, href, mime, *_ in opfwrapper.manifest_iter():
        if mime not in MIMES_OF_TEXT and mime not in MIMES_OF_STYLES:
            continue
        bookpath = opfwrapper.id_to_bookpath(fid)

        realpath = syspath.join(opfwrapper.ebook_root, path_posix_to_sys(bookpath))
        content = open(realpath, encoding="utf-8").read()
        result = analyze_one(bookpath, content, mime)
        map_path_refset[bookpath] = result
        if mime in MIMES_OF_STYLES:
            for ref_bookpath in result:
                map_ref_pathset[ref_bookpath].add(bookpath)
        elif mime in MIMES_OF_TEXT:
            for refset in result.values():
                for ref_bookpath in refset:
                    map_ref_pathset[ref_bookpath].add(bookpath)
    return map_path_refset, map_ref_pathset


class EpubFileEventHandler(FileSystemEventHandler):

    def __init__(
        self, 
        opfwrapper: OpfWrapper, 
        logger: logging.Logger = logging.getLogger("root"), 
        ignore: Optional[Callable[[str], bool]] = None, 
    ):
        super().__init__()

        self._opfwrapper: OpfWrapper = opfwrapper
        self.logger: logging.Logger = logger 
        self.ignore: Callable[[str], bool]
        if ignore is None:
            self.ignore = lambda bookpath: False
        else:
            def ignore_fn(bookpath: str) -> bool:
                if bookpath in opfwrapper.bookpath_to_id:
                    return False
                else:
                    return ignore(bookpath)
            self.ignore = ignore_fn

        self._bookpath_to_mtime: dict[str, int] = {
            bookpath: stat(opfwrapper.bookpath_to_path(bookpath)).st_mtime_ns
            for bookpath in opfwrapper.bookpath_to_id
        }

        # TODO: 可以优化
        self._map_path_refset, self._map_ref_pathset = analyze(opfwrapper)

    @property
    def opfwrapper(self) -> OpfWrapper:
        return self._opfwrapper

    def get_media_type(self, bookpath: str) -> str:
        try:
            id = self._opfwrapper.bookpath_to_id(bookpath)
            return self._opfwrapper.id_to_media_type(id)
        except KeyError:
            return guess_mimetype(bookpath) or "application/octet-stream"

    def _add_bookpath_ref(self, bookpath, mime=None):
        if mime is None:
            mime = self.get_media_type(bookpath)
        if mime in MIMES_OF_STYLES or mime in MIMES_OF_TEXT:
            try:
                realpath = self.get_path(bookpath)
                # TODO: 在 Windows 下，新增文件过快时，文件还没复制好，就已经去读了，就会报错 PermissionError
                content = open(realpath, encoding="utf-8").read()
            except FileNotFoundError:
                # TODO: The file may be deleted or moved, a callback should be registered here, 
                #       then called when the modified event is triggered
                return
            result = analyze_one(bookpath, content)
            if not result:
                return
            self._map_path_refset[bookpath] = result
            if mime in MIMES_OF_STYLES:
                for ref_bookpath in result:
                    self._map_ref_pathset[ref_bookpath].add(bookpath)
            elif mime in MIMES_OF_TEXT:
                for refset in result.values():
                    for ref_bookpath in refset:
                        self._map_ref_pathset[ref_bookpath].add(bookpath)

    def _del_bookpath_ref(self, bookpath, mime=None):
        if mime is None:
            mime = self.get_media_type(bookpath)
        if mime in MIMES_OF_STYLES:
            refset = self._map_path_refset.pop(bookpath, None)
            if refset:
                for ref in refset:
                    self._map_ref_pathset[ref].discard(bookpath)
        elif mime in MIMES_OF_TEXT:
            result = self._map_path_refset.pop(bookpath, None)
            if result:
                for refset in result.values():
                    for ref_bookpath in refset:
                        self._map_ref_pathset[ref_bookpath].discard(bookpath)

    def _update_refby_files(self, bookpath, dest_bookpath, ls_refby):
        if not ls_refby:
            return

        def rel_ref(src, ref):
            # NOTE: ca means common ancestors
            ca = posixpath.commonprefix((src, ref)).count('/')
            return '../' * (src.count('/') - ca) + '/'.join(ref.split('/')[ca:])

        def url_repl(m, refby):
            try:
                link = next(filter(None, m.groups()))
            except StopIteration:
                return m[0]

            urlparts = urlparse(link)
            link = unquote(urlparts.path)
            if link in ('', '.') or CRE_PROT.match(link) is not None:
                return m[0]

            if reference_path(refby, link, "/") == bookpath:
                return 'url("%s")' % urlunparse(urlparts._replace(
                    path=quote(rel_ref(refby, dest_bookpath))
                ))
            else:
                return m[0]

        def ref_repl(m, refby):
            link = m['link']
            urlparts = urlparse(link)
            link = unquote(urlparts.path)
            if link in ('', '.') or CRE_PROT.match(link) is not None:
                return m[0]
            if reference_path(refby, link, "/") == bookpath:
                return m[1] + urlunparse(urlparts._replace(
                    path=quote(rel_ref(refby, dest_bookpath))
                ))
            else:
                return m[0]

        def sub_url_in_hxml(text, refby, cre=CRE_EL_STYLE):
            ls_repl_part = []
            for match in cre.finditer(text):
                repl_part, n = CRE_URL.subn(partial(url_repl, refby=refby), match[0])
                if n > 0:
                    ls_repl_part.append((match.span(), repl_part))
            if ls_repl_part:
                text_parts = []
                last_stop = 0
                for (start, stop), repl_part in ls_repl_part:
                    text_parts.append(text[last_stop:start])
                    text_parts.append(repl_part)
                    last_stop = stop
                else:
                    text_parts.append(text[last_stop:])
                return ''.join(text_parts)
            return text

        for refby in ls_refby:
            if type(refby) is str:
                if refby == bookpath:
                    refby = dest_bookpath
                refby_srcpath = self.get_path(refby)
                try:
                    if stat(refby_srcpath).st_mtime_ns != self._bookpath_to_mtime[refby_srcpath]:
                        self.logger.error(
                            'Automatic update reference %r -> %r was skipped, '
                            'because the file %r has been modified', 
                            bookpath, dest_bookpath, refby_srcpath
                        )
                        continue
                    content = open(refby_srcpath).read()
                except FileNotFoundError:
                    # NOTE: The file may have been moved or deleted
                    def callback(refby, refby_srcpath, types=None):
                        try:
                            if stat(refby_srcpath).st_mtime_ns != self._bookpath_to_mtime[refby_srcpath]:
                                self.logger.error(
                                    'Automatic update reference %r -> %r was skipped, '
                                    'because the file %r has been modified', 
                                    bookpath, dest_bookpath, refby_srcpath
                                )
                                return
                            content = open(refby_srcpath).read()
                        except FileNotFoundError:
                            self.logger.error(
                                'Automatic update reference %r -> %r was skipped, '
                                'because the file %r disappeared', 
                                bookpath, dest_bookpath, refby_srcpath
                            )
                            return
                        content = CRE_URL.sub(partial(url_repl, refby=refby), content)
                        open(refby_srcpath, 'w').write(content)
                        self.on_modified(FileModifiedEvent(refby_srcpath))

                    continue
                content = CRE_URL.sub(partial(url_repl, refby=refby), content)
            else:
                refby, types = refby
                if refby == bookpath:
                    refby = dest_bookpath
                refby_srcpath = self._watchdir + path_posix_to_sys(refby)
                try:
                    if stat(refby_srcpath).st_mtime_ns != self._bookpath_to_mtime[refby_srcpath]:
                        self.logger.error(
                            'Automatic update reference %r -> %r was skipped, '
                            'because the file %r has been modified', 
                            bookpath, dest_bookpath, refby_srcpath
                        )
                        continue
                    content = open(refby_srcpath).read()
                except FileNotFoundError:
                    # NOTE: The file may have been moved or deleted
                    def callback(refby, refby_srcpath, types=types):
                        try:
                            if stat(refby_srcpath).st_mtime_ns != self._bookpath_to_mtime[refby_srcpath]:
                                self.logger.error(
                                    'Automatic update reference %r -> %r was skipped, '
                                    'because the file %r has been modified', 
                                    bookpath, dest_bookpath, refby_srcpath
                                )
                                return
                            content = open(refby_srcpath).read()
                        except FileNotFoundError:
                            self.logger.error(
                                'Automatic update reference %r -> %r was skipped, '
                                'because the file %r disappeared', 
                                bookpath, dest_bookpath, refby_srcpath
                            )
                            return
                        for tp in types:
                            if tp == 'ref':
                                content = CRE_REF.sub(partial(ref_repl, refby=refby), content)
                            elif tp == 'inline':
                                content = sub_url_in_hxml(content, refby, CRE_INLINE_STYLE)
                            elif tp == 'style':
                                content = sub_url_in_hxml(content, refby, CRE_EL_STYLE)
                        open(refby_srcpath, 'w').write(content)
                        self.on_modified(FileModifiedEvent(refby_srcpath))

                    continue
                for tp in types:
                    if tp == 'ref':
                        content = CRE_REF.sub(partial(ref_repl, refby=refby), content)
                    elif tp == 'inline':
                        content = sub_url_in_hxml(content, refby, CRE_INLINE_STYLE)
                    elif tp == 'style':
                        content = sub_url_in_hxml(content, refby, CRE_EL_STYLE)
            open(refby_srcpath, 'w').write(content)
            self.on_modified(FileModifiedEvent(refby_srcpath))

    def on_created(self, event):
        if event.is_directory:
            self.logger.debug(
                "Ignored created event, because it is a directory: %r" % event.src_path)
            return

        opfwrapper = self._opfwrapper
        path = realpath(event.src_path)
        bookpath = opfwrapper.path_to_bookpath(path)

        if bookpath in opfwrapper.bookpath_to_id:
            self.on_deleted(FileDeletedEvent(path))

        if self.ignore(bookpath):
            self.logger.debug(
                "Ignored created event, because it is specified to be ignored: %r" % path)
            return

        try:
            self._bookpath_to_mtime[bookpath] = stat(path).st_mtime_ns
        except FileNotFoundError:
            self.logger.debug(
                "Ignored created event, maybe it was deleted or moved: %r" % path)
            return

        media_type = guess_mimetype(bookpath) or "application/octet-stream"
        if media_type in MIMES_OF_TEXT or media_type in MIMES_OF_STYLES:
            try:
                self._add_bookpath_ref(bookpath, media_type)
            except FileNotFoundError:
                self.logger.debug(
                    "Ignored created event, maybe it was deleted or "
                    "moved during processing: %r" % path)
                return
            except UnicodeDecodeError:
                self.logger.debug(
                    "Ignored created event, because it is a referencing file, "
                    "but cannot be parsed: %r" % path)
                return

        opfwrapper.add(bookpath=bookpath)
        self.logger.info("Created file: %r" % path)

    def on_deleted(self, event):
        opfwrapper = self._opfwrapper
        path = realpath(event.src_path)
        bookpath = opfwrapper.path_to_bookpath(path)
        logger = self.logger

        def delete(bookpath):
            item = opfwrapper.delete(bookpath=bookpath)
            self._del_bookpath_ref(bookpath, item.mimetype)
            self._bookpath_to_mtime.pop(bookpath, None)
            logger.info("Deleted file: %r" % opfwrapper.bookpath_to_path(bookpath))

        if event.is_directory:
            bookpath += '/'
            for subbookpath in tuple(opfwrapper.bookpath_to_id):
                if subbookpath.startswith(bookpath):
                    delete(subbookpath)
        elif bookpath in opfwrapper.bookpath_to_id:
            delete(bookpath)

    def on_modified(self, event):
        # NOTE: When a file is modified, two modified events will be triggered, 
        #       the first is truncation, and the second is writing.
        if event.is_directory:
            self.logger.debug(
                "Ignored modified event, because it is a directory: %r" % event.src_path)
            return

        opfwrapper = self._opfwrapper
        path = realpath(event.src_path)
        bookpath = opfwrapper.path_to_bookpath(path)

        if bookpath not in opfwrapper.bookpath_to_id:
            self.logger.debug(
                "Ignored modified event, because it is not in the opf file: %r" % path)
            return

        try:
            mtime = stat(path).st_mtime_ns
        except FileNotFoundError:
            self.logger.debug(
                "Ignored modified event, maybe it was deleted or moved: %r" % path)
        else:
            if self._bookpath_to_mtime.get(src_path) == mtime:
                self.logger.debug(
                    "Ignored modified event, because its mtime has not changed: %r" % path)
                return

        self._del_bookpath_ref(bookpath)
        self._add_bookpath_ref(bookpath)
        self.logger.info("Modified file: %r", path)

    def on_moved(self, event):
        if event.is_directory:
            self.logger.debug(
                "Ignored moved event, because it is a directory: %r" % event.src_path)
            return

        opfwrapper = self._opfwrapper
        src_path, dest_path = realpath(event.src_path), realpath(event.dest_path)
        src_bookpath = opfwrapper.path_to_bookpath(src_path)
        dest_bookpath = opfwrapper.path_to_bookpath(dest_path)

        if dest_bookpath in opfwrapper.bookpath_to_id:
            self.on_deleted(dest_path)

        src_is_ignored = src_bookpath not in opfwrapper.bookpath_to_id and self.ignore(src_bookpath) 
        dest_is_ignored = self.ignore(dest_bookpath)
        if src_is_ignored:
            if not dest_is_ignored:
                self.logger.debug(
                    "Switch moved event to created event: %r -> %r" % (src_path, dest_path))
                self.on_created(FileCreatedEvent(dest_path))
        elif dest_is_ignored:
            self.logger.debug(
                "Switch moved event to deleted event: %r -> %r" % (src_path, dest_path))
            self.on_deleted(FileDeletedEvent(src_path))
        # TODO:
        elif src_bookpath not in self._opfwrapper.bookpath_to_id:
            self.logger.debug(
                "Ignored moved event, because file has already been moved: %r" 
                    % src_bookpath)
        else:
            if posixpath.splitext(src_bookpath)[1] == posixpath.splitext(dest_bookpath)[1]:
                opfwrapper = self._opfwrapper
                oldpath = src_bookpath
                newpath = dest_bookpath
                fid = opfwrapper.bookpath_to_id(oldpath)
                oldhref = opfwrapper.id_to_href(fid)
                newhref = relative_path(opfwrapper.opf_bookpath, newpath, "/")

                opfwrapper.bookpath_to_id.pop(oldpath, None)
                opfwrapper.href_to_id.pop(oldhref, None)
                opfwrapper.id_to_bookpath[fid] = newpath
                opfwrapper.href_to_id[newhref] = fid
                opfwrapper.bookpath_to_id[newpath] = fid
            else:
                self._opfwrapper.delete(bookpath=src_bookpath)
                self._opfwrapper.add(bookpath=dest_bookpath)

            # TODO: 下面这一大段，过于混乱，需要重构
            old_mtime = self._bookpath_to_mtime[src_path]
            self._bookpath_to_mtime[dest_path] = old_mtime
            # 各个文件引用多少其它文件及次数
            map_path_refset = self._map_path_refset
            # 各个文件被那些文件引用
            map_ref_pathset = self._map_ref_pathset
            # 我被哪些文件所引用
            pathset = map_ref_pathset.get(src_bookpath)
            # 我被哪些文件所引用，以及引用的方式
            ls_refby = []
            # map_ref_pathset[src_bookpath] -> map_ref_pathset[dest_bookpath]
            if pathset is not None:
                map_ref_pathset[dest_bookpath] = map_ref_pathset.pop(src_bookpath)
                for p in pathset:
                    result = map_path_refset[p]
                    if type(result) is dict:
                        ls_refby.append(
                            (p, [key for key, val in result.items() if src_bookpath in val]))
                    else:
                        ls_refby.append(p)
            # 我引用的文件
            refs = map_path_refset[src_bookpath]
            # src_bookpath in map_ref_pathset[*] -> dest_bookpath in map_ref_pathset[*]
            if type(refs) is dict:
                for refs2 in refs.values():
                    for ref in refs2:
                        map_ref_pathset[ref].discard(src_bookpath)
                        map_ref_pathset[ref].add(dest_bookpath)
            else:
                for ref in refs:
                    map_ref_pathset[ref].discard(src_bookpath)
                    map_ref_pathset[ref].add(dest_bookpath)

            result = map_path_refset.get(src_bookpath)
            self._del_bookpath_ref(src_bookpath)
            old_mime = self.get_media_type(src_bookpath)
            mime = self.get_media_type(dest_bookpath)
            if result is not None and old_mime == mime:
                map_path_refset[dest_bookpath] = result
                if mime in MIMES_OF_TEXT:
                    for ref_bookpath in result:
                        map_ref_pathset[ref_bookpath].add(dest_bookpath)
                else:
                    for refset in result.values():
                        for ref_bookpath in refset:
                            map_ref_pathset[ref_bookpath].add(dest_bookpath)
            else:
                self._add_bookpath_ref(dest_bookpath, mime)

            self.logger.info(
                "Moved file: from %s to %s", src_bookpath, dest_bookpath)
            self._update_refby_files(src_bookpath, dest_bookpath, ls_refby)


def watch(
    watchdir, 
    opfwrapper=None, 
    logger=logging, 
    ignore=None, 
):
    "Monitor all events of an epub editing directory, and maintain opf continuously."
    # watchdir = fsdecode(watchdir)
    if opfwrapper is None:
        opfwrapper = OpfWrapper(watchdir)
    observer = Observer()
    event_handler = EpubFileEventHandler(
        watchdir, opfwrapper=opfwrapper, logger=logger, ignore=ignore)
    observer.schedule(event_handler, watchdir, recursive=True)
    logger.info("Watching directory: %r" % watchdir)
    observer.start()
    try:
        while True:
            sleep(0.1)
    except KeyboardInterrupt:
        logger.info('Shutting down watching ...')
        opfwrapper.dump()
    finally:
        observer.stop()
        observer.join()
    logger.info('Done!')

