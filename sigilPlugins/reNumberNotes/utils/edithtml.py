from platform import system
from contextlib import contextmanager

from lxml.etree import _Element
from lxml.html import (
    fromstring as _html_fromstring, tostring as _html_tostring, 
    Element, HtmlElement, HTMLParser
)


__all__ = ['DoNotWriteBack', 'make_html_element', 'html_fromstring', 
           'html_tostring', 'ctx_edit_html']


_PLATFORM_IS_WINDOWS = system() == 'Windows'
_HTML_DOCTYPE = b'<!DOCTYPE html>'
_XHTML_DOCTYPE = (b'<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" '
                  b'"http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">')
_HTML_PARSER = HTMLParser(default_doctype=False)


class DoNotWriteBack(Exception):
    '''If changes do not require writing back to the file, 
    you can raise this exception'''


def _ensure_bytes(o):
    'Ensure the return value is `bytes` type'
    if isinstance(o, bytes):
        return o
    elif isinstance(o, str):
        return bytes(o, encoding='utf-8')
    else:
        return bytes(o)


def make_html_element(
    tag, 
    text='', 
    children=None,
    tail=None, 
):
    'Make a HtmlElement object'
    el = Element(tag)
    if text is not None:
        el.text = text
    if children is not None:
        el.extend(children)
    if tail is not None:
        el.tail = text
    return el


def html_fromstring(string, parser=_HTML_PARSER, **kwds):
    '''Convert a string to `lxml.etree._Element` object by using 
    `lxml.html.fromstring` function

    Tips: Please read the following documentation(s) for details
        - lxml.html.fromstring
        - lxml.etree.fromstring
        - lxml.html.HTMLParser

    :params parser: `parser` allows reading HTML into a normal XML tree, 
        this argument will be passed to `lxml.html.fromstring` function
    :params kwds: Keyword arguments will be passed to 
        `lxml.html.fromstring` function

    :return: A single element/document
    '''
    if not string.strip():
        return _html_fromstring(
            b'<html>\n    <head/>\n    <body/>\n</html>', 
            parser=parser, **kwds)
    tree = _html_fromstring(string, parser=parser, **kwds)
    # get root element
    for tree in tree.iterancestors(): 
        pass
    if tree.find('head') is None:
        tree.insert(0, make_html_element('head', tail='\n'))
    if tree.find('body') is None:
        tree.append(make_html_element('body', tail='\n'))
    return tree


def html_tostring(el, method='html', **kwds):
    '''Convert a root element node to string 
    by using `lxml.html.tostring` function

    Tips: Please read the following documentation(s) for details
        - lxml.html.tostring
        - lxml.etree.tostring

    :param method: Defines the output method.
        It defaults to 'html', but can also be 'xml' or 'xhtml' for xhtml output, 
        or 'text' to serialise to plain text without markup.
    :param kwds: Keyword arguments `kwds` will be passed to 
        `lxml.html.tostring` function

    :return: An HTML string representation of the document
    '''
    if method not in ('xml', 'html', 'xhtml'):
        return _html_tostring(el, method=method, **kwds)

    roottree = el.getroottree() if isinstance(el, _Element) else el
    root = roottree.getroot()
    docinfo = roottree.docinfo
    doctype = kwds.pop('doctype', docinfo.doctype)
    encoding = kwds.setdefault('encoding', docinfo.encoding or 'UTF-8')

    if not doctype:
        if method == 'html':
            doctype = _HTML_DOCTYPE
        elif method == 'xhtml':
            doctype = _XHTML_DOCTYPE

    if method == 'xhtml':
        method = 'xml'
    string = (
        # However, to be honest, if it is an HTML file, 
        # it does not need to have a <?xml ?> header
        b'<?xml version="%(xml_version)s" encoding="%(encoding)s"?>'
        b'\n%(doctype)s\n%(doc)s'
    ) % {
        b'xml_version': _ensure_bytes(docinfo.xml_version or b'1.0'),
        b'encoding': _ensure_bytes(encoding),
        b'doctype': _ensure_bytes(doctype),
        b'doc': _html_tostring(root, method=method, **kwds),
    }
    if _PLATFORM_IS_WINDOWS:
        string = string.replace(b'&#13;', b'')
    return string


@contextmanager
def ctx_edit_html(bc, manifest_id):
    '''Read and yield the etree object (parsed from a html file), 
    and then write back the above etree object.

    :param bc: `BookContainer` object. 
        An object of ePub book content provided by Sigil, 
        which can be used to access and operate the files in ePub
    :param manifest_id: Manifest id, be located in content.opf file, 
        The XPath as following (the `namespace` depends on the specific situation):
        /namespace:package/namespace:manifest/namespace:item/@id

    Example::
        def operations_on_etree(etree):
            ...

        with ctx_edit_html(bc, manifest_id) as etree:
            operations_on_etree(etree)
    '''
    tree = html_fromstring(bc.readfile(manifest_id).encode('utf-8'))
    try:
        if (yield tree) is not None:
            raise DoNotWriteBack
    except DoNotWriteBack:
        pass
    else:
        method = 'xhtml' if 'xhtml' in bc.id_to_mime(manifest_id) else 'html'
        bc.writefile(
            manifest_id, 
            html_tostring(tree, method=method).decode('utf-8')
        )

