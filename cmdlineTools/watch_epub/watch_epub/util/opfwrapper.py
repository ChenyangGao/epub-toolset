#!/usr/bin/env python3
# coding: utf-8

__version__ = (0, 1)

import sys
import os
import re
import os.path as syspath
import posixpath

from dataclasses import dataclass, field
from os import fsdecode, PathLike
from typing import Iterator, MutableMapping, NamedTuple, Optional, Union

from urllib.parse import quote, unquote, urlparse
from util.pathutils import reference_path, relative_path, starting_dir, to_posixpath

from util.mimetype import guess_mimetype
from util.makeid import makeid
from util.opfparser import OpfParser

import unicodedata



# https://www.w3.org/publishing/epub3/epub-packages.html#sec-package-elem

# TODO: 😂 我认为，对OPF的操作，应该是对DOM树的操作

@dataclass
class MetadataElement:
    name: str
    attrib: dict = field(default_factory=dict)
    content: str = ""


@dataclass
class ManifestItem:
    id: str
    href: str
    media_type: str = "application/octet-stream"
    fallback: Optional[str] = None
    media_overlay: Optional[str] = None
    properties: Optional[str] = None


@dataclass
class SpineItemref:
    idref: str
    id: Optional[str] = None
    linear: Optional[str] = None
    properties: Optional[str] = None


@dataclass
class GuideItem:
    type: str
    title: str
    href: str

    @property
    def parsed_href(self):
        return urlparse(self.href)


@dataclass
class BindingsItem:
    mediatype
    handler


@dataclass
class CollectionItem:
    ...




def _unicodestr(p):
    if p is None:
        return None
    if isinstance(p, str):
        return p
    return p.decode('utf-8', errors='replace')

_PKG_VER = re.compile(r'''<\s*package[^>]*version\s*=\s*["']([^'"]*)['"][^>]*>''', re.IGNORECASE)

# Wrapper Class is used to peform record keeping for Sigil.  It keeps track of modified,
# added, and deleted files while providing some degree of protection against files under
# Sigil's control from being directly manipulated.
# Uses "write-on-modify" and so removes the need for wholesale copying of files

_guide_types = ['cover', 'title-page', 'toc', 'index', 'glossary', 'acknowledgements',
                'bibliography', 'colophon', 'copyright-page', 'dedication',
                'epigraph', 'foreward', 'loi', 'lot', 'notes', 'preface', 'text']

PROTECTED_FILES = [
    'mimetype',
    'META-INF/container.xml',
]
SPINE_CONCERNED_MIMES = ["text/html", "application/xhtml+xml"]


def _epub_file_walk(top):
    top = os.fsdecode(top)
    rv = []
    for base, dnames, names in os.walk(top):
        for name in names:
            rv.append(os.path.relpath(os.path.join(base, name), top))
    return rv


class WrapperException(Exception):
    pass


class OpfIter:

    def metadata_iter(self) -> Iterator[MetadataItem]:
        yield from self.metadata

    def manifest_iter(self) -> Iterator[ManifestItem]:
        yield from self.manifest.values()

    def text_iter(self) -> Iterator[ManifestItem]:
        id_to_spine = self.id_to_spine
        id_to_mime = self.id_to_mime
        for id in self.id_to_href:
            if id in id_to_spine and id_to_spine[id].linear != (False, "no") or \
                    self.id_to_mime.get(id) in ("text/html", "application/xhtml+xml"):
                yield ManifestItem(
                    id = id, 
                    href    = self.id_to_href[id], 
                    bookpath    = self.id_to_bookpath[id], 
                    mimetype    = self.id_to_mime.get.get(id, "application/octet-stream"), 
                    properties  = self.id_to_properties.get(id), 
                    fallback    = self.id_to_fallback.get(id), 
                    overlay     = self.id_to_overlay.get(id), 
                )

    def spine_iter(self) -> Iterator[SpineItemref]:
        yield from self.id_to_spine.values()

    def guide_iter(self) -> Iterator[GuideItem]:
        yield from self.guide

    def bindings_iter(self) -> Iterator[BindingsItem]:
        yield from self.bindings

    def collection_iter(self) -> Iterator[CollectionItem]:
        yield from self.bindings


