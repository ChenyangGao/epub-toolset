#!/usr/bin/env python3
# coding: utf-8

from __future__ import annotations

__author__  = "ChenyangGao <https://chenyanggao.github.io/>"
__version__ = (0, 0, 1)
__all__ = ["XMLItem", "XMLElement", "fromstring", "tostring"]

from dataclasses import dataclass, field
from html import escape, unescape
from re import compile as re_compile
from typing import Generator, NamedTuple, Optional


cre_starttagopen = re_compile(r'<[a-zA-Z]')
cre_tagfind_tolerant = re_compile(r'([a-zA-Z][^\s/>\x00]*)(?:\s|/(?!>))*')
cre_attrfind_tolerant = re_compile(
    r'(?P<attr>(?<=[\'"\s/])[^\s/>][^\s/=>]*)(\s*=+\s*(?P<value>\'(?P<v1>[^\']*)\''
    r'|"(?P<v2>[^"]*)"|(?P<v3>(?![\'"])[^>\s]*)))?(?:\s|/(?!>))*') 


class XMLItem(NamedTuple):
    type: str
    data: str
    raw: str

    def __abs__(self) -> str:
        return self.raw

    def __str__(self) -> str:
        return self.data

    @staticmethod
    def pi(raw: str) -> XMLItem:
        return XMLItem("pi", raw[2:-1], raw)

    @staticmethod
    def decl(raw: str) -> XMLItem:
        return XMLItem("decl", raw[2:-1], raw)

    @staticmethod
    def comment(raw: str) -> XMLItem:
        return XMLItem("comment", raw[4:-3], raw)

    @staticmethod
    def starttag(raw: str) -> XMLItem:
        return XMLItem("starttag", raw[1:-1], raw)

    @staticmethod
    def endtag(raw: str) -> XMLItem:
        return XMLItem("endtag", raw[2:-1], raw)

    @staticmethod
    def startendtag(raw: str) -> XMLItem:
        return XMLItem("startendtag", raw[1:-2], raw)

    @staticmethod
    def unknowntag(raw: str) -> XMLItem:
        return XMLItem("unknowntag", raw[1:-1], raw)

    @staticmethod
    def text(raw: str) -> XMLItem:
        return XMLItem("text", raw, raw)

    @staticmethod
    def parse_iter(xml_text: str) -> Generator[XMLItem, None, None]:
        # next tag begin
        ntb: int
        # tag begin
        te: int
        pos: int = 0
        pos_stop: int = len(xml_text)
        startswith = xml_text.startswith
        find = xml_text.find
        while pos < pos_stop:
            if startswith("<", pos):
                if startswith("<!--", pos):
                    te = find('-->', pos+4)
                    if te == -1:
                        raise ValueError("Comment tag is not closed, at pos %d" % pos)
                    te += 3
                    yield XMLItem.comment(xml_text[pos:te])
                    pos = te
                    continue
                te = find(">", pos)
                if te == -1:
                    raise ValueError("Tag is not closed, at pos %d" % pos)
                te += 1
                if startswith("</", pos):
                    yield XMLItem.endtag(xml_text[pos:te])
                elif startswith("<?", pos):
                    yield XMLItem.pi(xml_text[pos:te])
                elif startswith("<!", pos):
                    yield XMLItem.decl(xml_text[pos:te])
                elif cre_starttagopen.match(xml_text, pos):
                    if xml_text.endswith("/>", pos, te):
                        yield XMLItem.startendtag(xml_text[pos:te])
                    else:
                        yield XMLItem.starttag(xml_text[pos:te])
                else:
                    yield XMLItem.unknowntag(xml_text[pos:te])
                pos = te
            else:
                ntb = find("<", pos)
                if ntb == -1:
                    ntb = pos_stop
                yield XMLItem.text(xml_text[pos:ntb])
                pos = ntb


@dataclass
class XMLElement:
    type: str = "element"
    tag: str = ""
    attrib: dict[str, Optional[str]] = field(default_factory=dict)
    parent: Optional[XMLElement] = None
    children: list[XMLElement] = field(default_factory=list)
    text_content: str = ""
    tail_content: str = ""

    def __repr__(self):
        return f"<{type(self).__qualname__} {self.type!r} at {hex(id(self))}>"

    def __str__(self):
        return tostring(self, indent="  ")

    @property
    def text(self):
        return unescape(self.text_content)

    @text.setter
    def text(self, text: str):
        self.text_content = escape(text)

    @property
    def tail(self):
        return unescape(self.tail_content)

    @tail.setter
    def tail(self, text: str):
        self.tail_content = escape(text)


