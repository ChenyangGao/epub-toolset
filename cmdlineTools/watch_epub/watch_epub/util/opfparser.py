#!/usr/bin/env python3
# coding: utf-8

__version__ = (0, 1)

import sys
import os
import posixpath

from os import path as syspath
from re import search as re_search
from urllib.parse import unquote
from util.pathutils import reference_path, posixpath_to_syspath


SPECIAL_HANDLING_TAGS = dict([
    ('?xml', ('xmlheader', -1)),
    ('!--', ('comment', -3)),
    ('!DOCTYPE', ('doctype', -1))
])

SPECIAL_HANDLING_TYPES = ['xmlheader', 'doctype', 'comment']

_OPF_PARENT_TAGS = ['package', 'metadata', 'dc-metadata', 'x-metadata', 'manifest', 'spine', 'tours', 'guide', 'bindings']


def get_opf_bookpath(ebook_root: str = ""):
    path_to_container_xml = syspath.join(ebook_root, "META-INF", "container.xml")
    xml_data = open(path_to_container_xml, "rb").read()
    match = re_search(
        b'<rootfile\\s[^>]*?media-type="application/oebps-package\+xml"[^>]*', xml_data)
    if match is not None:
        submatch = re_search(b'\\sfull-path="([^"]+)', match[0])
        if submatch is not None:
            return unquote(submatch[1])
    raise ValueError("The opf file path is not defined")