class OpfPathOp:

    def path_to_href(self, path: Union[AnyStr, PathLike[AnyStr]]) -> str:
        bookpath = self.path_to_bookpath(path_to_bookpath)
        return posixpath.relpath(bookpath, self.opf_dir)

    def path_to_bookpath(self, path: Union[AnyStr, PathLike[AnyStr]]) -> str:
        path_: str = fsdecode(syspath.realpath(path))
        if not path_.startswith(self.ebook_root):
            raise ValueError(f"{path!r} is not in the directory {self.ebook_root!r}")
        return path_to_posix(path_.removeprefix(self.ebook_root)).lstrip("/")

    def href_to_path(self, href: str) -> str:
        return syspath.join(
            self.ebook_root, 
            path_posix_to_sys(self.opf_dir), 
            path_posix_to_sys(href), 
        )

    def bookpath_to_path(self, bookpath: str) -> str:
        return syspath.join(
            self.ebook_root, 
            path_posix_to_sys(bookpath), 
        )

    def bookpath_to_href(self, bookpath: str) -> str:
        return posixpath.relpath(bookpath, self.opf_dir)

    def href_to_bookpath(self, href: str) -> str:
        return posixpath.join(self.opf_dir, href)

    def has(
        self, 
        id: Optional[str] = None, 
        href: Optional[str] = None, 
        bookpath: Optional[str] = None, 
    ) -> bool:
        if id is not None:
            return id in self.manifest
        elif href is not None:
            return href in self.href_to_id
        elif bookpath is not None:
            return href in self.bookpath_to_id

    def get(
        self, 
        id: Optional[str] = None, 
        href: Optional[str] = None, 
        bookpath: Optional[str] = None, 
    ) -> ManifestItem:
        if id is not None:
            pass
        elif href is not None:
            try:
                id = self.href_to_id[href]
            except KeyError:
                raise WrapperException(
                    f"href {href!r} does not exist in manifest!")
        elif bookpath is not None:
            try:
                id = self.bookpath_to_id[bookpath]
            except KeyError:
                raise WrapperException(
                    f"Bookpath {bookpath!r} does not exist in manifest!")
        else:
            raise ValueError("Give (not None) at least one of arguments: "
                             "id, href or bookpath")

        return self.manifest[id]

    def add(
        self, 
        path: Union[None, AnyStr, PathLike[AnyStr]] = None, 
        bookpath: Optional[str] = None, 
        href: Optional[str] = None, 
        id: Optional[str] = None, 
        mime: Optional[str] = None, 
        properties: Optional[dict] = None, 
        fallback: Optional[str] = None, 
        overlay: Optional[str] = None, 
    ) -> ManifestItem:
        if path is not None:
            href = self.path_to_href(path)
            bookpath = self.path_to_bookpath(path)
        elif bookpath is not None:
            href = self.bookpath_to_href(bookpath)
        elif href is not None:
            bookpath = self.bookpath_to_href(href)
        else:
            raise ValueError("Give (not None) at least one of arguments: "
                             "path, bookpath or href")

        if id is None:
            id = makeid(bookpath, href, self.manifest.keys())
        elif id in self.manifest:
            raise WrapperException(f"Id {id} is already exist in manifest")

        if mime is None:
            mime = guess_mimetype(href)
        if mime is None:
            raise WrapperException("Unable to determine media-type (MIME)")

        item = self.manifest[id] = ManifestItem(
            id, href, bookpath, mime, properties, fallback, overlay)
        self.href_to_id[href] = id
        self.bookpath_to_id[bookpath] = id

        if mime in SPINE_CONCERNED_MIMES:
            self.spine[id] = SpineItemref(id)

        return item

    def delete(
        self, 
        id: Optional[str] = None, 
        href: Optional[str] = None, 
        bookpath: Optional[str] = None, 
    ) -> ManifestItem:
        item = self.get(id, href, bookpath)
        del self.manifest[item.id]
        self.href_to_id.pop(item.href, None)
        self.bookpath_to_id.pop(item.bookpath, None)
        self.spine.pop(item.id, None)

        return item


