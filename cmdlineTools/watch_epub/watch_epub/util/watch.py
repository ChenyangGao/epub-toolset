 #!/usr/bin/env python
# coding: utf-8

__author__  = "ChenyangGao <https://chenyanggao.github.io/>"
__version__ = (0, 1)
__all__ = ["watch"]

# TODO: 移动文件到其他文件夹，那么这个文件所引用的那些文件，相对位置也会改变
# TODO: created 事件时，文件不存在，则文件可能是被移动或删除，则应该注册一个回调，因为事件没有被正确处理
# TODO: 是否需要忽略那些所在的祖先目录也是隐藏（以'.'为前缀）的文件？

import logging
import posixpath

from collections import defaultdict, Counter
from functools import partial
from os import path as syspath, stat
from os.path import basename, dirname, realpath, sep
from re import compile as re_compile, Pattern
from time import sleep
from typing import Final
from urllib.parse import quote, unquote, urlparse, urlunparse

from watchdog.events import ( # type: ignore
    FileDeletedEvent, FileCreatedEvent, FileModifiedEvent, FileSystemEventHandler
)
from watchdog.observers import Observer # type: ignore

from util.hrefutils import buildRelativePath
from util.pathutils import guess_mimetype, relative_path, to_syspath, to_posixpath
from util.wrapper import Wrapper


MIMES_OF_TEXT = ("text/html", "application/xhtml+xml", "application/x-dtbook+xml")
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

LOGGER: Final[logging.Logger] = logging.getLogger()
LOGGER.setLevel(logging.INFO)
_sh = logging.StreamHandler()
LOGGER.addHandler(_sh)
_fmt = logging.Formatter('[%(asctime)s] %(levelname)s ➜ %(message)s')
_fmt.datefmt = '%Y-%m-%d %H:%M:%S'
_sh.setFormatter(_fmt)


# TODO: 使用策略模式
# TODO: 应该更新 toc 文件
def analyze_one(bookpath, data, mime=None):
    """"""
    def gen_filtered_links(links):
        for link in links:
            link = unquote(link.partition('#')[0])
            if link in ('', '.') or CRE_PROT.match(link) is not None:
                continue
            ref_path = relative_path(link, bookpath, lib=posixpath)
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


