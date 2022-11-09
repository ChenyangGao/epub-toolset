#!/usr/bin/env python3
# coding: utf-8

__author__  = "ChenyangGao <https://chenyanggao.github.io/>"
__version__ = (0, 1, 1)
__all__ = ["OpfWrapper", "ManifestItem", "SpineItemref"]

from os import PathLike
from typing import AnyStr, Iterator, NamedTuple, Optional, Union

from lxml.etree import Element, _Element

from util.mapper import Mapper
from util.mimetype import guess_mimetype
from util.makeid import makeid
from util.opfparser import OpfParser


SPINE_CONCERNED_MIMES = ["text/html", "application/xhtml+xml"]


class ManifestItem(NamedTuple):
    id: str
    href: str
    bookpath: str
    media_type: str = "application/octet-stream"
    properties: Optional[str] = None
    fallback: Optional[str] = None
    media_overlay: Optional[str] = None


class SpineItemref(NamedTuple):
    idref: str
    id: Optional[str] = None
    linear: Optional[str] = None
    properties: Optional[str] = None


class OpfWrapper(OpfParser):

    def __init__(self, ebook_root: AnyStr | PathLike[AnyStr] = ""):
        super().__init__(ebook_root)

        # Invert key dictionaries to allow for reverse access
        self.id_to_bookpath = Mapper((id, self.id_to_bookpath(id)) for id in self.manifest_map)
        self.href_to_id = Mapper((self.id_to_href(id), id) for id in self.manifest_map)
        self.bookpath_to_id = Mapper((self.id_to_bookpath(id), id) for id in self.manifest_map)

    def has(
        self, 
        id: Optional[str] = None, 
        href: Optional[str] = None, 
        bookpath: Optional[str] = None, 
    ) -> bool:
        if id is not None:
            return id in self.manifest_map
        elif href is not None:
            return href in self.href_to_id
        elif bookpath is not None:
            return href in self.bookpath_to_id
        return False

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
                id = self.href_to_id(href)
            except KeyError as e:
                raise ValueError(
                    f"href {href!r} does not exist in manifest!") from e
        elif bookpath is not None:
            try:
                id = self.bookpath_to_id(bookpath)
            except KeyError as e:
                raise KeyError(
                    f"Bookpath {bookpath!r} does not exist in manifest!") from e
        else:
            raise ValueError("Give (not None) at least one of arguments: "
                             "id, href or bookpath")

        item = self.manifest_map[id]
        return ManifestItem(
            id            = id, 
            href          = item.attrib["href"], 
            bookpath      = self.id_to_bookpath(id), 
            media_type    = item.get("media-type", "application/octet-stream"), 
            properties    = item.get("properties"), 
            fallback      = item.get("fallback"), 
            media_overlay = item.get("media-overlay"), 
        )

    def add(
        self, 
        path: Union[None, AnyStr, PathLike[AnyStr]] = None, 
        bookpath: Optional[str] = None, 
        href: Optional[str] = None, 
        id: Optional[str] = None, 
        media_type: Optional[str] = None, 
        properties: Optional[dict] = None, 
        fallback: Optional[str] = None, 
        media_overlay: Optional[str] = None, 
    ) -> ManifestItem:
        if path is not None:
            bookpath = self.path_to_bookpath(path)
            href = self.bookpath_to_href(bookpath)
        elif bookpath is not None:
            href = self.bookpath_to_href(bookpath)
        elif href is not None:
            bookpath = self.href_to_bookpath(href)
        else:
            raise ValueError("Give (not None) at least one of arguments: "
                             "path, bookpath or href")

        if id is None:
            id = makeid(href, bookpath, self.manifest_map.keys())
        elif id in self.manifest_map:
            raise ValueError(f"Id {id} is already exist in manifest")

        if media_type is None:
            media_type = guess_mimetype(href)
        if media_type is None:
            raise ValueError("Unable to determine media-type (media_type)")

        attrib = {"id": id, "href": href, "media-type": media_type}
        if properties is not None:
            attrib["properties"] = properties
        if fallback is not None:
            attrib["fallback"] = fallback
        if media_overlay is not None:
            attrib["media-overlay"] = media_overlay
        el = Element("item", attrib)
        self.manifest.append(el)
        self.manifest_map[id] = el
        item = ManifestItem(
            id            = id, 
            href          = href, 
            bookpath      = bookpath, 
            media_type    = media_type, 
            properties    = properties, 
            fallback      = fallback, 
            media_overlay = media_overlay, 
        )
        self.id_to_bookpath[id] = bookpath
        self.href_to_id[href] = id
        self.bookpath_to_id[bookpath] = id

        if media_type in SPINE_CONCERNED_MIMES:
            el = Element("itemref", {"idref": id})
            self.spine.append(el)
            self.spine_map[id] = el

        return item

    def delete(
        self, 
        id: Optional[str] = None, 
        href: Optional[str] = None, 
        bookpath: Optional[str] = None, 
    ) -> ManifestItem:
        item = self.get(id, href, bookpath)

        el = self.manifest_map.pop(item.id)
        self.manifest.remove(el)

        del self.id_to_bookpath[item.id]
        del self.href_to_id[item.href]
        del self.bookpath_to_id[item.bookpath]

        if item.id in self.spine_map:
            el = self.spine_map.pop(item.id)
            self.spine.remove(el)

        return item

    def gettocid(self):
        # To find the manifest id of toc.ncx
        return next((
            id for id, item in self.manifest_map.items()
            if item.get("media-type") == "application/x-dtbncx+xml"
        ), None)

    def getpagemapid(self):
        # To find the manifest id of page-map.xml
        return next((
            id for id, item in self.manifest_map.items()
            if item.get("media-type") == "application/oebs-page-map+xml"
        ), None)

    def getnavid(self):
        # To find the manifest id of nav.xhtml
        if self.epub < "3.0":
            return None
        return next((
            id for id, item in self.manifest_map.items()
            if item.get("media-type") == "application/xhtml+xml"
                and "nav" in item.get("properties", "")
        ), None)

    def manifest_iter(self) -> Iterator[ManifestItem]:
        yield from map(self.get, self.manifest_map)

    def text_iter(self) -> Iterator[ManifestItem]:
        spine_map = self.spine_map
        for id, item in self.manifest_map.items():
            if id in spine_map and spine_map[id].get("linear") != "no" or \
                    item.get("media-type") in ("text/html", "application/xhtml+xml"):
                yield self.get(id)

    def spine_iter(self) -> Iterator[SpineItemref]:
        for idref, itemref in self.spine_map.items():
            yield SpineItemref(
                idref=idref, 
                id=itemref.get("id"), 
                linear=itemref.get("linear"), 
                properties=itemref.get("properties"), 
            )