def fromstring(s) -> XMLElement:
    def parse_tag(data):
        tag = ""
        start = 0
        if (m := cre_tagfind_tolerant.match(data)):
            tag = m[0].rstrip().lower()
            m.end()
        attrib = {
            m["attr"]: get_attrval(m)
            for m in
            cre_attrfind_tolerant.finditer(data, start)
        }
        return tag, attrib

    def get_attrval(m):
        if m['value'] is not None:
            v1, v2, v3 = m['v1'], m['v2'], m['v3']
            if v1 is not None:
                return unescape(v1)
            elif v2 is not None:
                return unescape(v2)
            else:
                return unescape(v3)
        return None

    root = XMLElement("root")
    stack = [root]
    isopen = True
    prev = root
    for item in XMLItem.parse_iter(s):
        item_type = item.type
        if item_type == "starttag":
            tag, attrib = parse_tag(item.data)
            el = XMLElement(tag=tag, attrib=attrib, parent=stack[-1])
            stack[-1].children.append(el)
            stack.append(el)
        elif item_type == "endtag":
            matched = cre_tagfind_tolerant.search(item.data)
            if not matched:
                raise ValueError("End tag name not found!")
            tag = matched[0].rstrip().lower()
            if tag != stack[-1].tag:
                raise ValueError(
                    f"Start tag <{stack[-1].tag}> and end tag <{tag}> are not match!")
            prev = stack.pop()
        elif item_type == "startendtag":
            tag, attrib = parse_tag(item.data)
            el = XMLElement(tag=tag, attrib=attrib, parent=stack[-1])
            stack[-1].children.append(el)
        elif item_type == "pi":
            tag, attrib = parse_tag(item.data)
            el = XMLElement("pi", tag=tag, attrib=attrib, parent=stack[-1])
            stack[-1].children.append(el)
        elif item_type == "decl":
            tag, attrib = parse_tag(item.data)
            el = XMLElement("decl", tag=tag, attrib=attrib, parent=stack[-1])
            stack[-1].children.append(el)
        elif item_type == "comment":
            el = XMLElement("comment", text_content=item.data, parent=stack[-1])
            stack[-1].children.append(el)
        elif item_type == "text":
            if isopen:
                stack[-1].text_content = item.data.strip()
            else:
                prev.tail_content = item.data.strip()

    return root


def tostring(el: XMLElement, /, indent: str = "") -> str:
    def str_attrib(attrib: dict[str, str]) -> str:
        return "".join(
            " " + atr if val is None else f' {atr}="{escape(val)}"'
            for atr, val in attrib.items()
        )

    def _tostring(el, level=0, /):
        append_indent(level)
        if el.type == "element":
            ls_append("<")
            ls_append(el.tag)
            ls_append(str_attrib(el.attrib))
            if not el.text_content and not el.children:
                ls_append("/>")
            else:
                ls_append(">")
                if el.text_content:
                    ls_append(el.text_content)
                if el.children:
                    ls_append("\n")
                    for sel in el.children:
                        _tostring(sel, level+1)
                    append_indent(level)
                    ls_append("</%s>" % el.tag)
                else:
                    ls_append("</%s>" % el.tag)
        elif el.type == "pi":
            ls_append("<?")
            ls_append(el.tag)
            if "?" in el.attrib:
                ls_append(str_attrib(
                    {atr: val for atr, val in el.attrib.items() if atr != "?"}
                ))
                ls_append("?>")
            else:
                ls_append(str_attrib(el.attrib))
                ls_append(">")
        elif el.type == "decl":
            ls_append("<!")
            ls_append(el.tag)
            ls_append(str_attrib(el.attrib))
            ls_append(">")
        elif el.type == "comment":
            ls_append("<!--")
            ls_append(el.text_content)
            ls_append("-->")
        if el.tail_content:
            ls_append("\n")
            append_indent(level)
            ls_append(el.tail_content)
        ls_append("\n")
        return "".join(ls)

    ls: list[str] = []
    ls_append = ls.append
    if indent:
        append_indent = lambda level: ls_append(indent * level)
    else:
        append_indent = lambda level: None

    if el.type == "root":
        return "".join(tostring(sel, indent) for sel in el.children)
    else:
        return _tostring(el)

