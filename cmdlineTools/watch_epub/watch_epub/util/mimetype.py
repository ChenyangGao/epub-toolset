#!/usr/bin/env python
# coding: utf-8

# https://mimetype.io/all-types/
# https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types
# https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types/Common_types
# https://pypi.org/project/filetype/
# https://pypi.org/project/python-magic/

from json import loads
from pathlib import Path
from pkgutil import get_data

_dir = Path(__file__).parent

def _update_mimetypes_json():
    from json import dump
    from urllib.request import urlopen
    from xml.etree.ElementTree import fromstring

    content = urlopen("https://mimetype.io/all-types/").read()
    tree = fromstring(content)

    top = tree.find('.//div[@class="right"]')

    ls = []
    type_ = None
    for el in top:
        if el.attrib["class"] == "parent-line":
            type_ = el[0].text
        elif el.attrib["class"] == "mimetype":
            ls.append(dict(
                type=type_, 
                mimetype=el.find('./section/div/a').text, 
                extensions=[el2.text for el2 in el.findall('.//div[@class="extensions"]/span')], 
                alternatives=[el2.text for el2 in el.findall('.//div[@class="alternatives"]/div[@class="alts"]/a')], 
            ))
    dump(ls, open(_dir.parent / "src" / "mimetypes.json", "w"))

MIMETYPE_LIST = loads(pkgutil.get_data("src", "mimetypes.json"))



