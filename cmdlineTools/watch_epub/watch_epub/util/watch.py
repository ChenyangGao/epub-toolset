#!/usr/bin/env python
# coding: utf-8

__author__  = "ChenyangGao <https://chenyanggao.github.io/>"
__version__ = (0, 1, 3)
__all__ = ["watch"]

# TODO: 移动文件到其他文件夹，那么这个文件所引用的那些文件，相对位置也会改变
# TODO: 在 windows 下文件被占用时，因为 PermissionError 不可打开，是否需要等会再去尝试打开，以及尝试多少次？
# TODO: 新增多线程或协程处理机制，加快效率，以及防止主线程崩溃
# TODO: 对于某些需要同步的文件，由于它们是不规范的，导致崩溃，这时就要跳过
# TODO: 判断文件是否改变：文件没变 <=> stat.st_mtime_ns没变 或 stat.st_size和md5没变
# TODO: 处理文件时，如果发现文件变了（和维护的最新信息不同），则需要先 analyse，如果分析后，得出处理还要继续才继续

import logging
import os.path as syspath
import posixpath

from collections import defaultdict, Counter
from functools import partial
from html import escape, unescape
from os import stat, fsdecode
from os.path import realpath
from re import compile as re_compile, Pattern
from time import sleep
from typing import Callable, Final, Optional
from urllib.parse import quote, unquote, urlparse, urlunparse

from watchdog.events import ( # type: ignore
    FileDeletedEvent, FileCreatedEvent, FileModifiedEvent, FileSystemEventHandler
)
from watchdog.observers import Observer # type: ignore

from util.mimetype import guess_mimetype
from util.pathutils import reference_path, path_posix_to_sys
from util.opfwrapper import OpfWrapper


# Match src or href attribute in xml/html/xhtml
CRE_REF: Final[Pattern] = re_compile(
    r'(<[^/][^>]*?[\s:](?:href|src)=")(?P<link>[^>"]+)')
# Match url function in css text
CRE_URL: Final[Pattern] = re_compile(
    r'\burl\(\s*(?:"(?P<dlink>(?:[^"]|(?<=\\)")+)"|'
    r'\'(?P<slink>(?:[^\']|(?<=\\)\')+)\'|(?P<link>[^)]+))\s*\)')
# Match <style> element in html/xhtml
CRE_EL_STYLE: Final[Pattern] = re_compile(r"<style\b[^>]*>(?P<text>[\s\S]+?)</style>")
# Match style attribute in html/xhtml
CRE_INLINE_STYLE: Final[Pattern] = re_compile(r'<[^/>][^>]*?\sstyle="(?P<attr>[^"]+)"')


MIME_REGISTRY = {}
UPDATE_REGISTRY = {}


def mime_register(*media_types):
    """"""
    def register(fn):
        for mime in media_types:
            MIME_REGISTRY[mime] = fn
        return fn
    return register


def updater_register(*op_types):
    """"""
    def register(fn):
        for op in op_types:
            UPDATE_REGISTRY[op] = fn
        return fn
    return register


def analyze(bookpath, text, mime=None):
    """"""
    if mime is None:
        mime = guess_mimetype(bookpath)
    handler = MIME_REGISTRY[mime]
    return handler(bookpath, text)


def update(text, src_bookpath, dest_bookpath, refby_bookpath, typelist):
    """"""
    for type_, *_ in typelist:
        text = UPDATE_REGISTRY[type_](
            text, src_bookpath, dest_bookpath, refby_bookpath)
    return text


def fileter_localpath(bookpath, hrefs):
    """"""
    for href in hrefs:
        phref = urlparse(href)
        if phref.scheme or phref.path in ("", "."):
            continue
        yield reference_path(bookpath, phref.path, "/")


@mime_register("text/css")
def analyze_css(bookpath, text):
    """"""
    return {
        "css": Counter(fileter_localpath(
            bookpath, (
                unquote(m[m.lastgroup])
                for m in CRE_URL.finditer(text)
            )
        )), 
    }