class OpfParser:

    def __init__(self, ebook_root: str = ""):
        self.ebook_root = ebook_root
        self.opf_bookpath = opf_bookpath = get_opf_bookpath(ebook_root)
        self.opf_path = opf_path = self.get_path(opf_bookpath)
        self.opf_dir, self.opf_name = posixpath.split(opf_bookpath)
        if self.opf_dir:
            self.opf_dir += "/"
        self.opf = open(opf_path, "r", encoding="utf-8").read()

        self.opos = 0
        self.package = None
        # list of (tname, tattr, tcontent)
        self.metadata = []
        self.metadata_attr = None
        self.cover_id = None

        self.id_to_bookpath = {}
        self.id_to_href = {}
        self.id_to_mime = {}
        self.id_to_properties = {}
        self.id_to_fallback = {}
        self.id_to_overlay = {}

        # list of (idref, linear, properties)
        self.spine = []
        self.spine_ppd = None
        # list of (type, title, href)
        self.guide = []
        # list of (media-type, handler)
        self.bindings = []

        self._parseData()

    # OPF tag iterator
    def _opf_tag_iter(self):
        tcontent = last_tattr = None
        prefix = []
        while True:
            text, tag = self._parseopf()
            if text is None and tag is None:
                break
            if text is not None:
                tcontent = text.rstrip(" \t\v\f\r\n")
            else:  # we have a tag
                ttype, tname, tattr = self._parsetag(tag)
                if ttype == "begin":
                    tcontent = None
                    prefix.append(tname)
                    if tname in _OPF_PARENT_TAGS:
                        yield ".".join(prefix), tname, tattr, tcontent
                    else:
                        last_tattr = tattr
                else:  # single or end
                    if ttype == "end":
                        prefix.pop()
                        tattr = last_tattr
                        if tattr is None:
                            tattr = dict()
                        last_tattr = None
                    elif ttype == 'single':
                        tcontent = None
                    if ttype == 'single' or (ttype == 'end' and tname not in _OPF_PARENT_TAGS):
                        yield ".".join(prefix), tname, tattr, tcontent
                    tcontent = None

    # now parse the OPF to extract manifest, spine , and metadata
    def _parseData(self):
        cnt = 0
        for prefix, tname, tattr, tcontent in self._opf_tag_iter():
            # package
            if tname == "package":
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
                if tattr.get("name", "") == "cover":
                    self.cover_id = tattr.get("content", None)
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
            if tname == "spine":
                if tattr is not None:
                    self.spine_ppd = tattr.get("page-progression-direction", None)
                continue
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

    # parse and return either leading text or the next tag
    def _parseopf(self):
        p = self.opos
        if p >= len(self.opf):
            return None, None
        if self.opf[p] != '<':
            res = self.opf.find('<', p)
            if res == -1 :
                res = len(self.opf)
            self.opos = res
            return self.opf[p:res], None
        # handle comment as a special case
        if self.opf[p:p + 4] == '<!--':
            te = self.opf.find('-->', p + 1)
            if te != -1:
                te = te + 2
        else:
            te = self.opf.find('>', p + 1)
            ntb = self.opf.find('<', p + 1)
            if ntb != -1 and ntb < te:
                self.opos = ntb
                return self.opf[p:ntb], None
        self.opos = te + 1
        return None, self.opf[p:te + 1]

    # parses tag to identify:  [tname, ttype, tattr]
    #    tname: tag name
    #    ttype: tag type ('begin', 'end' or 'single')
    #    tattr: dictionary of tag atributes
    def _parsetag(self, s):
        n = len(s)
        p = 1
        tname = None
        ttype = None
        tattr = dict()
        while p < n and s[p:p + 1] == ' ' : p += 1
        if s[p:p + 1] == '/':
            ttype = 'end'
            p += 1
            while p < n and s[p:p + 1] == ' ' : p += 1
        b = p
        # handle comment special case as there may be no spaces to
        # delimit name begin or end
        if s[b:].startswith('!--'):
            p = b + 3
            tname = '!--'
            ttype, backstep = SPECIAL_HANDLING_TAGS[tname]
            tattr['special'] = s[p:backstep].strip()
            return tname, ttype, tattr
        while p < n and s[p:p + 1] not in ('>', '/', ' ', '"', "'", "\r", "\n") : p += 1
        tname = s[b:p].lower()
        # remove redundant opf: namespace prefixes on opf tags
        if tname.startswith("opf:"):
            tname = tname[4:]
        # more special cases
        if tname == '!doctype':
            tname = '!DOCTYPE'
        if tname in SPECIAL_HANDLING_TAGS:
            ttype, backstep = SPECIAL_HANDLING_TAGS[tname]
            tattr['special'] = s[p:backstep]
        if ttype is None:
            # parse any attributes of begin or single tags
            while s.find('=', p) != -1 :
                while p < n and s[p:p + 1] == ' ' : p += 1
                b = p
                while p < n and s[p:p + 1] != '=' : p += 1
                aname = s[b:p].lower()
                aname = aname.rstrip(' ')
                p += 1
                while p < n and s[p:p + 1] == ' ' : p += 1
                if s[p:p + 1] in ('"', "'") :
                    qt = s[p:p + 1]
                    p = p + 1
                    b = p
                    while p < n and s[p:p + 1] != qt: p += 1
                    val = s[b:p]
                    p += 1
                else :
                    b = p
                    while p < n and s[p:p + 1] not in ('>', '/', ' '): p += 1
                    val = s[b:p]
                tattr[aname] = val
        if ttype is None:
            ttype = 'begin'
            if s.find('/', p) >= 0:
                ttype = 'single'
        return ttype, tname, tattr

    def handle_quoted_attribute_values(self, value):
        if '"' in value:
            value = value.replace('"', "&quot;")
        return value

    def taginfo_toxml(self, taginfo):
        res = []
        tname, tattr, tcontent = taginfo
        res.append('<' + tname)
        if tattr is not None:
            for key in tattr:
                val = self.handle_quoted_attribute_values(tattr[key])
                res.append(' ' + key + '="' + val + '"')
        if tcontent is not None:
            res.append('>' + tcontent + '</' + tname + '>\n')
        else:
            res.append('/>\n')
        return "".join(res)

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

    def get_path(self, bookpath):
        return syspath.join(
            self.ebook_root, 
            posixpath_to_syspath(bookpath), 
        )

