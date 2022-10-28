#!/usr/bin/env python3
# coding: utf-8

__version__ = (0, 1)

from collections import OrderedDict
from xml.etree.ElementTree import fromstring

from uuid import uuid4

import mimetypes
import sys
import os
import re
import posixpath
from util.hrefutils import urldecodepart, urlencodepart
from util.hrefutils import buildBookPath, startingDir, buildRelativePath
from util.hrefutils import mime_group_map

from util.opf_parser import Opf_Parser

import unicodedata

def _utf8str(p):
    if p is None:
        return None
    if isinstance(p, bytes):
        return p
    return p.encode('utf-8', errors='replace')

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

TEXT_MIMETYPES = [
    'image/svg+xml',
    'application/xhtml+xml',
    'text/css',
    'application/x-dtbncx+xml',
    'application/oebps-package+xml',
    'application/oebs-page-map+xml',
    'application/smil+xml',
    'application/adobe-page-template+xml',
    'application/vnd.adobe-page-template+xml',
    'text/javascript',
    'application/javascript'
    'application/pls+xml'
]

MIME_OF_TEXT = frozenset(mime for mime, group in mime_group_map.items() if group == "Text")

def _epub_file_walk(top):
    top = os.fsdecode(top)
    rv = []
    for base, dnames, names in os.walk(top):
        for name in names:
            rv.append(os.path.relpath(os.path.join(base, name), top))
    return rv


def get_opfpath(dir_=""):
    path = os.path.join(dir_, "META-INF/container.xml")
    data_container_xml = open(path, "rb").read()
    tree = fromstring(data_container_xml)
    opf_bookpath = next(
        el2.attrib["full-path"]
        for el1 in tree if el1.tag == "rootfiles" or el1.tag.endswith("}rootfiles")
        for el2 in el1 if el2.tag == "rootfile" or el2.tag.endswith("}rootfile")
            if el2.attrib.get("media-type") == "application/oebps-package+xml"
    )
    return os.path.join(dir_, opf_bookpath), opf_bookpath

class WrapperException(Exception):
    pass