@mime_register("text/html", "application/xhtml+xml")
def analyze_html(bookpath, text):
    """"""
    return {
        "attr_href_src": Counter(fileter_localpath(
            bookpath, (
                unquote(m["link"])
                for m in CRE_REF.finditer(text)
            )
        )), 
        "attr_style": Counter(fileter_localpath(
            bookpath, (
                m[m.lastgroup]
                for m0 in CRE_INLINE_STYLE.finditer(text)
                for m in CRE_URL.finditer(unquote(m0["attr"]))
            )
        )), 
        "el_style": Counter(fileter_localpath(
            bookpath, (
                unquote(m[m.lastgroup])
                for m0 in CRE_EL_STYLE.finditer(text)
                for m in CRE_URL.finditer(unescape(m0["text"]))
            )
        )), 
    }


@mime_register("application/x-dtbncx+xml")
def analyze_ncx(bookpath, text):
    """"""
    return {
        "attr_href_src": Counter(fileter_localpath(
            bookpath, (
                unquote(m["link"])
                for m in CRE_REF.finditer(text)
            )
        )), 
    }


@updater_register("css")
def update_css(text, src_bookpath, dest_bookpath, refby_bookpath):
    def repl(m):
        href = unquote(m[m.lastgroup])
        phref = urlparse(href)
        if phref.scheme or phref.path in ("", "."):
            return m[0]
        if reference_path(src_bookpath, phref.path, "/") == src_bookpath:
            return "url('%s')" % quote(
                urlunparse(phref._replace(path=relpath)), ":/#")
        else:
            return m[0]

    relpath = posixpath.relpath(dest_bookpath, posixpath.dirname(refby_bookpath))
    return CRE_URL.sub(repl, text)


@updater_register("attr_href_src")
def update_attr_href_src(text, src_bookpath, dest_bookpath, refby_bookpath):
    def repl(m):
        text = m[0]
        href = unquote(m["link"])
        phref = urlparse(href)
        if phref.scheme or phref.path in ("", "."):
            return text
        if reference_path(src_bookpath, phref.path, "/") == src_bookpath:
            start = m.start()
            begin = m.start("link")
            return text[:begin-start] + quote(urlunparse(phref._replace(path=relpath)), ":/#")
        else:
            return text

    relpath = posixpath.relpath(dest_bookpath, posixpath.dirname(refby_bookpath))
    return CRE_REF.sub(repl, text)


@updater_register("attr_style")
def update_attr_style(text, src_bookpath, dest_bookpath, refby_bookpath):
    def repl(m):
        text = m[0]
        text_attr = m["attr"]
        text_attr_new = quote(CRE_URL.sub(sub_repl, unquote(text_attr)), ":/#")
        if text_attr == text_attr_new:
            return text
        else:
            start, stop = m.span()
            begin, end = m.span("attr")
            text_new = text[:begin-start] + text_attr_new
            if end < stop:
                text_new += text[end-stop:]
            return text_new

    def sub_repl(m):
        href = m[m.lastgroup]
        phref = urlparse(href)
        if phref.scheme or phref.path in ("", "."):
            return m[0]
        if reference_path(src_bookpath, phref.path, "/") == src_bookpath:
            return "url('%s')" % quote(
                urlunparse(phref._replace(path=relpath)), ":/#")
        else:
            return m[0]

    relpath = posixpath.relpath(dest_bookpath, posixpath.dirname(refby_bookpath))
    return CRE_INLINE_STYLE.sub(repl, text)


@updater_register("el_style")
def update_el_style(text, src_bookpath, dest_bookpath, refby_bookpath):
    def repl(m):
        text = m[0]
        text_el = unescape(m["text"])
        text_el_new = CRE_URL.sub(sub_repl, text_el)
        if text_attr == text_attr_new:
            return text
        else:
            start, stop = m.span()
            begin, end = m.span("text")
            text_new = text[:begin-start] + escape(text_el_new)
            if end < stop:
                text_new += text[end-stop:]
            return text_new

    def sub_repl(m):
        href = unquote(m[m.lastgroup])
        phref = urlparse(href)
        if phref.scheme or phref.path in ("", "."):
            return m[0]
        if reference_path(src_bookpath, phref.path, "/") == src_bookpath:
            return 'url("%s")' % quote(
                urlunparse(phref._replace(path=relpath)), ":/#")
        else:
            return m[0]

    relpath = posixpath.relpath(dest_bookpath, posixpath.dirname(refby_bookpath))
    return CRE_EL_STYLE.sub(repl, text)


