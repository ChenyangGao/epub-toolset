#!/usr/bin/env python3
# coding: utf-8

__version__ = (0, 1, 2)

import os
import posixpath
import sys

from html import unescape
from os import path as syspath
from re import search as re_search
from urllib.parse import quote, unquote

from util.pathutils import posixpath_to_syspath


SPECIAL_HANDLING_TAGS = dict([
    ('?xml', ('xmlheader', -1)),
    ('!--', ('comment', -3)),
    ('!DOCTYPE', ('doctype', -1))
])
SPECIAL_HANDLING_TYPES = ['xmlheader', 'doctype', 'comment']
_OPF_PARENT_TAGS = [
    'package', 'metadata', 'dc-metadata', 'x-metadata', 
    'manifest', 'spine', 'tours', 'guide', 'bindings', 
]


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






"startendtag", tag, attrs
"starttag", tag, attrs
"endtag", tag
"comment", data
"decl", decl
"pi", data
"text", data

opf = '<?xml version="1.0" encoding="UTF-8"?>\n<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n    <rootfiles>\n        <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>\n   </rootfiles>\n</container>\n'

def parse_xml_iter(opf):
    "Parse and yield either leading text or the next tag."
    # next tag begin
    ntb: int
    # tag begin
    te: int
    pos: int = 0
    pos_stop: int = len(opf)
    startswith = opf.startswith

    while pos < pos_stop:
        if startswith("<", pos):
            if starttagopen.match(rawdata, pos): # < + letter
                k = parse_starttag(pos)
            elif startswith("</", pos):
                k = parse_endtag(pos)
            elif startswith("<!--", pos):
                te = opf.find('-->', pos)
                if te == -1:
                    raise ValueError
                te += 3
                yield "comment", opf[pos+4:te+3]
            elif startswith("<?", pos):
                k = parse_pi(pos)
            elif startswith("<!", pos):
                k = parse_html_declaration(pos)
            elif (i + 1) < n:
                handle_data("<")
                k = i + 1

        else:
            ntb = opf.find("<", pos)
            if ntb == -1:
                ntb = pos_stop
            yield "text", opf[pos:ntb]
            pos = ntb




# 参考：html.parser.HTMLParser
"""A parser for HTML and XHTML."""

# This file is based on sgmllib.py, but the API is slightly different.

# XXX There should be a way to distinguish between PCDATA (parsed
# character data -- the normal case), RCDATA (replaceable character
# data -- only char and entity references and end tags are special)
# and CDATA (character data -- only end tags are special).


import re
import _markupbase

from html import unescape


__all__ = ['HTMLParser']

# Regular expressions used for parsing

interesting_normal = re.compile('[&<]')
incomplete = re.compile('&[a-zA-Z#]')

entityref = re.compile('&([a-zA-Z][-.a-zA-Z0-9]*)[^a-zA-Z0-9]')
charref = re.compile('&#(?:[0-9]+|[xX][0-9a-fA-F]+)[^0-9a-fA-F]')

starttagopen = re.compile('<[a-zA-Z]')
piclose = re.compile('>')
commentclose = re.compile(r'--\s*>')
# Note:
#  1) if you change tagfind/attrfind remember to update locatestarttagend too;
#  2) if you change tagfind/attrfind and/or locatestarttagend the parser will
#     explode, so don't do it.
# see http://www.w3.org/TR/html5/tokenization.html#tag-open-state
# and http://www.w3.org/TR/html5/tokenization.html#tag-name-state
tagfind_tolerant = re.compile(r'([a-zA-Z][^\t\n\r\f />\x00]*)(?:\s|/(?!>))*')
attrfind_tolerant = re.compile(
    r'((?<=[\'"\s/])[^\s/>][^\s/=>]*)(\s*=+\s*'
    r'(\'[^\']*\'|"[^"]*"|(?![\'"])[^>\s]*))?(?:\s|/(?!>))*')
