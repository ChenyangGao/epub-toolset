__all__ = ["ext_to_mime"]

# See: https://mimetype.io/all-types/

if __name__ == "__main__":
    def fetch_mime_list():
        ""
        from xml.etree.ElementTree import fromstring
        from urllib.request import urlopen

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
                    extensions=[el2.text for el2 in el.findall(
                        './/div[@class="extensions"]/span')], 
                    alternatives=[el2.text for el2 in el.findall(
                        './/div[@class="alternatives"]/div[@class="alts"]/a')], 
                ))

        return ls

    from json import dump
    from pathlib import Path

    _path_to_mimejson = Path(__file__).parents[2] / "src" / "003-mime-all-types.json"
    dump(fetch_mime_list(), _path_to_mimejson.open("w"))

ext_to_mime = {}

try:
    from json import loads
    from pkgutil import get_data
    mime_list = loads(get_data("src", "003-mime-all-types.json"))
except:
    mime_list = fetch_mime_list()
for r in mime_list:
    mimetype = r["mimetype"]
    extensions = r["extensions"]
    for ext in extensions:
        ext_to_mime[ext] = mimetype

import mimetypes

if not mimetypes.inited:
    mimetypes.init()
types_map = mimetypes.types_map
add_type = mimetypes._db.add_type
for ext, mime in ext_to_mime.items():
    if ext not in types_map:
        add_type(mime, ext, True)