class EpubFileEventHandler(FileSystemEventHandler):
    """"""
    def __init__(
        self, 
        opfwrapper: OpfWrapper, /, 
        logger: logging.Logger = logging.getLogger(), 
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

    @property
    def opfwrapper(self) -> OpfWrapper:
        return self._opfwrapper

    def get_media_type(self, bookpath: str) -> str:
        try:
            id = self._opfwrapper.bookpath_to_id(bookpath)
            return self._opfwrapper.id_to_media_type(id)
        except KeyError:
            return guess_mimetype(bookpath) or "application/octet-stream"

    def on_created(self, event):
        if event.is_directory:
            self.logger.debug(
                "Ignored created event, because it is a directory: %r" % event.src_path)
            return

        opfwrapper = self._opfwrapper
        path = realpath(event.src_path)
        bookpath = opfwrapper.path_to_bookpath(path)

        if bookpath in opfwrapper.bookpath_to_id:
            return

        if self.ignore(bookpath):
            self.logger.debug(
                "Ignored created event, because it is specified to be ignored: %r" % path)
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
            logger.info("Deleted file: %r" % opfwrapper.bookpath_to_path(bookpath))

        if event.is_directory:
            bookpath = bookpath.rstrip("/") + "/"
            for subbookpath in tuple(opfwrapper.bookpath_to_id):
                if subbookpath.startswith(bookpath):
                    delete(subbookpath)
        elif bookpath in opfwrapper.bookpath_to_id:
            delete(bookpath)

    def on_moved(self, event):
        if event.is_directory:
            self.logger.debug(
                "Ignored moved event, because it is a directory: %r -> %r" 
                % (event.src_path, event.dest_path))
            return

        opfwrapper = self._opfwrapper
        src_path, dest_path = realpath(event.src_path), realpath(event.dest_path)
        src_bookpath = opfwrapper.path_to_bookpath(src_path)
        dest_bookpath = opfwrapper.path_to_bookpath(dest_path)

        if dest_bookpath in opfwrapper.bookpath_to_id:
            self.on_deleted(FileDeletedEvent(dest_path))

        src_is_ignored = self.ignore(src_bookpath) 
        dest_is_ignored = self.ignore(dest_bookpath)
        if src_is_ignored:
            self.logger.debug(
                "Switch moved event to created event: %r -> %r" % (src_path, dest_path))
            self.on_created(FileCreatedEvent(dest_path))
            return
        elif dest_is_ignored:
            self.logger.debug(
                "Switch moved event to deleted event: %r -> %r" % (src_path, dest_path))
            self.on_deleted(FileDeletedEvent(src_path))
            return

        src_ext = posixpath.splitext(src_bookpath)[1]
        dest_ext = posixpath.splitext(dest_bookpath)[1]
        src_media_type = self.get_media_type(src_bookpath)
        dest_media_type = self.get_media_type(dest_bookpath)
        if src_ext == dest_ext or src_media_type == dest_media_type:
            id = opfwrapper.bookpath_to_id(src_bookpath)
            src_href = opfwrapper.id_to_href(id)
            dest_href = opfwrapper.bookpath_to_href(dest_bookpath)
            del opfwrapper.bookpath_to_id[src_bookpath]
            opfwrapper.bookpath_to_id[dest_bookpath] = id
            del opfwrapper.href_to_id[src_href]
            opfwrapper.href_to_id[dest_href] = id
            opfwrapper.id_to_bookpath[id] = dest_bookpath
            opfwrapper.id_to_href(id, dest_href)
            dest_media_type = src_media_type
        else:
            opfwrapper.delete(bookpath=src_bookpath)
            opfwrapper.add(bookpath=dest_bookpath, media_type=dest_media_type)

        self.logger.info("Moved file: from %r to %r" % (src_path, dest_path))


class TrackingEpubFileEventHandler(EpubFileEventHandler):
    """"""
    def __init__(
        self, 
        opfwrapper: OpfWrapper, /, 
        logger: logging.Logger = logging.getLogger(), 
        ignore: Optional[Callable[[str], bool]] = None, 
    ):
        super().__init__(opfwrapper, logger, ignore)

        self._bookpath_to_stat: dict[str, int] = {
            bookpath: stat(opfwrapper.bookpath_to_path(bookpath))
            for bookpath in opfwrapper.bookpath_to_id
        }

        self._ref_to_refby = {}
        self._refby_to_ref = defaultdict(set)
        for bookpath in opfwrapper.bookpath_to_id:
            self._add_ref(bookpath)

    def is_reffile(self, bookpath):
        media_type = self.get_media_type(bookpath)
        return media_type in MIME_REGISTRY

    def readfile(self, bookpath):
        last_stat = stat(path)
        path = self._opfwrapper.bookpath_to_path(bookpath)
        while True:
            data = open(path, "rb").read()
            cur_stat = stat(path)
            if last_stat.st_mtime_ns == cur_stat.st_mtime_ns:
                break
            last_stat = cur_stat
        return data, last_stat

    def _add_ref(self, bookpath, mime=None):
        if mime is None:
            mime = self.get_media_type(bookpath)
        if mime not in MIME_REGISTRY:
            return
        path = self._opfwrapper.bookpath_to_path(bookpath)
        try:
            text = open(path, encoding="utf-8").read()
        except FileNotFoundError:
            self.logger.error(
                "The add_ref(bookpath=%r, mime=%r) was skipped, "
                "because the file %r was deleted or moved" % (
                    bookpath, mime, path
                )
            )
            return
        except PermissionError:
            # TODO: 在 Windows 下，新增文件过快时，文件还没复制好，就已经去读了，就会报错 PermissionError
            self.logger.error(
                "The add_ref(bookpath=%r, mime=%r) was skipped, "
                "because the file %r being occupied" % (
                    bookpath, mime, path
                )
            )
            return
        result = analyze(bookpath, text, mime)
        self._ref_to_refby[bookpath] = result
        refby_to_ref = self._refby_to_ref
        for refset in result.values():
            if not refset:
                continue
            for ref_bookpath in refset:
                refby_to_ref[ref_bookpath].add(bookpath)

    def _delete_ref(self, bookpath, mime=None):
        if mime is None:
            mime = self.get_media_type(bookpath)
        if mime not in MIME_REGISTRY:
            return
        result = self._ref_to_refby.pop(bookpath, None)
        if result:
            refby_to_ref = self._refby_to_ref
            for refset in result.values():
                for ref_bookpath in refset:
                    refby_to_ref[ref_bookpath].discard(bookpath)

    def _transfer_ref(self, src_bookpath, dest_bookpath):
        ref_to_refby, refby_to_ref = self._ref_to_refby, self._refby_to_ref

        d_refby = ref_to_refby.get(src_bookpath)
        if d_refby is not None:
            for refset in d_refby.values():
                for ref in refset:
                    refby_to_ref[ref].discard(src_bookpath)
                    refby_to_ref[ref].add(dest_bookpath)
            ref_to_refby[dest_bookpath] = ref_to_refby.pop(src_bookpath)

        refset = refby_to_ref.get(src_bookpath)
        if refset is not None:
            for ref in refset:
                for d in ref_to_refby[ref].values():
                    if src_bookpath in d:
                        d[dest_bookpath] = d.pop(src_bookpath)
            refby_to_ref[dest_bookpath] = refby_to_ref.pop(src_bookpath)

    def _get_refby(self, bookpath):
        refby = {}
        refset = self._refby_to_ref.get(bookpath)
        if refset:
            ref_to_refby = self._ref_to_refby
            for ref in refset:
                result = ref_to_refby[ref]
                refby[ref] = [
                    (key, val[bookpath]) 
                    for key, val in result.items() if bookpath in val
                ]
        return refby

    def _update_refby(self, src_bookpath, dest_bookpath, refby):
        if not refby:
            return

        to_path = self._opfwrapper.bookpath_to_path

        for refby_bookpath, typelist in refby.items():
            if refby_bookpath == src_bookpath:
                refby_bookpath = dest_bookpath

            refby_path = to_path(refby_bookpath)

            try:
                refby_stat = stat(refby_path)
                if refby_stat.st_mtime_ns != self._bookpath_to_stat[refby_bookpath].st_mtime_ns:
                    self.logger.error(
                        "Automatic update reference %r -> %r was skipped, "
                        "because the file %r was deleted or moved" % (
                            src_bookpath, dest_bookpath, refby_path
                        )
                    )
                    continue
                text = open(refby_path, encoding="utf-8").read()
            except FileNotFoundError:
                self.logger.error(
                    "Automatic update reference %r -> %r was skipped, "
                    "because the file %r have been deleted or moved" % (
                        src_bookpath, dest_bookpath, refby_path
                    )
                )
            else:
                text_new = update(text, src_bookpath, dest_bookpath, refby_bookpath, typelist)
                if text != text_new:
                    open(refby_path, "w", encoding="utf-8").write(text_new)
                    self.on_modified(FileModifiedEvent(refby_path))

    def on_created(self, event):
        if event.is_directory:
            self.logger.debug(
                "Ignored created event, because it is a directory: %r" % event.src_path)
            return

        opfwrapper = self._opfwrapper
        bookpath_to_stat = self._bookpath_to_stat
        path = realpath(event.src_path)
        bookpath = opfwrapper.path_to_bookpath(path)

        try:
            bookpath_stat = stat(path)
        except FileNotFoundError:
            if self.ignore(bookpath):
                self.logger.debug(
                    "Ignored created event, because it is specified to be ignored: %r" % path)
            else:
                self.logger.error(
                    "Ignored created event, maybe it was deleted or moved: %r" % path)
            return

        if bookpath in opfwrapper.bookpath_to_id:
            if bookpath_stat.st_mtime_ns == bookpath_to_stat[bookpath].st_mtime_ns:
                self.logger.debug(
                    "Ignored created event, because it was already created: %r" % event.src_path)
                return
            self.on_deleted(FileDeletedEvent(path))

        if self.ignore(bookpath):
            self.logger.debug(
                "Ignored created event, because it is specified to be ignored: %r" % path)
            return

        if self.is_reffile(bookpath):
            try:
                self._add_ref(bookpath)
            except FileNotFoundError:
                self.logger.error(
                    "Ignored created event, maybe it was deleted or "
                    "moved during processing: %r" % path)
                return
            except UnicodeDecodeError:
                choice = input('Created event occured, but the file %r cannot be decoded. '
                    'Set media-type to "application/octet-stream" (or skip): ([Y]/n)' % path)
                if choice.strip().lower() in ("", "y", "yes"):
                    opfwrapper.add(bookpath=bookpath, media_type="application/octet-stream")
                return

        opfwrapper.add(bookpath=bookpath)
        bookpath_to_stat[bookpath] = bookpath_stat
        self.logger.info("Created file: %r" % path)

    def on_deleted(self, event):
        opfwrapper = self._opfwrapper
        path = realpath(event.src_path)
        bookpath = opfwrapper.path_to_bookpath(path)
        logger = self.logger

        def delete(bookpath):
            item = opfwrapper.delete(bookpath=bookpath)
            self._delete_ref(bookpath, item.media_type)
            self._bookpath_to_stat.pop(bookpath, None)
            logger.info("Deleted file: %r" % opfwrapper.bookpath_to_path(bookpath))

        if event.is_directory:
            bookpath = bookpath.rstrip("/") + "/"
            for subbookpath in tuple(opfwrapper.bookpath_to_id):
                if subbookpath.startswith(bookpath):
                    delete(subbookpath)
        elif bookpath in opfwrapper.bookpath_to_id:
            delete(bookpath)

    def on_modified(self, event):
        # NOTE: In some platforms (operating systems or file systems), 
        #       when a file is modified, two modified events will be triggered, 
        #       the first is truncation, and the second is writing.
        if event.is_directory:
            self.logger.debug(
                "Ignored modified event, because it is a directory: %r" % event.src_path)
            return

        opfwrapper = self._opfwrapper
        path = realpath(event.src_path)
        bookpath = opfwrapper.path_to_bookpath(path)

        if bookpath not in opfwrapper.bookpath_to_id:
            if self.ignore(bookpath):
                self.logger.debug(
                "Ignored modified event, because it is not in the opf file: %r" % path)
            else:
                self.on_created(FileCreatedEvent(path))
            return
        elif not self.is_reffile(bookpath):
            return
        elif not syspath.isfile(path):
            self.on_deleted(FileDeletedEvent(path))
            return

        try:
            bookpath_stat = stat(path)
        except FileNotFoundError:
            self.logger.error(
                "Ignored modified event, maybe it was deleted or moved: %r" % path)
        else:
            last_stat = self._bookpath_to_stat.get(bookpath)
            if last_stat and last_stat.st_mtime_ns == bookpath_stat.st_mtime_ns:
                self.logger.debug(
                    "Ignored modified event, because its mtime is already latest: %r" % path)
                return
            self._bookpath_to_stat[bookpath] = bookpath_stat

        self._delete_ref(bookpath)
        self._add_ref(bookpath)
        self.logger.info("Modified file: %r" % path)

    def on_moved(self, event):
        if event.is_directory:
            self.logger.debug(
                "Ignored moved event, because it is a directory: %r -> %r" 
                % (event.src_path, event.dest_path))
            return

        opfwrapper = self._opfwrapper
        src_path, dest_path = realpath(event.src_path), realpath(event.dest_path)
        src_bookpath = opfwrapper.path_to_bookpath(src_path)
        dest_bookpath = opfwrapper.path_to_bookpath(dest_path)

        if dest_bookpath in opfwrapper.bookpath_to_id:
            self.on_deleted(FileDeletedEvent(dest_path))

        src_is_ignored = self.ignore(src_bookpath) 
        dest_is_ignored = self.ignore(dest_bookpath)
        if src_is_ignored:
            self.logger.debug(
                "Switch moved event to created event: %r -> %r" % (src_path, dest_path))
            self.on_created(FileCreatedEvent(dest_path))
            return
        elif dest_is_ignored:
            self.logger.debug(
                "Switch moved event to deleted event: %r -> %r" % (src_path, dest_path))
            self.on_deleted(FileDeletedEvent(src_path))
            return

        src_ext = posixpath.splitext(src_bookpath)[1]
        dest_ext = posixpath.splitext(dest_bookpath)[1]
        src_media_type = self.get_media_type(src_bookpath)
        dest_media_type = self.get_media_type(dest_bookpath)
        if src_ext == dest_ext or src_media_type == dest_media_type:
            id = opfwrapper.bookpath_to_id(src_bookpath)
            src_href = opfwrapper.id_to_href(id)
            dest_href = opfwrapper.bookpath_to_href(dest_bookpath)
            del opfwrapper.bookpath_to_id[src_bookpath]
            opfwrapper.bookpath_to_id[dest_bookpath] = id
            del opfwrapper.href_to_id[src_href]
            opfwrapper.href_to_id[dest_href] = id
            opfwrapper.id_to_bookpath[id] = dest_bookpath
            opfwrapper.id_to_href(id, dest_href)
            dest_media_type = src_media_type
        else:
            opfwrapper.delete(bookpath=src_bookpath)
            opfwrapper.add(bookpath=dest_bookpath, media_type=dest_media_type)

        self._transfer_ref(src_bookpath, dest_bookpath)
        self._bookpath_to_stat[dest_bookpath] = self._bookpath_to_stat.pop(src_bookpath)
        refby = self._get_refby(dest_bookpath)
        if dest_media_type not in MIME_REGISTRY:
            refby.pop(dest_bookpath, None)

        self.logger.info("Moved file: from %r to %r" % (src_path, dest_path))
        self._update_refby(src_bookpath, dest_bookpath, refby)


def watch(
    opfwrapper: OpfWrapper, /, 
    logger: logging.Logger = logging.getLogger(), 
    ignore: Optional[Callable[[str], bool]] = None,
    update_reference: bool = True, 
):
    """Monitor all events of an epub editing directory, and maintain opf continuously."""
    watchdir = opfwrapper.ebook_root
    observer = Observer()
    handler_class = TrackingEpubFileEventHandler if update_reference else EpubFileEventHandler
    event_handler = handler_class(opfwrapper, logger=logger, ignore=ignore)
    observer.schedule(event_handler, watchdir, recursive=True)
    logger.info("Watching directory: %r" % watchdir)
    observer.start()
    try:
        while True:
            sleep(0.1)
    except KeyboardInterrupt:
        logger.info("Shutting down watching ...")
    finally:
        observer.stop()
        observer.join()
    opfwrapper.dump()
    logger.info("Done!")

