#!/usr/bin/env python3
# coding: utf-8

__version__ = (0, 1)

import sys
import os

from util.hrefutils import urldecodepart, buildBookPath, startingDir, longestCommonPath
from util.hrefutils import mime_group_map
from collections import OrderedDict

SPECIAL_HANDLING_TAGS = OrderedDict([
    ('?xml', ('xmlheader', -1)),
    ('!--', ('comment', -3)),
    ('!DOCTYPE', ('doctype', -1))
])

SPECIAL_HANDLING_TYPES = ['xmlheader', 'doctype', 'comment']

_OPF_PARENT_TAGS = ['package', 'metadata', 'dc-metadata', 'x-metadata', 'manifest', 'spine', 'tours', 'guide', 'bindings']

def build_short_name(bookpath, lvl):
    pieces = bookpath.split("/")
    if lvl == 1: return pieces.pop()
    n = len(pieces)
    if lvl >= n: return "^" + bookpath
    pieces = pieces[n - lvl:n]
    return "/".join(pieces)

class Opf_Parser(object):

    def __init__(self, opf_path, opf_bookpath):
        opf_path = os.fsdecode(opf_path)
        self.opfname = os.path.basename(opf_bookpath)
        self.opf_bookpath = opf_bookpath
        self.opf_dir = startingDir(opf_bookpath)
        self.opf = open(opf_path, 'r', encoding="utf-8").read()
        self.opos = 0
        self.package = None
        self.metadata_attr = None
        self.metadata = []
        self.cover_id = None

        # let downstream invert any invertable dictionaries when needed
        self.manifest_id_to_href = OrderedDict()
        self.manifest_id_to_bookpath = OrderedDict()

        # create non-invertable dictionaries
        self.manifest_id_to_mime = OrderedDict()
        self.manifest_id_to_properties = OrderedDict()
        self.manifest_id_to_fallback = OrderedDict()
        self.manifest_id_to_overlay = OrderedDict()

        # spine and guide
        self.spine = []
        self.spine_ppd = None
        self.guide = []
        self.bindings = []

        # determine folder structure
        self.group_folder = OrderedDict()
        self.group_count = OrderedDict()
        self.group_folder["epub"] = ['META-INF']
        self.group_count["epub"] = [1]
        self.group_folder["opf"] = [self.opf_dir]
        self.group_count["opf"] = [1]

        # self.bookpaths = []
        # self.bookpaths.append(self.opf_bookpath)

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
                            tattr = OrderedDict()
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
                if mtype not in mime_group_map:
                    print("****Opf_Parser Warning****: Unknown MediaType: ", mtype)
                # url decode all relative hrefs since no fragment can be present
                # meaning no ambiguity in the meaning of any # chars in path
                if href.find(':') == -1:
                    href = urldecodepart(href)
                properties = tattr.pop("properties", None)
                fallback = tattr.pop("fallback", None)
                overlay = tattr.pop("media-overlay", None)

                # external resources are now allowed in the opf under epub3
                self.manifest_id_to_href[id] = href

                bookpath = ""
                if href.find(":") == -1:
                    bookpath = buildBookPath(href, self.opf_dir)
                self.manifest_id_to_bookpath[id] = bookpath
                self.manifest_id_to_mime[id] = mtype
                # self.bookpaths.append(bookpath)
                group = mime_group_map.get(mtype, '')
                if bookpath != "" and group != "":
                    folderlst = self.group_folder.get(group, [])
                    countlst = self.group_count.get(group, [])
                    sdir = startingDir(bookpath)
                    if sdir not in folderlst:
                        folderlst.append(sdir)
                        countlst.append(1)
                    else:
                        pos = folderlst.index(sdir)
                        countlst[pos] = countlst[pos] + 1
                    self.group_folder[group] = folderlst
                    self.group_count[group] = countlst
                self.manifest_id_to_properties[id] = properties
                self.manifest_id_to_fallback[id] = fallback
                self.manifest_id_to_overlay[id] = overlay
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

        # determine unique ShortPathName for each bookpath
        # start with filename and work back up the folders
        # spn = OrderedDict()
        # dupset = set()
        # nameset = {}
        # lvl = 1
        # for bkpath in self.bookpaths:
        #     aname = build_short_name(bkpath, lvl)
        #     spn[bkpath] = aname
        #     if aname in nameset:
        #         dupset.add(aname)
        #         nameset[aname].append(bkpath)
        #     else:
        #         nameset[aname]=[bkpath]
        #
        # now work just through any to-do list of duplicates
        # until all duplicates are gone
        #
        # todolst = list(dupset)
        # while(todolst):
        #     dupset = set()
        #     lvl += 1
        #     for aname in todolst:
        #         bklst = nameset[aname]
        #         del nameset[aname]
        #         for bkpath in bklst:
        #             newname = build_short_name(bkpath, lvl)
        #             spn[bkpath] = newname
        #             if newname in nameset:
        #                 dupset.add(newname)
        #                 nameset[newname].append(bkpath)
        #             else:
        #                 nameset[newname] = [bkpath]
        #     todolst = list(dupset)

        # finally sort by number of files in dir to find default folders for each group
        dirlst = []
        use_lower_case = False
        for group in self.group_folder.keys():
            folders = self.group_folder[group]
            cnts = self.group_count[group]
            folders = [x for _, x in sorted(zip(cnts, folders), reverse=True)]
            self.group_folder[group] = folders
            if group in ["Text", "Styles", "Images", "Audio", "Fonts", "Video", "Misc"]:
                afolder = folders[0]
                if afolder.find(group.lower()) > -1:
                    use_lower_case = True
                dirlst.append(folders[0])

        # now back fill any missing values
        # commonbase will end with a /
        commonbase = longestCommonPath(dirlst)
        if commonbase == "/":
            commonbase = ""
        for group in ["Styles", "Images", "Audio", "Fonts", "Video", "Misc"]:
            folders = self.group_folder.get(group, [])
            gname = group
            if use_lower_case:
                gname = gname.lower()
            if not folders:
                folders = [commonbase + gname]
                self.group_folder[group] = folders

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
    #    tname: tag name,    ttype: tag type ('begin', 'end' or 'single');
    #    tattr: dictionary of tag atributes
    def _parsetag(self, s):
        n = len(s)
        p = 1
        tname = None
        ttype = None
        tattr = OrderedDict()
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

    def get_epub_version(self):
        (ver, uid, tattr) = self.package
        return ver

    def get_package_tag(self):
        (ver, uid, tattr) = self.package
        packout = []
        packout.append('<package version="%s" unique-identifier="%s"' % (ver, uid))
        if tattr is not None:
            for key in tattr:
                val = self.handle_quoted_attribute_values(tattr[key])
                packout.append(' %s="%s"' % (key, val))
        packout.append(">\n")
        return "".join(packout)

    def get_metadataxml(self):
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

    def get_metadata_attr(self):
        return self.metadata_attr

    # list of (tname, tattr, tcontent)
    def get_metadata(self):
        return self.metadata

    def get_manifest_id_to_href_dict(self):
        return self.manifest_id_to_href

    def get_manifest_id_to_mime_dict(self):
        return self.manifest_id_to_mime

    def get_manifest_id_to_bookpath_dict(self):
        return self.manifest_id_to_bookpath

    def get_manifest_id_to_properties_dict(self):
        return self.manifest_id_to_properties

    def get_manifest_id_to_fallback_dict(self):
        return self.manifest_id_to_fallback

    def get_manifest_id_to_overlay_dict(self):
        return self.manifest_id_to_overlay

    def get_spine_ppd(self):
        return self.spine_ppd

    # list of (idref, linear, properties)
    def get_spine(self):
        return self.spine

    # list of (type, title, href)
    def get_guide(self):
        return self.guide

    # list of (media-type, handler)
    def get_bindings(self):
        return self.bindings

    def get_group_paths(self):
        return self.group_folder