class Wrapper(object):

    def __init__(self, ebook_root):
        self.outdir = self.ebook_root = os.fsdecode(ebook_root)
        opfpath, opfbookpath = get_opfpath(ebook_root)
        self.opfbookpath = opfbookpath
        op = self.op = Opf_Parser(opfpath, opfbookpath)

        # dictionaries used to map opf manifest information
        # copy in data from parsing of initial opf
        self.opf_dir = op.opf_dir
        # Note: manifest hrefs may only point to files (there are no fragments)
        # all manifest relative hrefs have already had their path component url decoded
        self.id_to_href = op.get_manifest_id_to_href_dict().copy()
        self.id_to_mime = op.get_manifest_id_to_mime_dict().copy()
        self.id_to_props = op.get_manifest_id_to_properties_dict().copy()
        self.id_to_fall = op.get_manifest_id_to_fallback_dict().copy()
        self.id_to_over = op.get_manifest_id_to_overlay_dict().copy()
        self.id_to_bookpath = op.get_manifest_id_to_bookpath_dict().copy()
        self.group_paths = op.get_group_paths().copy()
        self.spine_ppd = op.get_spine_ppd()
        self.spine = op.get_spine()
        # since guide hrefs may contain framents they are kept in url encoded form
        self.guide = op.get_guide()
        self.package_tag = op.get_package_tag()
        self.epub_version = op.get_epub_version()
        self.bindings = op.get_bindings()
        self.metadataxml = op.get_metadataxml()
        # invert key dictionaries to allow for reverse access
        self.href_to_id = {v: k for k, v in self.id_to_href.items()}
        self.bookpath_to_id = {v: k for k, v in self.id_to_bookpath.items()}
        self.metadata = op.get_metadata()
        self.metadata_attr = op.get_metadata_attr()

        self.other = []  # non-manifest file information
        self.id_to_filepath = OrderedDict()
        self.book_href_to_filepath = OrderedDict()
        self.modified = OrderedDict()
        self.added = []
        self.deleted = []

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

    def getversion(self):
        global _launcher_version
        return _launcher_version

    def getepubversion(self):
        return self.epub_version

    # utility routine to get mime from href (book href or opf href)
    # no fragments present
    def getmime(self, href):
        href = _unicodestr(href)
        href = urldecodepart(href)
        return mimetypes.guess_type(href)[0]

    # New in Sigil 1.1
    # ------------------

    # returns color mode of Sigil "light" or "dark"
    def colorMode(self):
        return _unicodestr(self.colormode)

    # returns color as css or javascript hex color string #xxxxxx
    # Accepts the following color roles "Window", "Base", "Text", "Highlight", "HighlightedText"
    def color(self, role):
        role = _unicodestr(role)
        role = role.lower()
        color_roles = ["window", "base", "text", "highlight", "highlightedtext"]
        colors = self.colors.split(',')
        if role in color_roles:
            idx = color_roles.index(role)
            return _unicodestr(colors[idx])
        return None

    # New in Sigil 1.0
    # ----------------

    # A book path (aka "bookpath" or "book_path") is a unique relative path
    # from the ebook root to a specific file.  As a relative path meant to
    # be used in an href or src link it only uses forward slashes "/"
    # as path segment separators.  Since all files exist inside the
    # epub root (folder the epub was unzipped into), book paths will NEVER
    # have or use "./" or "../" ie they are in always in canonical form

    # We will use the terms book_href (aka "bookhref") interchangeabily
    # with bookpath with the following convention:
    #   - use book_href when working with "other" files outside of the manifest
    #   - use bookpath when working with files in the manifest
    #   - use either when the file in question in the OPF as it exists in the intersection

    # returns the bookpath/book_href to the opf file
    def get_opfbookpath(self):
        return self.opfbookpath

    # returns the book path to the folder containing this bookpath
    def get_startingdir(self, bookpath):
        bookpath = _unicodestr(bookpath)
        return startingDir(bookpath)

    # return a bookpath for the file pointed to by the href from
    # the specified bookpath starting directory
    # no fragments allowed in href (must have been previously split off)
    def build_bookpath(self, href, starting_dir):
        href = _unicodestr(href)
        href = urldecodepart(href)
        starting_dir = _unicodestr(starting_dir)
        return buildBookPath(href, starting_dir)

    # returns the href relative path from source bookpath to target bookpath
    def get_relativepath(self, from_bookpath, to_bookpath):
        from_bookpath = _unicodestr(from_bookpath)
        to_bookpath = _unicodestr(to_bookpath)
        return buildRelativePath(from_bookpath, to_bookpath)

    # ----------

    # routine to detect if the current epub is in Sigil standard epub form
    def epub_is_standard(self):
        groups = ["Text", "Styles", "Fonts", "Images", "Audio", "Video", "Misc"]
        paths = ["OEBPS/Text", "OEBPS/Styles", "OEBPS/Fonts", "OEBPS/Images", "OEBPS/Audio", "OEBPS/Video", "OEBPS/Misc"]
        std_epub = self.opfbookpath == "OEBPS/content.opf"
        tocid = self.gettocid()
        if tocid is not None:
            std_epub = std_epub and self.id_to_bookpath[tocid] == "OEBPS/toc.ncx"
        if self.epub_version.startswith("2"):
            std_epub = std_epub and tocid is not None
        for g, p in zip(groups, paths):
            folders = self.group_paths[g]
            std_epub = std_epub and folders[0] == p and len(folders) == 1
        return std_epub


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
                href = urlencodepart(href)
            mime = self.id_to_mime[id]
            props = ''
            properties = self.id_to_props[id]
            if properties is not None:
                props = ' properties="%s"' % properties
            fall = ''
            fallback = self.id_to_fall[id]
            if fallback is not None:
                fall = ' fallback="%s"' % fallback
            over = ''
            overlay = self.id_to_over[id]
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
        if self.op is not None:
            platpath = self.opfbookpath.replace('/', os.sep)
            filepath = os.path.join(self.outdir, platpath)
            base = os.path.dirname(filepath)
            if not os.path.exists(base):
                os.makedirs(base)
            with open(filepath, 'wb') as fp:
                data = _utf8str(self.build_opf())
                fp.write(data)


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
                properties = self.id_to_props[id]
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
        self.modified[self.opfbookpath] = 'file'

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
        self.modified[self.opfbookpath] = 'file'

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
        self.modified[self.opfbookpath] = 'file'

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
        self.modified[self.opfbookpath] = 'file'

    def getspine_ppd(self):
        return self.spine_ppd

    def setspine_ppd(self, ppd):
        ppd = _unicodestr(ppd)
        if ppd not in ['rtl', 'ltr', None]:
            raise WrapperException('incorrect page-progression direction')
        self.spine_ppd = ppd
        self.modified[self.opfbookpath] = 'file'

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
        self.modified[self.opfbookpath] = 'file'


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
            thref = urldecodepart(href.split('#')[0])
            if thref not in self.href_to_id:
                raise WrapperException('guide href not in manifest')
            guide.append((type, title, href))
        self.guide = guide
        self.modified[self.opfbookpath] = 'file'


    # routines to get and set metadata xml fragment

    def getmetadataxml(self):
        return self.metadataxml

    def setmetadataxml(self, new_metadata):
        self.metadataxml = _unicodestr(new_metadata)
        self.modified[self.opfbookpath] = 'file'


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
        self.modified[self.opfbookpath] = 'file'

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
        del self.id_to_props[id]
        del self.id_to_fall[id]
        del self.id_to_over[id]
        self.id_to_props[id] = properties
        self.id_to_fall[id] = fallback
        self.id_to_over[id] = overlay
        self.modified[self.opfbookpath] = 'file'


    # helpful mapping routines for file info from the opf manifest

    def map_href_to_id(self, href, ow):
        href = _unicodestr(href)
        href = urldecodepart(href)
        return self.href_to_id.get(href, ow)

    # new in Sigil 1.0
    def map_bookpath_to_id(self, bookpath, ow):
        bookpath = _unicodestr(bookpath)
        return self.bookpath_to_id.get(bookpath, ow)

    def map_basename_to_id(self, basename, ow):
        for bookpath in self.bookpath_to_id:
            filename = bookpath.split("/")[-1]
            if filename == basename:
                return self.bookpath_to_id[bookpath]
        return ow

    def map_id_to_href(self, id, ow):
        id = _unicodestr(id)
        return self.id_to_href.get(id, ow)

    # new in Sigil 1.0
    def map_id_to_bookpath(self, id, ow):
        id = _unicodestr(id)
        return self.id_to_bookpath.get(id, ow)

    def map_id_to_mime(self, id, ow):
        id = _unicodestr(id)
        return self.id_to_mime.get(id, ow)

    def map_id_to_properties(self, id, ow):
        id = _unicodestr(id)
        return self.id_to_props.get(id, ow)

    def map_id_to_fallback(self, id, ow):
        id = _unicodestr(id)
        return self.id_to_fall.get(id, ow)

    def map_id_to_overlay(self, id, ow):
        id = _unicodestr(id)
        return self.id_to_over.get(id, ow)

    # new in Sigil 1.0
    # returns a sorted folder list for that group
    # valid groups: Text, Styles, Images, Fonts, Audio, Video, ncx, opf, Misc
    def map_group_to_folders(self, group, ow):
        group = _unicodestr(group)
        return self.group_paths.get(group, ow)

    # new in Sigil 1.0
    def map_mediatype_to_group(self, mtype, ow):
        mtype = _unicodestr(mtype)
        return mime_group_map.get(mtype, ow)

    # utility routine to copy entire ebook to a destination directory
    # including the any prior updates and changes to the opf

    def copy_book_contents_to(self, destdir):
        destdir = _unicodestr(destdir)
        if destdir is None or not os.path.isdir(destdir):
            raise WrapperException('destination directory does not exist')
        for id in self.id_to_filepath:
            rpath = self.id_to_filepath[id]
            data = self.readfile(id)
            filepath = os.path.join(destdir, rpath)
            base = os.path.dirname(filepath)
            if not os.path.exists(base):
                os.makedirs(base)
            if isinstance(data, str):
                data = _utf8str(data)
            with open(filepath, 'wb') as fp:
                fp.write(data)
        for id in self.book_href_to_filepath:
            rpath = self.book_href_to_filepath[id]
            data = self.readotherfile(id)
            filepath = os.path.join(destdir, rpath)
            base = os.path.dirname(filepath)
            if not os.path.exists(base):
                os.makedirs(base)
            if isinstance(data, str):
                data = _utf8str(data)
            with open(filepath, 'wb') as fp:
                fp.write(data)

    def addfile(self, bookpath, uniqueid=None, mime=None, properties=None, fallback=None, overlay=None):
        bookpath = _unicodestr(bookpath).replace(os.sep, "/")
        basename = os.path.basename(bookpath)
        if uniqueid is None:
            uniqueid = basename
            if uniqueid in self.id_to_href:
                uniqueid = str(uuid4())
        else:
            uniqueid = _unicodestr(uniqueid)
            if uniqueid in self.id_to_href:
                raise WrapperException('Manifest Id is not unique')
        mime = _unicodestr(mime)
        if mime is None:
            mime = mimetypes.guess_type(basename)[0]
        if mime is None:
            raise WrapperException("Mime Type Missing")
        if mime == "application/x-dtbncx+xml" and self.epub_version.startswith("2"):
            raise WrapperException('Can not add or remove an ncx under epub2')
        href = buildRelativePath(self.opfbookpath, bookpath)
        if href in self.href_to_id:
            raise WrapperException('bookpath already exists')
        # now actually write out the new file
        filepath = bookpath.replace("/", os.sep)
        self.id_to_filepath[uniqueid] = filepath
        self.id_to_href[uniqueid] = href
        self.id_to_mime[uniqueid] = mime
        self.id_to_props[uniqueid] = properties
        self.id_to_fall[uniqueid] = fallback
        self.id_to_over[uniqueid] = overlay
        self.id_to_bookpath[uniqueid] = bookpath
        self.href_to_id[href] = uniqueid
        self.bookpath_to_id[bookpath] = uniqueid

        # add to spine
        if mime in MIME_OF_TEXT:
            self.spine.append((uniqueid, "no", None))

        return uniqueid, bookpath, mime

    def addfile_by_href(self, href, uniqueid=None, mime=None, properties=None, fallback=None, overlay=None):
        bookpath = posixpath.join(self.opf_dir, href)
        self.addfile(bookpath, uniqueid=uniqueid, mime=mime, 
                     properties=properties, fallback=fallback, overlay=overlay)

    def deletefile(self, id):
        id = _unicodestr(id)
        if id not in self.id_to_href:
            raise WrapperException('Id does not exist in manifest')
        filepath = self.id_to_filepath.get(id, None)
        if id is None:
            raise WrapperException('Id does not exist in manifest')
        if self.epub_version.startswith("2") and id == self.gettocid():
            raise WrapperException('Can not add or remove an ncx under epub2')

        # remove from manifest
        href = self.id_to_href[id]
        bookpath = self.id_to_bookpath[id]
        mime = self.id_to_mime[id]
        del self.id_to_href[id]
        del self.id_to_mime[id]
        del self.id_to_props[id]
        del self.id_to_fall[id]
        del self.id_to_over[id]
        del self.id_to_bookpath[id]
        del self.href_to_id[href]
        del self.bookpath_to_id[bookpath]

        # remove from spine
        new_spine = []
        was_modified = False
        for sid, linear, properties in self.spine:
            if sid != id:
                new_spine.append((sid, linear, properties))
            else:
                was_modified = True
        if was_modified:
            self.setspine_epub3(new_spine)

        del self.id_to_filepath[id]

        return id, bookpath, mime

    def deletefile_by_href(self, book_href):
        id = self.href_to_id[_unicodestr(book_href)]
        return self.deletefile(id)

    def deletefile_by_path(self, bookpath):
        id = self.bookpath_to_id[_unicodestr(bookpath)]
        return self.deletefile(id)

