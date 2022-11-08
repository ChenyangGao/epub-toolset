#!/usr/bin/env python3
# coding: utf-8

# Reference:
#   - https://www.w3.org/publishing/epub3/epub-packages.html
#   - https://www.w3.org/community/epub3/

__version__ = (0, 1, 1)

import sys
import os
import os.path as syspath
import posixpath

from os import fsdecode, PathLike
from re import search as re_search
from typing import AnyStr
from urllib.parse import unquote

from util.light_xml_parser import fromstring
from util.mapper import Mapper
from util.pathutils import reference_path, path_posix_to_sys


SPECIAL_HANDLING_TAGS = dict([
    ("?xml", ("xmlheader", -1)),
    ("!--", ("comment", -3)),
    ("!DOCTYPE", ("doctype", -1))
])

SPECIAL_HANDLING_TYPES = ["xmlheader", "doctype", "comment"]

_OPF_PARENT_TAGS = [
    "package", "metadata", "dc-metadata", "x-metadata", 
    "manifest", "spine", "tours", "guide", "bindings", 
    "collection"
]



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


# TODO: 用正则表达式实现，或者使用jsonpath
def get_opf_bookpath(ebook_root: AnyStr | PathLike[AnyStr] = "") -> str:
    path_to_container_xml = syspath.join(
        fsdecode(ebook_root), "META-INF", "container.xml")
    tree = fromstring(open(path_to_container_xml, "r", encoding="utf-8").read())
    # > See: https://www.w3.org/publishing/epub32/epub-ocf.html#sec-container-metainf-container.xml
    # An OCF Processor *MUST* consider the first **rootfile** element within the **rootfiles** element 
    # to represent the [Default Rendition](https://www.w3.org/publishing/epub32/epub-ocf.html#dfn-default-rendition) 
    # for the contained EPUB Publication. [Reading Systems](https://www.w3.org/publishing/epub32/epub-spec.html#dfn-epub-reading-system) 
    # are *REQUIRED* to present the Default Rendition, but *MAY* present other Renditions in the container.
    try:
        return matched[0].attrib["full-path"]
    except (IndexError, KeyError):
        raise ValueError("The OPF file path is not defined in OCF file")


class OpfParser:

    def __init__(self, ebook_root: AnyStr | PathLike[AnyStr] = ""):
        self.ebook_root = fsdecode(syspath.realpath(ebook_root))
        opf_bookpath = self.opf_bookpath = get_opf_bookpath(ebook_root)
        opf_path = self.opf_path = self.get_path(opf_bookpath)
        self.opf_dir, self.opf_name = posixpath.split(opf_bookpath)
        if self.opf_dir:
            self.opf_dir += "/"
        self.opf = open(opf_path, "r", encoding="utf-8").read()
        self._opf_etree = fromstring(self.opf)

        self.package = None
        self.metadata = []
        self.manifest = Mapper()
        self.spine = Mapper()
        self.guide = []
        self.bindings = []
        self.collections = []

        self._parseData()


    # now parse the OPF to extract manifest, spine , and metadata
    def _parseData(self):
        cnt = 0
        for prefix, tname, tattr, tcontent in self._opf_tag_iter():
            # package
            if tname == "package":
                # TODO: 默认版本改成3.0
                ver = tattr.pop("version", "2.0")
                uid = tattr.pop("unique-identifier", "bookid")
                self.package = (ver, uid, tattr)
                continue
            # metadata
            if tname == "metadata":
                self.metadata_attr = tattr
                continue
            if tname in ["meta", "link"] or tname.startswith("dc:") and "metadata" in prefix:
                self.metadata.append((tname, tattr, tcontent))
                continue
            # manifest
            # Note: manifest hrefs when relative may not contain a fragment
            # as they must refer to and entire file
            if tname == "item" and "manifest" in prefix:
                nid = "xid%03d" % cnt
                cnt += 1
                id = tattr.pop("id", nid)
                href = tattr.pop("href", '')
                mtype = tattr.pop("media-type", '')
                if mtype == "text/html":
                    mtype = "application/xhtml+xml"
                # url decode all relative hrefs since no fragment can be present
                # meaning no ambiguity in the meaning of any # chars in path
                if href.find(':') == -1:
                    href = unquote(href)
                properties = tattr.pop("properties", None)
                fallback = tattr.pop("fallback", None)
                overlay = tattr.pop("media-overlay", None)

                # external resources are now allowed in the opf under epub3
                self.id_to_href[id] = href

                bookpath = ""
                if href.find(":") == -1:
                    bookpath = reference_path(self.opf_dir, href, "/")

                self.id_to_bookpath[id] = bookpath
                self.id_to_mime[id] = mtype
                self.id_to_properties[id] = properties
                self.id_to_fallback[id] = fallback
                self.id_to_overlay[id] = overlay

                continue
            # spine
            if tname == "itemref" and "spine" in prefix:
                idref = tattr.pop("idref", "")
                linear = tattr.pop("linear", None)
                properties = tattr.pop("properties", None)
                self.spine.append((idref, linear, properties))
                continue
            # guide
            # Note: guide hrefs may have fragments, so leave any
            # guide hrefs in their raw urlencoded form to prevent
            # errors
            if tname == "reference" and "guide" in prefix:
                type = tattr.pop("type", '')
                title = tattr.pop("title", '')
                href = tattr.pop("href", '')
                self.guide.append((type, title, href))
                continue
            # bindings (stored but ignored for now)
            if tname in ["mediaType", "mediatype"] and "bindings" in prefix:
                mtype = tattr.pop("media-type", "")
                handler = tattr.pop("handler", "")
                self.bindings.append((mtype, handler))
                continue

    @property
    def epub_version(self):
        (ver, uid, tattr) = self.package
        return ver

    @property
    def package_tag(self):
        (ver, uid, tattr) = self.package
        packout = []
        packout.append('<package version="%s" unique-identifier="%s"' % (ver, uid))
        if tattr is not None:
            for key in tattr:
                val = self.handle_quoted_attribute_values(tattr[key])
                packout.append(' %s="%s"' % (key, val))
        packout.append(">\n")
        return "".join(packout)

    @property
    def metadataxml(self):
        data = []
        tattr = self.metadata_attr
        tag = "<metadata"
        if tattr is not None:
            for key in tattr:
                val = self.handle_quoted_attribute_values(tattr[key])
                tag += ' ' + key + '="' + val + '"'
        tag += '>\n'
        data.append(tag)
        for taginfo in self.metadata:
            data.append(self.taginfo_toxml(taginfo))
        data.append('</metadata>\n')
        return "".join(data)




    def id_to_href(self, id):
        return self.manifest[id].href

    def id_to_bookpath(self, id):
        return self.manifest[id].bookpath

    def id_to_mime(self, id):
        return self.manifest[id].mime

    def id_to_properties(self, id):
        return self.manifest[id].properties

    def id_to_fallback(self, id):
        return self.manifest[id].fallback

    def id_to_overlay(self, id):
        return self.manifest[id].overlay

    def id_to_spine(self, id):
        return self.spine[id]