def analyze(wrapper):
    """"""
    map_path_refset = {}
    map_ref_pathset = defaultdict(set)

    for fid, href, mime in wrapper.manifest_iter():
        if mime not in MIMES_OF_TEXT or mime not in MIMES_OF_STYLES:
            continue

        bookpath = wrapper.id_to_bookpath[fid]

        realpath = syspath.join(wrapper.ebook_root, to_syspath(bookpath, posixpath))
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

    def __init__(self, watchdir, wrapper=None, logger=LOGGER):
        super().__init__()
        watchdir = realpath(watchdir)
        if not watchdir.endswith(sep):
            watchdir += sep
        self._watchdir = watchdir
        if wrapper is None:
            wrapper = Wrapper(watchdir)
        self._wrapper = wrapper
        self._map_path_refset, self._map_ref_pathset = analyze(wrapper)
        self._file_missing = defaultdict(list)
        self._file_mtime = {
            (p := syspath.join(watchdir, to_syspath(bookpath, posixpath))): 
                stat(p).st_mtime_ns
            for bookpath in wrapper.bookpath_to_id
        }
        self.logger = logger

    @property
    def watchdir(self):
        """"""
        return self._watchdir

    @property
    def wrapper(self):
        return self._wrapper

    def get_bookpath(self, path):
        """"""
        return to_posixpath(realpath(path)[len(self._watchdir):])

    def get_path(self, bookpath):
        """"""
        return syspath.join(self._watchdir, to_syspath(bookpath, posixpath))

    def get_mime(self, bookpath):
        """"""
        wrapper = self._wrapper
        if bookpath in wrapper.bookpath_to_id:
            return wrapper.id_to_mime[wrapper.bookpath_to_id[bookpath]]
        else:
            return guess_mimetype(bookpath)

    def _add_bookpath_ref(self, bookpath, mime=None):
        if mime is None:
            mime = self.get_mime(bookpath)
        if mime in MIMES_OF_STYLES or mime in MIMES_OF_TEXT:
            try:
                realpath = self.get_path(bookpath)
                content = open(realpath, encoding="utf-8").read()
            except FileNotFoundError:
                # TODO: The file may be deleted or moved, a callback should be registered here, 
                #       then called when the modified event is triggered
                return
            result = analyze_one(bookpath, content)
            if not result:
                return
            self._map_path_refset[bookpath] = result
            if mime in MIMES_OF_TEXT:
                for ref_bookpath in result:
                    self._map_ref_pathset[ref_bookpath].add(bookpath)
            elif mime in MIMES_OF_TEXT:
                for refset in result.values():
                    for ref_bookpath in refset:
                        self._map_ref_pathset[ref_bookpath].add(bookpath)

    def _del_bookpath_ref(self, bookpath, mime=None):
        if mime is None:
            mime = self.get_mime(bookpath)
        if mime in MIMES_OF_TEXT:
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

            if relative_path(link, refby, lib=posixpath) == bookpath:
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
            if relative_path(link, refby, lib=posixpath) == bookpath:
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
                    if stat(refby_srcpath).st_mtime_ns != self._file_mtime[refby_srcpath]:
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
                            if stat(refby_srcpath).st_mtime_ns != self._file_mtime[refby_srcpath]:
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
                        self.on_modified(FileModifiedEvent(refby_srcpath), _keep_callbacks=True)
                    self._file_missing[refby_srcpath].append(callback)
                    continue
                content = CRE_URL.sub(partial(url_repl, refby=refby), content)
            else:
                refby, types = refby
                if refby == bookpath:
                    refby = dest_bookpath
                refby_srcpath = self._watchdir + to_syspath(refby, posixpath)
                try:
                    if stat(refby_srcpath).st_mtime_ns != self._file_mtime[refby_srcpath]:
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
                            if stat(refby_srcpath).st_mtime_ns != self._file_mtime[refby_srcpath]:
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
                        self.on_modified(FileModifiedEvent(refby_srcpath), _keep_callbacks=True)
                    self._file_missing[refby_srcpath].append(callback)
                    continue
                for tp in types:
                    if tp == 'ref':
                        content = CRE_REF.sub(partial(ref_repl, refby=refby), content)
                    elif tp == 'inline':
                        content = sub_url_in_hxml(content, refby, CRE_INLINE_STYLE)
                    elif tp == 'style':
                        content = sub_url_in_hxml(content, refby, CRE_EL_STYLE)
            open(refby_srcpath, 'w').write(content)
            self.on_modified(FileModifiedEvent(refby_srcpath), _keep_callbacks=True)

    def on_created(self, event):
        """"""
        src_path = event.src_path
        self._file_missing.pop(src_path, None)

        bookpath = self.get_bookpath(src_path)
        if event.is_directory:
            self.logger.debug(
                "Ignored created event, because it is directory: %r" % bookpath)
        elif basename(bookpath).startswith("."):
            self.logger.debug(
                "Ignored created event, because filename prefix with '.': %r" 
                    % bookpath)
        elif bookpath in self.wrapper.bookpath_to_id:
            self.logger.debug(
                "Ignored created event, because it is not in the opf file: %r" 
                    % bookpath)
        else:
            *_, mime = self._wrapper.addfile(bookpath)
            mtime = stat(src_path).st_mtime_ns
            self._add_bookpath_ref(bookpath, mime)
            self._file_mtime[src_path] = mtime
            self.logger.info("Created file: %r" % bookpath)

    def on_deleted(self, event):
        """"""
        src_path = event.src_path
        self._file_missing.pop(src_path, None)

        logger = self.logger
        wrapper = self._wrapper

        def delete(bookpath):
            try:
                *_, mimetype = wrapper.deletefile_by_path(bookpath)
            except:
                logger.debug(
                    "Ignored deleted event, because it is not in the opf file: %r" 
                        % bookpath)
            else:
                self._del_bookpath_ref(bookpath, mimetype)
                logger.info("Deleted file: %s" % bookpath)

        bookpath = self.get_bookpath(src_path)
        if event.is_directory:
            bookpath += '/'
            for subbookpath, _ in tuple(wrapper.bookpath_to_id.items()):
                if subbookpath.startswith(bookpath):
                    delete(subbookpath)
        else:
            delete(bookpath)

    def on_modified(self, event, _keep_callbacks=False):
        """"""
        # NOTE: When a file is modified, two modified events will be triggered, 
        #       the first is truncation, and the second is writing.
        src_path = event.src_path
        bookpath = self.get_bookpath(src_path)

        if event.is_directory:
            self.logger.debug(
                "Ignored modified event, because it is directory: %r" % bookpath)
        elif bookpath not in self._wrapper.bookpath_to_id:
            self.logger.debug(
                "Ignored modified event, because it is not in the opf file: %r" 
                    % bookpath)
        else:
            try:
                mtime = stat(src_path).st_mtime_ns
            except FileNotFoundError:
                self.logger.debug(
                    "Ignored modified event, maybe it was deleted or moved: %r" 
                        % bookpath)
            else:
                if self._file_mtime.get(src_path) == mtime:
                    self.logger.debug(
                        "Ignored modified event, because its mtime has not changed: %r" 
                            % bookpath)
                    return
                if not _keep_callbacks:
                    self._file_missing.pop(src_path, None)
                self._file_mtime[src_path] = mtime
                self._del_bookpath_ref(bookpath)
                self._add_bookpath_ref(bookpath)
                self.logger.info("Modified file: %r", bookpath)

    def on_moved(self, event):
        """"""
        src_path, dest_path = event.src_path, event.dest_path
        src_bookpath = self.get_bookpath(src_path)
        dest_bookpath = self.get_bookpath(dest_path)

        if event.is_directory:
            self.logger.debug(
                "Ignored moved event, because it is directory: %r" % src_bookpath)
            return

        src_is_hidden = basename(src_bookpath).startswith('.')
        dst_is_hidden = basename(dest_bookpath).startswith('.')
        if src_is_hidden:
            if not dst_is_hidden:
                self.logger.debug(
                    "Switch moved event to created event: %r -> %r" 
                        % (src_bookpath, dst_is_hidden))
                self.on_created(FileCreatedEvent(dest_path))
        elif dst_is_hidden:
            self.logger.debug(
                "Switch moved event to deleted event: %r -> %r" 
                    % (src_bookpath, dst_is_hidden))
            self.on_deleted(FileDeletedEvent(src_path))
        elif src_bookpath not in self.wrapper.bookpath_to_id:
            self.logger.debug(
                "Ignored moved event, because file has already been moved: %r" 
                    % src_bookpath)
        else:
            if posixpath.splitext(src_bookpath)[1] == posixpath.splitext(dest_bookpath)[1]:
                wrapper = self._wrapper
                oldpath = src_bookpath
                newpath = dest_bookpath
                fid = wrapper.bookpath_to_id[oldpath]
                oldhref = wrapper.id_to_href[fid]
                newhref = buildRelativePath(wrapper.opfbookpath, newpath)
                del wrapper.bookpath_to_id[oldpath]
                del wrapper.href_to_id[oldhref]
                wrapper.href_to_id[newhref] = fid
                wrapper.bookpath_to_id[newpath] = fid
                wrapper.id_to_filepath[fid] = newpath
                wrapper.id_to_href[fid] = newhref
            else:
                self.wrapper.deletefile_by_path(src_bookpath)
                self.wrapper.addfile(dest_bookpath)

            old_mtime = self._file_mtime[src_path]
            self._file_mtime[dest_path] = old_mtime
            map_path_refset, map_ref_pathset = self._map_path_refset, self._map_ref_pathset
            pathset = map_ref_pathset.get(src_bookpath)
            ls_refby = []
            if pathset:
                for p in pathset:
                    result = map_path_refset[p]
                    if type(result) is dict:
                        ls_refby.append(
                            (p, [key for key, val in result.items() if src_bookpath in val]))
                    else:
                        ls_refby.append(p)

            result = map_path_refset.get(src_bookpath)
            self._del_bookpath_ref(src_bookpath)
            old_mime = self.get_mime(src_bookpath)
            mime = self.get_mime(dest_bookpath)
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

            if src_path in self._file_missing:
                callbacks = self._file_missing.pop(src_path)
                try:
                    mtime = stat(dest_path).st_mtime_ns
                except FileNotFoundError:
                    self._file_missing[dest_path] = callback
                else:
                    if mtime == old_mtime:
                        for callback in callbacks:
                            callback(dest_bookpath, dest_path)
            self.logger.info(
                "Moved file: from %s to %s", src_bookpath, dest_bookpath)
            self._update_refby_files(src_bookpath, dest_bookpath, ls_refby)


def watch(watchdir, wrapper=None):
    "Monitor all events of an epub editing directory, and maintain opf continuously."
    if wrapper is None:
        wrapper = Wrapper(watchdir)
    observer = Observer()
    event_handler = EpubFileEventHandler(watchdir, wrapper)
    observer.schedule(event_handler, watchdir, recursive=True)
    LOGGER.info("Watching directory: %r" % watchdir)
    observer.start()
    try:
        while True:
            sleep(0.1)
    except KeyboardInterrupt:
        LOGGER.info('Shutting down watching ...')
        wrapper.write_opf()
    finally:
        observer.stop()
        observer.join()
    LOGGER.info('Done!')