# iterators

    def text_iter(self):
        # yields manifest id, href in spine order plus any non-spine items
        text_set = set([k for k, v in self.id_to_mime.items() if v == 'application/xhtml+xml'])
        for (id, linear, properties) in self.spine:
            if id in text_set:
                text_set -= set([id])
                href = self.id_to_href[id]
                yield id, href
        for id in text_set:
            href = self.id_to_href[id]
            yield id, href

    def css_iter(self):
        # yields manifest id, href
        for id in sorted(self.id_to_mime):
            mime = self.id_to_mime[id]
            if mime == 'text/css':
                href = self.id_to_href[id]
                yield id, href

    def image_iter(self):
        # yields manifest id, href, and mimetype
        for id in sorted(self.id_to_mime):
            mime = self.id_to_mime[id]
            if mime.startswith('image'):
                href = self.id_to_href[id]
                yield id, href, mime

    def font_iter(self):
        # yields manifest id, href, and mimetype
        for id in sorted(self.id_to_mime):
            mime = self.id_to_mime[id]
            if 'font-' in mime or 'truetype' in mime or 'opentype' in mime or mime.startswith('font/'):
                href = self.id_to_href[id]
                yield id, href, mime

    def manifest_iter(self):
        # yields manifest id, href, and mimetype
        for id in sorted(self.id_to_mime):
            mime = self.id_to_mime[id]
            href = self.id_to_href[id]
            yield id, href, mime

    # New for epub3
    def manifest_epub3_iter(self):
        # yields manifest id, href, mimetype, properties, fallback, media-overlay
        for id in sorted(self.id_to_mime):
            mime = self.id_to_mime[id]
            href = self.id_to_href[id]
            properties = self.id_to_props[id]
            fallback = self.id_to_fall[id]
            overlay = self.id_to_over[id]
            yield id, href, mime, properties, fallback, overlay

    def spine_iter(self):
        # yields spine idref, linear(yes,no,None), href in spine order
        for (id, linear, properties) in self.spine:
            href = self.id_to_href[id]
            yield id, linear, href

    # New for epub3
    def spine_epub3_iter(self):
        # yields spine idref, linear(yes,no,None), properties, href in spine order
        for (id, linear, properties) in self.spine:
            href = self.id_to_href[id]
            yield id, linear, properties, href


    def guide_iter(self):
        # yields guide reference type, title, href, and manifest id of href
        for (type, title, href) in self.guide:
            thref = href.split('#')[0]
            id = self.href_to_id.get(thref, None)
            yield type, title, href, id

    # New for epub3
    def bindings_epub3_iter(self):
        # yields media-type handler in bindings order
        for (mtype, handler) in self.bindings:
            handler_href = self.id_to_href[handler]
            yield mtype, handler, handler_href


    def media_iter(self):
        # yields manifest, title, href, and manifest id of href
        for id in sorted(self.id_to_mime):
            mime = self.id_to_mime[id]
            if mime.startswith('audio') or mime.startswith('video'):
                href = self.id_to_href[id]
                yield id, href, mime

    def selected_iter(self):
        # yields id type ('other' or 'manifest') and id/otherid for each file selected in the BookBrowser
        for book_href in self.selected:
            id_type = 'other'
            id = book_href
            if book_href in self.bookpath_to_id:
                id_type = 'manifest'
                id = self.bookpath_to_id[book_href]
            yield id_type, id


