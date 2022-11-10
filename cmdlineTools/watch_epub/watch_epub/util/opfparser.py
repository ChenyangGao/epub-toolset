#!/usr/bin/env python3
# coding: utf-8

__author__  = "ChenyangGao <https://chenyanggao.github.io/>"
__version__ = (0, 1, 2)
__all__ = ["get_opf_bookpath", "OpfParser"]

# Reference:
#   - https://www.w3.org/publishing/epub3/epub-packages.html
#   - https://www.w3.org/community/epub3/

import os.path as syspath
import posixpath

from os import fsdecode, PathLike
from typing import AnyStr, Optional, Union

from lxml.etree import _Element, _ElementTree

from util.lxmlparser import xml_fromstring, xml_tostring
from util.pathutils import path_to_posix, path_posix_to_sys


def get_opf_bookpath(ebook_root: AnyStr | PathLike[AnyStr] = "") -> str:
    path_to_container_xml = syspath.join(
        fsdecode(ebook_root), "META-INF", "container.xml")
    tree = xml_fromstring(open(path_to_container_xml, "rb").read())
    # > See: https://www.w3.org/publishing/epub32/epub-ocf.html#sec-container-metainf-container.xml
    # An OCF Processor *MUST* consider the first **rootfile** element within the **rootfiles** element 
    # to represent the [Default Rendition](https://www.w3.org/publishing/epub32/epub-ocf.html#dfn-default-rendition) 
    # for the contained EPUB Publication. [Reading Systems](https://www.w3.org/publishing/epub32/epub-spec.html#dfn-epub-reading-system) 
    # are *REQUIRED* to present the Default Rendition, but *MAY* present other Renditions in the container.
    matched = tree.xpath('//*[name()="rootfiles"]/*[name()="rootfile"]/@full-path')
    try:
        return matched[0]
    except IndexError:
        raise ValueError("The OPF file path is not defined in OCF file")


class OpfParser:

    def __init__(self, ebook_root: AnyStr | PathLike[AnyStr] = ""):
        self.ebook_root: str = fsdecode(syspath.realpath(ebook_root))
        self.opf_bookpath: str = get_opf_bookpath(ebook_root)
        self.opf_path: str = self.bookpath_to_path(self.opf_bookpath)
        self.opf_dir: str
        self.opf_name: str
        self.opf_dir, self.opf_name = posixpath.split(self.opf_bookpath)
        if self.opf_dir:
            self.opf_dir += "/"

        self.opf: _ElementTree
        self.package: _Element
        self.metadata: _Element
        self.manifest: _Element
        self.spine: _Element
        self.guide: Optional[_Element]
        self.bindings: Optional[_Element]
        self.collections: list[_Element]
        self.load()

    def load(self):
        self.loads(open(self.opf_path, "rb").read())

    def loads(self, text: Union[bytes, str]):
        # See: https://www.w3.org/publishing/epub32/epub-packages.html#sec-package-elem
        root = xml_fromstring(text)
        if root.xpath("name()") != "package":
            raise ValueError("The root element is not <package>")
        self.opf = root.getroottree()
        self.package = root
        if not root.get("version"):
            root.set("version", "3.0")
        if not root.get("unique-identifier"):
            root.set("unique-identifier", "bookid")

        metadata = root[0]
        if metadata.xpath("name()") != "metadata":
            raise ValueError
        self.metadata = metadata

        manifest = root[1]
        if manifest.xpath("name()") != "manifest":
            raise ValueError
        self.manifest = manifest
        manifest_map = self.manifest_map = {}
        for item in manifest:
            if item.xpath("name()") == "item":
                manifest_map[item.attrib["id"]] = item

        spine = root[2]
        if spine.xpath("name()") != "spine":
            raise ValueError
        self.spine = spine
        spine_map = self.spine_map = {}
        for itemref in spine:
            if itemref.xpath("name()") == "itemref":
                spine_map[itemref.attrib["idref"]] = itemref

        self.guide = None
        self.bindings = None
        self.collections = []
        for el in root[3:]:
            name = el.xpath("name()")
            # TODO: "guide/reference/@href" associated with local files 
            #     (and may have fragments, i.e. hashtag). Thus, when a local 
            #     file is renamed or modified, the link should also be repaired.
            # See: https://idpf.org/epub/20/spec/OPF_2.0_final_spec.html#Section2.6
            if name == "guide": # LEGACY
                self.guide = el
            elif name == "bindings": # DEPRECATED
                self.bindings = el
            elif name == "collection":
                self.collections.append(el)

    def dump(self):
        open(self.opf_path, "wb").write(self.dumps())

    def dumps(self) -> bytes:
        return xml_tostring(self.opf, pretty_print=True)

    def __enter__(self):
        return self

    def __exit__(self, ext_type, exc_value, exc_tb):
        if ext_type is None:
            self.dump()

    @property
    def version(self) -> str:
        return self.package.attrib["version"]

    def bookpath_to_href(self, bookpath: str) -> str:
        return posixpath.relpath(bookpath, self.opf_dir)

    def bookpath_to_path(self, bookpath: str) -> str:
        return syspath.join(
            self.ebook_root, 
            path_posix_to_sys(bookpath), 
        )

    def href_to_bookpath(self, href: str) -> str:
        return posixpath.join(self.opf_dir, href)

    def href_to_path(self, href: str) -> str:
        bookpath = self.href_to_bookpath(href)
        return self.bookpath_to_path(bookpath)

    def path_to_bookpath(self, path: Union[AnyStr, PathLike[AnyStr]]) -> str:
        path_: str = fsdecode(syspath.realpath(path))
        if not path_.startswith(self.ebook_root):
            raise ValueError(f"{path!r} is not in the directory {self.ebook_root!r}")
        return path_to_posix(syspath.relpath(path_, self.ebook_root))

    def path_to_href(self, path: Union[AnyStr, PathLike[AnyStr]]) -> str:
        bookpath = self.path_to_bookpath(path)
        return self.bookpath_to_href(bookpath)

    def id_to_href(self, id: str) -> str:
        return self.manifest_map[id].attrib["href"]

    def id_to_bookpath(self, id: str) -> str:
        href = self.id_to_href(id)
        return self.href_to_bookpath(href)

    def id_to_media_type(self, id: str) -> str:
        return self.manifest_map[id].attrib["media-type"]

    def id_to_properties(self, id: str) -> Optional[str]:
        return self.manifest_map[id].get("properties")

    def id_to_fallback(self, id: str) -> Optional[str]:
        return self.manifest_map[id].get("fallback")

    def id_to_media_overlay(self, id: str) -> Optional[str]:
        return self.manifest_map[id].get("media-overlay")

    def id_to_spine_itemref(self, id: str):
        return self.spine_map[id]

