__all__ = ['iter_refer']

import posixpath

from itertools import chain
from typing import Generator, NamedTuple, Optional, Union
from urllib.parse import urldefrag

from lxml.etree import _Element # type: ignore

from .edit import read_html_iter
from .path import ElementPath, startswith_protocal, relative_path


class Relation(NamedTuple):
    href: Optional[ElementPath] = None
    id:  Optional[ElementPath] = None


class Refer(NamedTuple('Refer', start=Relation, end=Relation)):
    def __str__(self):
        try:
            return self._str
        except AttributeError:
            s = self._str = str_refer(self.start, self.end)
            return s


def get_reverse_refer(
    refer_href_el: _Element, 
    refer_bookhref: str, 
    refed_id_el: _Element, 
    refed_bookhref: str, 
) -> Union[tuple[None, None], tuple[_Element, _Element]]:
    refer_id = refer_href_el.attrib.get('id')
    for el in chain(
        (refed_id_el,), refed_id_el.iterdescendants(), 
        refed_id_el.itersiblings(), refed_id_el.iterancestors(), 
    ):
        if el.tag != 'a' or 'href' not in el.attrib:
            continue

        href = el.attrib['href']
        if startswith_protocal(href):
            continue

        link, hashtag = urldefrag(href)
        if not hashtag:
            continue

        path = relative_path(link, refed_bookhref, posixpath)
        if path != refer_bookhref:
            continue

        if refer_id == hashtag:
            return refer_href_el, el

        for refer_id_el in chain(
            refer_href_el.iterdescendants(), 
            refer_href_el.itersiblings(), 
            refer_href_el.iterancestors(), 
        ):
            if refer_id_el.attrib.get('id') == hashtag:
                return refer_id_el, el
    return None, None


def str_refer(start: Relation, end: Relation) -> str:
    a, b, c, d = start.href, start.id, end.href, end.id
    if b is None:
        return '''\
a.href → b.id
a := %s
b := %s''' % (a, d)
    if a == b:
        if c == d:
            return '''\
a.href → c.id
⇃        ↿
a.id   ← c.href
a := %s
c := %s''' % (a, d)
        return '''\
a.href → d.id
⇃        ↿
a.id   ← c.href
a := %s
c := %s
d := %s''' % (a, c, d)
    elif c == d:
        return '''\
a.href → c.id
⇃        ↿
b.id   ← c.href
a := %s
b := %s
c := %s''' % (a, b, c)
    return '''\
a.href → d.id
⇃        ↿
b.id   ← c.href
a := %s
b := %s
c := %s
d := %s''' % (a, b, c, d)


def iter_refer(bc) -> Generator[Refer, None, None]:
    map_href_tree = {href: tree for _, href, tree in read_html_iter(bc)}
    href_el_set = set()
    for book_href, tree in map_href_tree.items():
        for refer_href_el in tree.findall('.//*[@href]'):
            if refer_href_el.tag != 'a' or refer_href_el in href_el_set:
                continue

            href = refer_href_el.attrib['href']
            if startswith_protocal(href):
                continue

            link, hashtag = urldefrag(href)
            if hashtag == '':
                continue

            if link == '':
                refed_book_href = book_href
                refed_tree = tree
            else:
                refed_book_href = relative_path(link, book_href, posixpath)
                if refed_book_href == book_href:
                    refed_tree = tree
                else:
                    refed_tree = map_href_tree[refed_book_href]

            xpath = './/*[@id="%s"]' % hashtag
            refed_id_el = refed_tree.find(xpath)

            refer_id_el, refed_href_el = get_reverse_refer(
                refer_href_el, book_href, refed_id_el, refed_book_href)

            refer_href_elpath = ElementPath.of(refer_href_el, book_href)
            refed_id_elpath = ElementPath.of(refed_id_el, refed_book_href)
            if refer_id_el is None:
                refer_id_elpath = None
            elif refer_href_el is refer_id_el:
                refer_id_elpath = refer_href_elpath
            else:
                refer_id_elpath = ElementPath.of(refer_id_el, book_href)
            if refed_href_el is None:
                refed_href_elpath = None
            elif refed_href_el is refed_id_el:
                refed_href_elpath = refed_id_elpath
            else:
                refed_href_elpath = ElementPath.of(refed_href_el, refed_book_href)

            yield Refer(
                Relation(refer_href_elpath, refer_id_elpath), 
                Relation(refed_href_elpath, refed_id_elpath), 
            )

            href_el_set.add(refer_href_el)
            href_el_set.add(refed_href_el)


if __name__ == '__main__':
    import sys

    bc = sys._getframe(0).f_globals['bc']
    for i, l in enumerate(iter_refer(bc), 1):
        print('\nRelation', i)
        print(l)

