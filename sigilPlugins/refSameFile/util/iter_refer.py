__all__ = ['iter_refer']

import posixpath

from typing import Generator, NamedTuple
from urllib.parse import urldefrag

from .edit import read_html_iter
from .path import ElementPath, startswith_protocal, relative_path


class Refer(NamedTuple):
    href: ElementPath
    id: ElementPath

    def __str__(self):
        return '%s → %s' % self


def iter_refer(bc) -> Generator[Refer, None, None]:
    map_href_tree = {href: tree for _, href, tree in read_html_iter(bc)}
    for book_href, tree in map_href_tree.items():
        for ref_el in tree.findall('.//*[@href]'):
            if ref_el.tag != 'a':
                continue
            href = ref_el.attrib['href']
            if startswith_protocal(href):
                continue
            link, hashtag = urldefrag(href)
            if hashtag == '':
                continue

            xpath = './/*[@id="%s"]' % hashtag
            if link == '':
                refed_el = tree.find(xpath)
            else:
                href = relative_path(link, book_href, posixpath)
                refed_el = map_href_tree[href].find(xpath)

            if refed_el is not None:
                yield Refer(
                    ElementPath.of(ref_el, book_href), 
                    ElementPath.of(refed_el, href), 
                )


if __name__ == '__main__':
    import sys

    bc = sys._getframe(0).f_globals['bc']
    for i, l in enumerate(iter_refer(bc), 1):
        print('\nRelation', i)
        print(l)