locatestarttagend_tolerant = re.compile(r"""
  <[a-zA-Z][^\t\n\r\f />\x00]*       # tag name
  (?:[\s/]*                          # optional whitespace before attribute name
    (?:(?<=['"\s/])[^\s/>][^\s/=>]*  # attribute name
      (?:\s*=+\s*                    # value indicator
        (?:'[^']*'                   # LITA-enclosed value
          |"[^"]*"                   # LIT-enclosed value
          |(?!['"])[^>\s]*           # bare value
         )
        \s*                          # possibly followed by a space
       )?(?:\s|/(?!>))*
     )*
   )?
  \s*                                # trailing whitespace
""", re.VERBOSE)
endendtag = re.compile('>')
# the HTML 5 spec, section 8.1.2.2, doesn't allow spaces between
# </ and the tag name, so maybe this should be fixed
endtagfind = re.compile(r'</\s*([a-zA-Z][-.a-zA-Z0-9:_]*)\s*>')



class HTMLParser(_markupbase.ParserBase):
    """Find tags and other markup and call handler functions.

    Usage:
        p = HTMLParser()
        p.feed(data)
        ...
        p.close()

    Start tags are handled by calling self.handle_starttag() or
    self.handle_startendtag(); end tags by self.handle_endtag().  The
    data between tags is passed from the parser to the derived class
    by calling self.handle_data() with the data as argument (the data
    may be split up in arbitrary chunks).  If convert_charrefs is
    True the character references are converted automatically to the
    corresponding Unicode character (and self.handle_data() is no
    longer split in chunks), otherwise they are passed by calling
    self.handle_entityref() or self.handle_charref() with the string
    containing respectively the named or numeric reference as the
    argument.
    """

    CDATA_CONTENT_ELEMENTS = ("script", "style")

    def __init__(self, *, convert_charrefs=True):
        """Initialize and reset this instance.

        If convert_charrefs is True (the default), all character references
        are automatically converted to the corresponding Unicode characters.
        """
        self.convert_charrefs = convert_charrefs
        self.reset()

    def reset(self):
        """Reset this instance.  Loses all unprocessed data."""
        self.rawdata = ''
        self.lasttag = '???'
        self.interesting = interesting_normal
        self.cdata_elem = None
        _markupbase.ParserBase.reset(self)

    def feed(self, data):
        r"""Feed data to the parser.

        Call this as often as you want, with as little or as much text
        as you want (may include '\n').
        """
        self.rawdata = self.rawdata + data
        self.goahead(0)

    def close(self):
        """Handle any buffered data."""
        self.goahead(1)

    __starttag_text = None

    def get_starttag_text(self):
        """Return full source of start tag: '<...>'."""
        return self.__starttag_text

    def set_cdata_mode(self, elem):
        self.cdata_elem = elem.lower()
        self.interesting = re.compile(r'</\s*%s\s*>' % self.cdata_elem, re.I)

    def clear_cdata_mode(self):
        self.interesting = interesting_normal
        self.cdata_elem = None

    # Internal -- handle data as far as reasonable.  May leave state
    # and data to be processed by a subsequent call.  If 'end' is
    # true, force handling all data as if followed by EOF marker.
    def goahead(self, end):
        rawdata = self.rawdata
        i = 0
        n = len(rawdata)
        while i < n:
            if self.convert_charrefs and not self.cdata_elem:
                j = rawdata.find('<', i)
                if j < 0:
                    # if we can't find the next <, either we are at the end
                    # or there's more text incoming.  If the latter is True,
                    # we can't pass the text to handle_data in case we have
                    # a charref cut in half at end.  Try to determine if
                    # this is the case before proceeding by looking for an
                    # & near the end and see if it's followed by a space or ;.
                    amppos = rawdata.rfind('&', max(i, n-34))
                    if (amppos >= 0 and
                        not re.compile(r'[\s;]').search(rawdata, amppos)):
                        break  # wait till we get all the text
                    j = n
            else:
                match = self.interesting.search(rawdata, i)  # < or &
                if match:
                    j = match.start()
                else:
                    if self.cdata_elem:
                        break
                    j = n
            if i < j:
                if self.convert_charrefs and not self.cdata_elem:
                    self.handle_data(unescape(rawdata[i:j]))
                else:
                    self.handle_data(rawdata[i:j])
            i = self.updatepos(i, j)
            if i == n: break
            startswith = rawdata.startswith
            if startswith('<', i):
                if starttagopen.match(rawdata, i): # < + letter
                    k = self.parse_starttag(i)
                elif startswith("</", i):
                    k = self.parse_endtag(i)
                elif startswith("<!--", i):
                    k = self.parse_comment(i)
                elif startswith("<?", i):
                    k = self.parse_pi(i)
                elif startswith("<!", i):
                    k = self.parse_html_declaration(i)
                elif (i + 1) < n:
                    self.handle_data("<")
                    k = i + 1
                else:
                    break
                if k < 0:
                    if not end:
                        break
                    k = rawdata.find('>', i + 1)
                    if k < 0:
                        k = rawdata.find('<', i + 1)
                        if k < 0:
                            k = i + 1
                    else:
                        k += 1
                    if self.convert_charrefs and not self.cdata_elem:
                        self.handle_data(unescape(rawdata[i:k]))
                    else:
                        self.handle_data(rawdata[i:k])
                i = self.updatepos(i, k)
            elif startswith("&#", i):
                match = charref.match(rawdata, i)
                if match:
                    name = match.group()[2:-1]
                    self.handle_charref(name)
                    k = match.end()
                    if not startswith(';', k-1):
                        k = k - 1
                    i = self.updatepos(i, k)
                    continue
                else:
                    if ";" in rawdata[i:]:  # bail by consuming &#
                        self.handle_data(rawdata[i:i+2])
                        i = self.updatepos(i, i+2)
                    break
            elif startswith('&', i):
                match = entityref.match(rawdata, i)
                if match:
                    name = match.group(1)
                    self.handle_entityref(name)
                    k = match.end()
                    if not startswith(';', k-1):
                        k = k - 1
                    i = self.updatepos(i, k)
                    continue
                match = incomplete.match(rawdata, i)
                if match:
                    # match.group() will contain at least 2 chars
                    if end and match.group() == rawdata[i:]:
                        k = match.end()
                        if k <= i:
                            k = n
                        i = self.updatepos(i, i + 1)
                    # incomplete
                    break
                elif (i + 1) < n:
                    # not the end of the buffer, and can't be confused
                    # with some other construct
                    self.handle_data("&")
                    i = self.updatepos(i, i + 1)
                else:
                    break
            else:
                assert 0, "interesting.search() lied"
        # end while
        if end and i < n and not self.cdata_elem:
            if self.convert_charrefs and not self.cdata_elem:
                self.handle_data(unescape(rawdata[i:n]))
            else:
                self.handle_data(rawdata[i:n])
            i = self.updatepos(i, n)
        self.rawdata = rawdata[i:]

    # Internal -- parse html declarations, return length or -1 if not terminated
    # See w3.org/TR/html5/tokenization.html#markup-declaration-open-state
    # See also parse_declaration in _markupbase
    def parse_html_declaration(self, i):
        rawdata = self.rawdata
        assert rawdata[i:i+2] == '<!', ('unexpected call to '
                                        'parse_html_declaration()')
        if rawdata[i:i+4] == '<!--':
            # this case is actually already handled in goahead()
            return self.parse_comment(i)
        elif rawdata[i:i+3] == '<![':
            return self.parse_marked_section(i)
        elif rawdata[i:i+9].lower() == '<!doctype':
            # find the closing >
            gtpos = rawdata.find('>', i+9)
            if gtpos == -1:
                return -1
            self.handle_decl(rawdata[i+2:gtpos])
            return gtpos+1
        else:
            return self.parse_bogus_comment(i)

    # Internal -- parse bogus comment, return length or -1 if not terminated
    # see http://www.w3.org/TR/html5/tokenization.html#bogus-comment-state
    def parse_bogus_comment(self, i, report=1):
        rawdata = self.rawdata
        assert rawdata[i:i+2] in ('<!', '</'), ('unexpected call to '
                                                'parse_comment()')
        pos = rawdata.find('>', i+2)
        if pos == -1:
            return -1
        if report:
            self.handle_comment(rawdata[i+2:pos])
        return pos + 1

    # Internal -- parse processing instr, return end or -1 if not terminated
    def parse_pi(self, i):
        rawdata = self.rawdata
        assert rawdata[i:i+2] == '<?', 'unexpected call to parse_pi()'
        match = piclose.search(rawdata, i+2) # >
        if not match:
            return -1
        j = match.start()
        self.handle_pi(rawdata[i+2: j])
        j = match.end()
        return j

    # Internal -- handle starttag, return end or -1 if not terminated
    def parse_starttag(self, i):
        self.__starttag_text = None
        endpos = self.check_for_whole_start_tag(i)
        if endpos < 0:
            return endpos
        rawdata = self.rawdata
        self.__starttag_text = rawdata[i:endpos]

        # Now parse the data between i+1 and j into a tag and attrs
        attrs = []
        match = tagfind_tolerant.match(rawdata, i+1)
        assert match, 'unexpected call to parse_starttag()'
        k = match.end()
        self.lasttag = tag = match.group(1).lower()
        while k < endpos:
            m = attrfind_tolerant.match(rawdata, k)
            if not m:
                break
            attrname, rest, attrvalue = m.group(1, 2, 3)
            if not rest:
                attrvalue = None
            elif attrvalue[:1] == '\'' == attrvalue[-1:] or \
                 attrvalue[:1] == '"' == attrvalue[-1:]:
                attrvalue = attrvalue[1:-1]
            if attrvalue:
                attrvalue = unescape(attrvalue)
            attrs.append((attrname.lower(), attrvalue))
            k = m.end()

        end = rawdata[k:endpos].strip()
        if end not in (">", "/>"):
            lineno, offset = self.getpos()
            if "\n" in self.__starttag_text:
                lineno = lineno + self.__starttag_text.count("\n")
                offset = len(self.__starttag_text) \
                         - self.__starttag_text.rfind("\n")
            else:
                offset = offset + len(self.__starttag_text)
            self.handle_data(rawdata[i:endpos])
            return endpos
        if end.endswith('/>'):
            # XHTML-style empty tag: <span attr="value" />
            self.handle_startendtag(tag, attrs)
        else:
            self.handle_starttag(tag, attrs)
            if tag in self.CDATA_CONTENT_ELEMENTS:
                self.set_cdata_mode(tag)
        return endpos

    # Internal -- check to see if we have a complete starttag; return end
    # or -1 if incomplete.
    def check_for_whole_start_tag(self, i):
        rawdata = self.rawdata
        m = locatestarttagend_tolerant.match(rawdata, i)
        if m:
            j = m.end()
            next = rawdata[j:j+1]
            if next == ">":
                return j + 1
            if next == "/":
                if rawdata.startswith("/>", j):
                    return j + 2
                if rawdata.startswith("/", j):
                    # buffer boundary
                    return -1
                # else bogus input
                if j > i:
                    return j
                else:
                    return i + 1
            if next == "":
                # end of input
                return -1
            if next in ("abcdefghijklmnopqrstuvwxyz=/"
                        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
                # end of input in or before attribute value, or we have the
                # '/' from a '/>' ending
                return -1
            if j > i:
                return j
            else:
                return i + 1
        raise AssertionError("we should not get here!")

    # Internal -- parse endtag, return end or -1 if incomplete
    def parse_endtag(self, i):
        rawdata = self.rawdata
        assert rawdata[i:i+2] == "</", "unexpected call to parse_endtag"
        match = endendtag.search(rawdata, i+1) # >
        if not match:
            return -1
        gtpos = match.end()
        match = endtagfind.match(rawdata, i) # </ + tag + >
        if not match:
            if self.cdata_elem is not None:
                self.handle_data(rawdata[i:gtpos])
                return gtpos
            # find the name: w3.org/TR/html5/tokenization.html#tag-name-state
            namematch = tagfind_tolerant.match(rawdata, i+2)
            if not namematch:
                # w3.org/TR/html5/tokenization.html#end-tag-open-state
                if rawdata[i:i+3] == '</>':
                    return i+3
                else:
                    return self.parse_bogus_comment(i)
            tagname = namematch.group(1).lower()
            # consume and ignore other stuff between the name and the >
            # Note: this is not 100% correct, since we might have things like
            # </tag attr=">">, but looking for > after the name should cover
            # most of the cases and is much simpler
            gtpos = rawdata.find('>', namematch.end())
            self.handle_endtag(tagname)
            return gtpos+1

        elem = match.group(1).lower() # script or style
        if self.cdata_elem is not None:
            if elem != self.cdata_elem:
                self.handle_data(rawdata[i:gtpos])
                return gtpos

        self.handle_endtag(elem)
        self.clear_cdata_mode()
        return gtpos

















# bookpath, bookhref

class OpfParser:

    def __init__(self, ebook_root: str = ""):
        self.ebook_root = ebook_root
        self.opf_bookpath = opf_bookpath = get_opf_bookpath(ebook_root)
        self.opf_path = opf_path = self.get_path(opf_bookpath)
        self.opf_dir, self.opf_name = posixpath.split(opf_bookpath)
        self.opf_dir += "/"
        self.opf = open(opf_path, "r", encoding="utf-8").read()

        self.package = None
        self.metadata_attr = None
        self.metadata = []
        self.cover_id = None

        # 
        self.id_to_bookpath = {}
        self.id_to_href = {}
        self.id_to_mime = {}
        self.id_to_properties = {}
        self.id_to_fallback = {}
        self.id_to_overlay = {}
        self.bookpath_to_id = {}

        # spine and guide
        self.spine = []
        self.spine_ppd = None
        self.guide = []
        self.bindings = []
        self._parse_data()

    def _parse_data(self):
        "Parse the OPF file content, to extract manifest, spine, and metadata."
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
                    href = urldecodepart(href)
                properties = tattr.pop("properties", None)
                fallback = tattr.pop("fallback", None)
                overlay = tattr.pop("media-overlay", None)

                # external resources are now allowed in the opf under epub3
                self.id_to_href[id] = href

                bookpath = ""
                if href.find(":") == -1:
                    bookpath = buildBookPath(href, self.opf_dir)
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

    def _opf_tag_iter(self):
        "OPF tag iterator."
        tcontent = last_tattr = None
        prefix = []
        while True:
            text, tag = self._parse_opf()
            if text is None and tag is None:
                break
            if text is not None:
                tcontent = text.rstrip()
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
                            tattr = {}
                        last_tattr = None
                    elif ttype == 'single':
                        tcontent = None
                    if ttype == 'single' or (ttype == 'end' and tname not in _OPF_PARENT_TAGS):
                        yield ".".join(prefix), tname, tattr, tcontent
                    tcontent = None









    # generator
    @staticmethod
    def _parse_opf(opf):
        "Parse and yield either leading text or the next tag."
        <??>
        <(?P[^\s>]+ (/)>
        pos = 0
        pos_stop = len(opf)
        while pos < pos_stop:
            if opf[pos] != '<':
                res = opf.find('<', pos)
                if res == -1:
                    res = pos_stop
                yield opf[pos:res], None
                pos = res
                continue
            # handle comment as a special case
            if opf[pos:pos+4] == '<!--':
                te = opf.find('-->', pos+1)
                if te != -1:
                    te = te + 2
            else:
                te = opf.find('>', pos+1)
                ntb = opf.find('<', pos+1)
                if ntb != -1 and ntb < te:
                    yield opf[pos+1:ntb], None
                    pos = ntb
                    continue
            yield None, opf[pos+1:te+1]
            pos = te + 1

    def _parse_tag(self, s):
        """parses tag to identify:  [tname, ttype, tattr]
            tname: tag name
            ttype: tag type ('begin', 'end' or 'single')
            tattr: dictionary of tag atributes
        """
        n = len(s)
        p = 1
        tname = None
        ttype = None
        tattr = {}
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

    @property()
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
            posixpath_to_syspath(opf_bookpath), 
        )