class OpfWrapper(OpfParser, OpfIter, OpfPathOp):

    def __init__(self, ebook_root: str = ""):
        super().__init__(ebook_root)

        # invert key dictionaries to allow for reverse access
        self.href_to_id = {v: k for k, v in self.id_to_href.items()}
        self.bookpath_to_id = {v: k for k, v in self.id_to_bookpath.items()}

        # walk the ebook directory tree building up initial list of
        # all unmanifested (other) files
        for filepath in _epub_file_walk(ebook_root):
            book_href = filepath.replace(os.sep, "/")
            # OS X file names and paths use NFD form. The EPUB
            # spec requires all text including filenames to be in NFC form.
            book_href = unicodedata.normalize('NFC', book_href)
            # if book_href file in manifest convert to manifest id
            id = self.bookpath_to_id.get(book_href, None)
            if id is None:
                self.other.append(book_href)
                self.book_href_to_filepath[book_href] = filepath
            else:
                self.id_to_filepath[id] = filepath

    # utility routine to get mime from href (book href or opf href)
    # no fragments present
    def getmime(self, href):
        href = _unicodestr(href)
        href = unquote(href)
        return guess_mimetype(href)

    # New in Sigil 1.0
    # ----------------

    # A book path (aka "bookpath" or "book_path") is a unique relative path
    # from the ebook root to a specific file.  As a relative path meant to
    # be used in an href or src link it only uses forward slashes "/"
    # as path segment separators.  Since all files exist inside the
    # epub root (folder the epub was unzipped into), book paths will NEVER
    # have or use "./" or "../" ie they are in always in canonical form

    # We will use the terms book_href (aka "href") interchangeabily
    # with bookpath with the following convention:
    #   - use book_href when working with "other" files outside of the manifest
    #   - use bookpath when working with files in the manifest
    #   - use either when the file in question in the OPF as it exists in the intersection

    # returns the book path to the folder containing this bookpath
    def get_startingdir(self, bookpath):
        bookpath = _unicodestr(bookpath)
        return starting_dir(bookpath, "/")

    # return a bookpath for the file pointed to by the href from
    # the specified bookpath starting directory
    # no fragments allowed in href (must have been previously split off)
    def build_bookpath(self, href, starting_dir):
        href = _unicodestr(href)
        href = unquote(href)
        starting_dir = _unicodestr(starting_dir)
        if starting_dir:
            starting_dir += "/"
        return reference_path(starting_dir, href, "/")

    # returns the href relative path from source bookpath to target bookpath
    def get_relativepath(self, from_bookpath, to_bookpath):
        from_bookpath = _unicodestr(from_bookpath)
        to_bookpath = _unicodestr(to_bookpath)
        return relative_path(from_bookpath, to_bookpath, "/")

    # ----------

    # routines to rebuild the opf on the fly from current information
    def build_package_starttag(self):
        return self.package_tag

    def build_manifest_xml(self):
        manout = []
        manout.append('  <manifest>\n')
        for id in sorted(self.id_to_mime):
            href = self.id_to_href[id]
            # relative manifest hrefs must have no fragments
            if href.find(':') == -1:
                href = quote(href)
            mime = self.id_to_mime[id]
            props = ''
            properties = self.id_to_properties[id]
            if properties is not None:
                props = ' properties="%s"' % properties
            fall = ''
            fallback = self.id_to_fallback[id]
            if fallback is not None:
                fall = ' fallback="%s"' % fallback
            over = ''
            overlay = self.id_to_overlay[id]
            if overlay is not None:
                over = ' media-overlay="%s"' % overlay
            manout.append('    <item id="%s" href="%s" media-type="%s"%s%s%s />\n' % (id, href, mime, props, fall, over))
        manout.append('  </manifest>\n')
        return "".join(manout)

    def build_spine_xml(self):
        spineout = []
        ppd = ''
        ncx = ''
        map = ''
        if self.spine_ppd is not None:
            ppd = ' page-progression-direction="%s"' % self.spine_ppd
        tocid = self.gettocid()
        if tocid is not None:
            ncx = ' toc="%s"' % tocid
        pagemapid = self.getpagemapid()
        if pagemapid is not None:
            map = ' page-map="%s"' % pagemapid
        spineout.append('  <spine%s%s%s>\n' % (ppd, ncx, map))
        for (id, linear, properties) in self.spine:
            lin = ''
            if linear is not None:
                lin = ' linear="%s"' % linear
            props = ''
            if properties is not None:
                props = ' properties="%s"' % properties
            spineout.append('    <itemref idref="%s"%s%s/>\n' % (id, lin, props))
        spineout.append('  </spine>\n')
        return "".join(spineout)

    def build_guide_xml(self):
        guideout = []
        if len(self.guide) > 0:
            guideout.append('  <guide>\n')
            for (type, title, href) in self.guide:
                # note guide hrefs may have fragments so must be kept
                # in url encoded form at all times until splitting into component parts
                guideout.append('    <reference type="%s" href="%s" title="%s"/>\n' % (type, href, title))
            guideout.append('  </guide>\n')
        return "".join(guideout)

    def build_bindings_xml(self):
        bindout = []
        if len(self.bindings) > 0 and self.epub_version.startswith('3'):
            bindout.append('  <bindings>\n')
            for (mtype, handler) in self.bindings:
                bindout.append('    <mediaType media-type="%s" handler="%s"/>\n' % (mtype, handler))
            bindout.append('  </bindings>\n')
        return "".join(bindout)

    def build_opf(self):
        data = []
        data.append('<?xml version="1.0" encoding="utf-8" standalone="yes"?>\n')
        data.append(self.build_package_starttag())
        data.append(self.metadataxml)
        data.append(self.build_manifest_xml())
        data.append(self.build_spine_xml())
        data.append(self.build_guide_xml())
        data.append(self.build_bindings_xml())
        data.append('</package>\n')
        return "".join(data)

    def write_opf(self):
        platpath = self.opf_bookpath.replace('/', os.sep)
        filepath = os.path.join(self.ebook_root, platpath)
        base = os.path.dirname(filepath)
        if not os.path.exists(base):
            os.makedirs(base)
        with open(filepath, "w", encoding="utf-8") as fp:
            fp.write(self.build_opf())

    # routines to help find the manifest id of toc.ncx and page-map.xml

    def gettocid(self):
        for id in self.id_to_mime:
            mime = self.id_to_mime[id]
            if mime == "application/x-dtbncx+xml":
                return id
        return None

    def getpagemapid(self):
        for id in self.id_to_mime:
            mime = self.id_to_mime[id]
            if mime == "application/oebs-page-map+xml":
                return id
        return None

    # routines to help find the manifest id of the nav
    def getnavid(self):
        if self.epub_version == "2.0":
            return None
        for id in self.id_to_mime:
            mime = self.id_to_mime[id]
            if mime == "application/xhtml+xml":
                properties = self.id_to_properties[id]
                if properties is not None and "nav" in properties:
                    return id
        return None

    # routines to manipulate the spine
    def getspine(self):
        osp = []
        for (sid, linear, properties) in self.spine:
            osp.append((sid, linear))
        return osp

    def setspine(self, new_spine):
        spine = []
        for (sid, linear) in new_spine:
            properties = None
            sid = _unicodestr(sid)
            linear = _unicodestr(linear)
            if sid not in self.id_to_href:
                raise WrapperException('Spine Id not in Manifest')
            if linear is not None:
                linear = linear.lower()
                if linear not in ['yes', 'no']:
                    raise Exception('Improper Spine Linear Attribute')
            spine.append((sid, linear, properties))
        self.spine = spine
        self.modified[self.opf_bookpath] = 'file'

    def getspine_epub3(self):
        return self.spine

    def setspine_epub3(self, new_spine):
        spine = []
        for (sid, linear, properties) in new_spine:
            sid = _unicodestr(sid)
            linear = _unicodestr(linear)
            properties = _unicodestr(properties)
            if properties is not None and properties == "":
                properties = None
            if sid not in self.id_to_href:
                raise WrapperException('Spine Id not in Manifest')
            if linear is not None:
                linear = linear.lower()
                if linear not in ['yes', 'no']:
                    raise Exception('Improper Spine Linear Attribute')
            if properties is not None:
                properties = properties.lower()
            spine.append((sid, linear, properties))
        self.spine = spine
        self.modified[self.opf_bookpath] = 'file'

    def getbindings_epub3(self):
        return self.bindings

    def setbindings_epub3(self, new_bindings):
        bindings = []
        for (mtype, handler) in new_bindings:
            mtype = _unicodestr(mtype)
            handler = _unicodestr(handler)
            if mtype is None or mtype == "":
                continue
            if handler is None or handler == "":
                continue
            if handler not in self.id_to_href:
                raise WrapperException('Handler not in Manifest')
            bindings.append((mtype, handler))
        self.bindings = bindings
        self.modified[self.opf_bookpath] = 'file'

    def spine_insert_before(self, pos, sid, linear, properties=None):
        sid = _unicodestr(sid)
        linear = _unicodestr(linear)
        properties = _unicodestr(properties)
        if properties is not None and properties == "":
            properties = None
        if sid not in self.id_to_mime:
            raise WrapperException('that spine idref does not exist in manifest')
        n = len(self.spine)
        if pos == 0:
            self.spine = [(sid, linear, properties)] + self.spine
        elif pos == -1 or pos >= n:
            self.spine.append((sid, linear, properties))
        else:
            self.spine = self.spine[0:pos] + [(sid, linear, properties)] + self.spine[pos:]
        self.modified[self.opf_bookpath] = 'file'

    def getspine_ppd(self):
        return self.spine_ppd

    def setspine_ppd(self, ppd):
        ppd = _unicodestr(ppd)
        if ppd not in ['rtl', 'ltr', None]:
            raise WrapperException('incorrect page-progression direction')
        self.spine_ppd = ppd
        self.modified[self.opf_bookpath] = 'file'

    def setspine_itemref_epub3_attributes(self, idref, linear, properties):
        idref = _unicodestr(idref)
        linear = _unicodestr(linear)
        properties = _unicodestr(properties)
        if properties is not None and properties == "":
            properties = None
        pos = -1
        i = 0
        for (sid, slinear, sproperties) in self.spine:
            if sid == idref:
                pos = i
                break
            i += 1
        if pos == -1:
            raise WrapperException('that idref is not exist in the spine')
        self.spine[pos] = (sid, linear, properties)
        self.modified[self.opf_bookpath] = 'file'

    # routines to get and set the guide
    def getguide(self):
        return self.guide

    # guide hrefs must be in urlencoded form (percent encodings present if needed)
    # as they may include fragments and # is a valid url path character
    def setguide(self, new_guide):
        guide = []
        for (type, title, href) in new_guide:
            type = _unicodestr(type)
            title = _unicodestr(title)
            href = _unicodestr(href)
            if type not in _guide_types:
                type = "other." + type
            if title is None:
                title = 'title missing'
            thref = unquote(href.split('#')[0])
            if thref not in self.href_to_id:
                raise WrapperException('guide href not in manifest')
            guide.append((type, title, href))
        self.guide = guide
        self.modified[self.opf_bookpath] = 'file'

    # routines to get and set metadata xml fragment
    def getmetadataxml(self):
        return self.metadataxml

    def setmetadataxml(self, new_metadata):
        self.metadataxml = _unicodestr(new_metadata)
        self.modified[self.opf_bookpath] = 'file'

    # routines to get and set the package tag
    def getpackagetag(self):
        return self.package_tag

    def setpackagetag(self, new_packagetag):
        pkgtag = _unicodestr(new_packagetag)
        version = ""
        mo = _PKG_VER.search(pkgtag)
        if mo:
            version = mo.group(1)
        if version != self.epub_version:
            raise WrapperException('Illegal to change the package version attribute')
        self.package_tag = pkgtag
        self.modified[self.opf_bookpath] = 'file'

    def set_manifest_epub3_attributes(self, id, properties=None, fallback=None, overlay=None):
        id = _unicodestr(id)
        properties = _unicodestr(properties)
        if properties is not None and properties == "":
            properties = None
        fallback = _unicodestr(fallback)
        if fallback is not None and fallback == "":
            fallback = None
        overlay = _unicodestr(overlay)
        if overlay is not None and overlay == "":
            overlay = None
        if id not in self.id_to_href:
            raise WrapperException('Id does not exist in manifest')
        del self.id_to_properties[id]
        del self.id_to_fallback[id]
        del self.id_to_overlay[id]
        self.id_to_properties[id] = properties
        self.id_to_fallback[id] = fallback
        self.id_to_overlay[id] = overlay
        self.modified[self.opf_bookpath] = 'file'






