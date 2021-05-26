'''
This module provides some functions for modifying files in the 
[Sigil Ebook Editor](https://sigil-ebook.com/) plug-ins.
'''

__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 10)
__all__ = [
    'WriteBack', 'DoNotWriteBack', 'make_element','make_html_element', 
    'xml_fromstring', 'xml_tostring', 'html_fromstring', 'html_tostring', 
    'edit', 'ctx_edit', 'ctx_edit_sgml', 'ctx_edit_html', 'edit_iter', 
    'edit_batch', 'edit_html_iter', 'edit_html_batch', 'IterElementInfo', 
    'EnumSelectorType', 'element_iter', 'EditStack', 'TextEtreeEditStack', 
]

import sys

from contextlib import contextmanager, ExitStack
from enum import Enum
from functools import partial
from inspect import getfullargspec, CO_VARARGS
from platform import system
from typing import (
    cast, Any, Callable, ContextManager, Dict, Generator, 
    Iterable, Iterator, List, Mapping, NamedTuple, Optional, 
    Tuple, TypeVar, Union, 
)
from types import MappingProxyType

from cssselect.xpath import GenericTranslator # type: ignore
from lxml.cssselect import CSSSelector # type: ignore
from lxml.etree import ( # type: ignore
    fromstring as xml_fromstring, tostring as _xml_tostring, 
    _Element, _ElementTree, Element, XPath, 
) 
from lxml.html import ( # type: ignore
    fromstring as _html_fromstring, tostring as _html_tostring, 
    Element as HTMLElement, HtmlElement, HTMLParser, 
)

from bookcontainer import BookContainer # type: ignore


T = TypeVar('T')

_PLATFORM_IS_WINDOWS = system() == 'Windows'
_HTML_DOCTYPE = b'<!DOCTYPE html>'
_XHTML_DOCTYPE = (b'<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" '
                  b'"http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">')
_HTML_PARSER = HTMLParser(default_doctype=False)


class WriteBack(Exception):
    '''If changes require writing back to the file, 
    you can raise this exception'''

    def __init__(self, data):
        self.data = data


class DoNotWriteBack(Exception):
    '''If changes do not require writing back to the file, 
    you can raise this exception'''


def _ensure_bytes(o: Any) -> bytes:
    'Ensure the return value is `bytes` type'
    if isinstance(o, bytes):
        return o
    elif isinstance(o, str):
        return bytes(o, encoding='utf-8')
    else:
        return bytes(o)


class _Result(NamedTuple):
    argcount: int
    has_varargs: bool


def _posargcount(func: Callable) -> Tuple[int, bool]:
    code = getattr(func, '__code__', None)
    if code:
        return _Result(code.co_argcount, bool(code.co_flags & CO_VARARGS))
    try:
        argspec = getfullargspec(func)
    except:
        return _Result(0, False)
    else:
        return _Result(len(argspec.args), argspec.varargs is not None)


def _make_standard_predicate(
    predicate: Optional[Callable[..., bool]] = None,
) -> Callable[[str, str, str], bool]:
    if predicate is None:
        def pred(manifest_id: str, href: str, mimetype: str) -> bool:
            return True
    else:
        argcount, has_varargs = _posargcount(predicate)
        if has_varargs or argcount >= 3:
            def pred(manifest_id: str, href: str, mimetype: str) -> bool:
                return (cast(Callable[..., bool], predicate))(manifest_id, href, mimetype)
        elif argcount == 2:
            def pred(manifest_id: str, href: str, mimetype: str) -> bool:
                return (cast(Callable[..., bool], predicate))(manifest_id, href)
        elif argcount == 1:
            def pred(manifest_id: str, href: str, mimetype: str) -> bool:
                return (cast(Callable[..., bool], predicate))(manifest_id)
        else:
            def pred(manifest_id: str, href: str, mimetype: str) -> bool:
                return (cast(Callable[..., bool], predicate))()

    pred.__name__ = 'predicate'
    return pred


def make_element(
    tag: str, 
    text: Optional[str] = None, 
    attrib: Optional[Mapping] = None,
    nsmap: Optional[Mapping] = None,
    children: Optional[List[_Element]] = None,
    tail: Optional[str] = None, 
    **_extra,
) -> _Element:
    '''Make a lxml.etree._Element object

    Tips: Please read the following documentation(s) for details
        - lxml.etree.Element
        - lxml.html._Element
    '''
    el = Element(tag, attrib=attrib, nsmap=nsmap, **_extra)
    if text is not None:
        el.text = text
    if children is not None:
        el.extend(children)
    if tail is not None:
        el.tail = tail
    return el


def make_html_element(
    tag: str, 
    text: Optional[str] = '', 
    attrib: Optional[Mapping] = None,
    nsmap: Optional[Mapping] = None,
    children: Optional[List[HtmlElement]] = None,
    tail: Optional[str] = None, 
    **_extra,
) -> HtmlElement:
    '''Make a lxml.html.HtmlElement object

    Tips: Please read the following documentation(s) for details
        - lxml.etree.Element
        - lxml.html.HtmlElement
    '''
    el = HTMLElement(tag, attrib=attrib, nsmap=nsmap, **_extra)
    if text is not None:
        el.text = text
    if children is not None:
        el.extend(children)
    if tail is not None:
        el.tail = tail
    return el


def xml_tostring(
    el: Union[_Element, _ElementTree], 
    method: str = 'xml', 
    **kwds,
) -> bytes:
    '''Convert a root element node to string by using 
    `lxml.etree.tostring` function

    Tips: Please read the following documentation(s) for details
        - lxml.etree.tostring

    :param method: The argument 'method' selects the output method: 'xml',
        'html', plain 'text' (text content without tags), 'c14n' or 'c14n2'.
        Default is 'xml'.
        With ``method="c14n"`` (C14N version 1), the options ``exclusive``,
        ``with_comments`` and ``inclusive_ns_prefixes`` request exclusive
        C14N, include comments, and list the inclusive prefixes respectively.
        With ``method="c14n2"`` (C14N version 2), the ``with_comments`` and
        ``strip_text`` options control the output of comments and text space
        according to C14N 2.0.
    :param kwds: Keyword arguments `kwds` will be passed to 
        `lxml.etree.tostring` function

    :return: An XML string representation of the document
    '''
    if method not in ('xml', 'html'):
        return _xml_tostring(el, method=method, **kwds)

    roottree: _ElementTree = el.getroottree() if isinstance(el, _Element) else el
    docinfo = roottree.docinfo
    encoding = kwds.setdefault('encoding', docinfo.encoding or 'UTF-8')

    string = _xml_tostring(roottree, method=method, **kwds)
    if method == 'xml':
        string = b'<?xml version="%s" encoding="%s"?>\n'% (
            _ensure_bytes(docinfo.xml_version or b'1.0'),
            _ensure_bytes(encoding),
        ) + string

    if _PLATFORM_IS_WINDOWS:
        string = string.replace(b'&#13;', b'')
    return string


def html_fromstring(
    string: Union[str, bytes], 
    parser = _HTML_PARSER,
    **kwds
) -> _Element:
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


def html_tostring(
    el: Union[_Element, _ElementTree], 
    method: str = 'html', 
    **kwds,
) -> bytes:
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

    roottree: _ElementTree = el.getroottree() if isinstance(el, _Element) else el
    root: _Element = roottree.getroot()
    docinfo  = roottree.docinfo
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


def edit(
    manifest_id: str, 
    operate: Callable[..., Union[bytes, str]], 
    bc: Optional[BookContainer] = None, 
) -> bool:
    '''Read the file data, operate on, and then write the changed data back

    :param manifest_id: Manifest id, be located in content.opf file, 
        The XPath as following (the `namespace` depends on the specific situation):
        /namespace:package/namespace:manifest/namespace:item/@id
    :param operate: Take data in, operate on, and then return the changed data
    :param bc: `BookContainer` object. 
        An object of ePub book content provided by Sigil, 
        which can be used to access and operate the files in ePub.

    :return: Is it successful?
    '''
    if bc is None:
        bc = cast(BookContainer, sys._getframe(1).f_globals['bc'])

    content = bc.readfile(manifest_id)

    try:
        content_new = operate(content)
    except DoNotWriteBack:
        return False
    except WriteBack as exc:
        content_new = exc.data

    if content != content_new:
        bc.writefile(manifest_id, content_new)
        return True
    return False


@contextmanager
def ctx_edit(
    manifest_id: str, 
    bc: Optional[BookContainer] = None, 
    wrap_me: bool = False, 
    extra_data: Optional[Mapping] = None, 
) -> Generator[Union[None, dict, bytes, str], Any, bool]:
    '''Read and yield the file data, and then take in and write back the changed data.

    :param manifest_id: Manifest id, be located in content.opf file, 
        The XPath as following (the `namespace` depends on the specific situation):
        /namespace:package/namespace:manifest/namespace:item/@id
    :param bc: `BookContainer` object. 
        An object of ePub book content provided by Sigil, 
        which can be used to access and operate the files in ePub.
    :param wrap_me: Whether to wrap up object, if True, return a dict containing keys 
                    ('manifest_id', 'data', 'write_back')
    :param extra_data: If `wrap_me` is true and `extra_data` is not None, then update
                       `extra_data` to the dictionary of return.

    :return: A context manager that returns the `data`
        if wrap_me:
            data = {'manifest_id': manifest_id, 'data': bc.readfile(manifest_id)}
        else:
            data = bc.readfile(manifest_id)

    Example::
        def operations_on_content(data_old):
            ...
            return data_new

        with ctx_edit(manifest_id, bc) as content:
            content_new = operations_on_content(content)
            if content != content_new:
                raise WriteBack(content_new)

        # OR equivalent to
        with ctx_edit(manifest_id, bc, wrap_me=True) as data:
            content = data['data']
            content_new = operations_on_content(content)
            if content == content_new:
                del data['data']
                # OR raise DoNotWriteBack
            else:
                data['data'] = content_new
    '''
    if bc is None:
        bc = cast(BookContainer, sys._getframe(1).f_globals['bc'])

    content = bc.readfile(manifest_id)

    try:
        if wrap_me:
            data = {
                'manifest_id': manifest_id, 
                'data': content,
                'write_back': True,
            }
            if extra_data:
                data.update(extra_data)
            while (yield data) is not None:
                pass
            if data.get('data') is None or not data.get('write_back'):
                raise DoNotWriteBack
            content_new = data['data']
        else:
            content_new = yield content
            if content_new is None:
                raise DoNotWriteBack
            while (yield None) is not None:
                pass
    except DoNotWriteBack:
        return False
    except WriteBack as exc:
        content_new = exc.data

    if content != content_new:
        bc.writefile(manifest_id, content_new)
        return True
    return False


@contextmanager
def ctx_edit_sgml(
    manifest_id: str,
    bc: Optional[BookContainer] = None, 
    fromstring: Callable = xml_fromstring,
    tostring: Callable[..., Union[bytes, bytearray, str]] = xml_tostring,
) -> Generator[Any, Any, bool]:
    '''Read and yield the etree object (parsed from a xml file), 
    and then write back the above etree object.

    :param manifest_id: Manifest id, be located in content.opf file, 
        The XPath as following (the `namespace` depends on the specific situation):
        /namespace:package/namespace:manifest/namespace:item/@id
    :param bc: `BookContainer` object. 
        An object of ePub book content provided by Sigil, 
        which can be used to access and operate the files in ePub.
    :param fromstring: Parses an XML or SGML document or fragment from a string.
                       Returns the root node (or the result returned by a parser target).
    :param fromstring: Serialize an element to an encoded string representation of its XML
                       or SGML tree.

    Example::
        def operations_on_etree(etree):
            ...

        with ctx_edit_sgml(manifest_id, bc) as etree:
            operations_on_etree(etree)
    '''
    if bc is None:
        bc = cast(BookContainer, sys._getframe(1).f_globals['bc'])

    content = bc.readfile(manifest_id)
    tree = fromstring(content.encode('utf-8'))

    try:
        if (yield tree) is not None:
            raise DoNotWriteBack
    except DoNotWriteBack:
        return False
    except WriteBack as exc:
        content_new = exc.data
        if not isinstance(content_new, (bytes, bytearray, str)):
            content_new = tostring(content_new)
    else:
        content_new = tostring(tree)

    if isinstance(content_new, (bytes, bytearray)):
        content_new = content_new.decode('utf-8')

    if content != content_new:
        bc.writefile(manifest_id, content_new)
        return True
    return False


@contextmanager
def ctx_edit_html(
    manifest_id: str, 
    bc: Optional[BookContainer] = None, 
) -> Generator[Any, Any, bool]:
    '''Read and yield the etree object (parsed from a html file), 
    and then write back the above etree object.

    :param manifest_id: Manifest id, be located in content.opf file, 
        The XPath as following (the `namespace` depends on the specific situation):
        /namespace:package/namespace:manifest/namespace:item/@id
    :param bc: `BookContainer` object. 
        An object of ePub book content provided by Sigil, 
        which can be used to access and operate the files in ePub.

    Example::
        def operations_on_etree(etree):
            ...

        with ctx_edit_html(manifest_id, bc) as etree:
            operations_on_etree(etree)
    '''
    if bc is None:
        bc = cast(BookContainer, sys._getframe(1).f_globals['bc'])

    return (yield from ctx_edit_sgml.__wrapped__( # type: ignore
        bc, 
        manifest_id, 
        html_fromstring, 
        partial(
            html_tostring, 
            method='xhtml' if 'xhtml' in bc.id_to_mime(manifest_id) else 'html',
        ),
    ))


def edit_iter(
    manifest_id_s: Optional[Iterable[str]] = None, 
    bc: Optional[BookContainer] = None, 
    predicate: Optional[Callable[..., bool]] = None, 
    wrap_me: bool = False, 
    yield_cm: bool = False, 
) -> Generator:
    '''Used to process a collection of specified files in ePub file one by one

    :param manifest_id_s: Manifest id collection, be located in content.opf file,
        The XPath as following (the `namespace` depends on the specific situation):
        /namespace:package/namespace:manifest/namespace:item/@id
    :param bc: `BookContainer` object. 
        An object of ePub book content provided by Sigil, 
        which can be used to access and operate the files in ePub.
    :param predicate: If it is a callable, it will receive parameters in order (if possible)
                      (`manifest_id`, `OPF_href`, `mimetype`), and then determine whether to 
                      continue processing.
    :param wrap_me: Will pass to function ctx_edit as keyword argument.
    :param yield_cm: Determines whether each iteration returns the context manager.

    Example::
        def operations_on_content(data_old):
            ...
            return data_new

        edit_worker = edit_iter(('id1', 'id2'), bc)
        for content in edit_worker:
            content_new = operations_on_content(content)
            if content != content_new:
                edit_worker.send(content_new)

        # OR equivalent to
        for cm in edit_iter(('id1', 'id2'), bc, yield_cm=True):
            with cm as content:
                content_new = operations_on_content()
                if content != content_new:
                    raise WriteBack(content_new)

        # OR equivalent to
        for data in edit_iter(('id1', 'id2'), bc, wrap_me=True):
            content = data['data']
            content_new = operations_on_content(content)
            if content == content_new:
                del data['data']
            else:
                data['data'] = content_new
    '''
    predicate = _make_standard_predicate(predicate)

    if bc is None:
        bc = cast(BookContainer, sys._getframe(1).f_globals['bc'])

    if manifest_id_s is None:
        it = bc.manifest_iter()
    else:
        it = ((fid, bc.id_to_href(fid), bc.id_to_mime(fid)) 
              for fid in manifest_id_s)

    for fid, href, mime in it:
        if not predicate(fid, href, mime):
            continue
        extra_data = {'href': href, 'mimetype': mime}
        if yield_cm:
            yield ctx_edit(bc, fid, wrap_me=wrap_me, extra_data=extra_data)
        else:
            yield from ctx_edit.__wrapped__( # type: ignore
                bc, fid, wrap_me=wrap_me, extra_data=extra_data)


def edit_batch(
    operate: Callable, 
    manifest_id_s: Optional[Iterable[str]] = None, 
    bc: Optional[BookContainer] = None, 
    predicate: Optional[Callable[..., bool]] = None, 
) -> Dict[str, bool]:
    '''Used to process a collection of specified files in ePub file one by one

    :param manifest_id_s: Manifest id collection, be located in content.opf file,
        The XPath as following (the `namespace` depends on the specific situation):
        /namespace:package/namespace:manifest/namespace:item/@id
    :param operate: Take data in, operate on, and then return the changed data.
    :param bc: `BookContainer` object. 
        An object of ePub book content provided by Sigil, 
        which can be used to access and operate the files in ePub.
    :param predicate: If it is a callable, it will receive parameters in order (if possible)
                      (`manifest_id`, `OPF_href`, `mimetype`), and then determine whether to 
                      continue processing.

    :return: Dictionary, keys are the manifest id of all processed files, values are whether 
             an exception occurs when processing the corresponding file 
             (whatever the file was modified or not).

    Example::
        def operations_on_content(data_old):
            ...
            return data_new

        edit_batch(operations_on_content, ('id1', 'id2'), bc)
    '''
    predicate = _make_standard_predicate(predicate)

    if bc is None:
        bc = cast(BookContainer, sys._getframe(1).f_globals['bc'])

    if manifest_id_s is None:
        it = bc.manifest_iter()
    else:
        it = ((fid, bc.id_to_href(fid), bc.id_to_mime(fid)) 
              for fid in manifest_id_s)

    success_status: Dict[str, bool] = {}
    for fid, href, mime in it:
        if not predicate(fid, href, mime):
            continue
        try:
            data: dict
            with ctx_edit(bc, fid, wrap_me=True) as data: # type: ignore
                data['data'] = operate(data['data'])
            success_status[fid] = True
        except:
            success_status[fid] = False
    return success_status


def edit_html_iter(
    bc: Optional[BookContainer] = None, 
    predicate: Optional[Callable[..., bool]] = None, 
    wrap_me: bool = False, 
    yield_cm: bool = False, 
) -> Generator[Union[None, _Element, dict], Any, None]:
    '''Used to process a collection of specified html files in ePub file one by one

    :param bc: `BookContainer` object. 
        An object of ePub book content provided by Sigil, 
        which can be used to access and operate the files in ePub.
    :param predicate: If it is a callable, it will receive parameters in order (if possible)
                      (`manifest_id`, `OPF_href`, `mimetype`), and then determine whether to 
                      continue processing.
    :param wrap_me: Whether to wrap up object, if True, return a dict containing keys 
                    ('manifest_id', 'OPF_href', 'mimetype', 'etree', 'write_back')
    :param yield_cm: Determines whether each iteration returns the context manager.

    Example::
        def operations_on_etree(etree):
            ...

        edit_worker = edit_html_iter(bc)
        for etree in edit_worker:
            operations_on_etree(etree)
            ## if no need to write back
            # edit_worker.throw(DoNotWriteBack)
            ## OR
            # edit_worker.send(0)

        # OR equivalent to
        for cm in edit_html_iter(bc, yield_cm=True):
            with cm as etree:
                operations_on_etree(etree)
                ## if no need to write back
                # raise DoNotWriteBack

        # OR equivalent to
        for data in edit_html_iter(bc, wrap_me=True):
            operations_on_etree(data['etree'])
            ## if no need to write back
            # data['write_back'] = False
            ## OR
            # del data['write_back']
    '''
    predicate = _make_standard_predicate(predicate)

    if bc is None:
        bc = cast(BookContainer, sys._getframe(1).f_globals['bc'])

    for fid, href in bc.text_iter():
        mime = bc.id_to_mime(fid)
        if not predicate(fid, href, mime):
            continue
        if yield_cm:
            yield ctx_edit_html(bc, fid)
        else:
            with ctx_edit_html(bc, fid) as tree:
                if wrap_me:
                    data = {
                        'manifest_id': fid, 
                        'href': href, 
                        'mimetype': mime, 
                        'etree': tree,
                        'write_back': True,
                    }
                    while (yield data) is not None:
                        pass
                    if not data.get('write_back', False):
                        raise DoNotWriteBack
                else:
                    while (yield tree) is not None:
                        pass


def edit_html_batch(
    operate: Callable[[_Element], Any], 
    bc: Optional[BookContainer] = None, 
    predicate: Optional[Callable[..., bool]] = None, 
) -> Dict[str, bool]:
    '''Used to process a collection of specified html files in ePub file one by one

    :param operate: Take etree object in, operate on.
    :param bc: `BookContainer` object. 
        An object of ePub book content provided by Sigil, 
        which can be used to access and operate the files in ePub.
    :param predicate: If it is a callable, it will receive parameters in order (if possible)
                      (`manifest_id`, `OPF_href`, `mimetype`), and then determine whether to 
                      continue processing.

    :return: Dictionary, keys are the manifest id of all processed files, values are whether 
             an exception occurs when processing the corresponding file 
             (whatever the file was modified or not).

    Example::
        def operations_on_etree(etree):
            ...

        edit_html_batch(operations_on_etree, bc)
    '''
    predicate = _make_standard_predicate(predicate)

    if bc is None:
        bc = cast(BookContainer, sys._getframe(1).f_globals['bc'])

    success_status: Dict[str, bool] = {}
    for fid, href in bc.text_iter():
        mime = bc.id_to_mime(fid)
        if not predicate(fid, href, mime):
            continue
        try:
            with ctx_edit_html(bc, fid) as tree:
                operate(tree)
            success_status[fid] = True
        except:
            success_status[fid] = False   
    return success_status


class IterElementInfo(NamedTuple):
    '''The wrapper for the output tuple, contains the following fields

    global_no:   the sequence number of epub (global) output
    local_no:    the sequence number of each (x)html (local) output
    element:     (x)html element object
    etree:       (x)html tree object
    manifest_id: manifest id
    href:        OPF href
    mimetype:    media type
    '''
    global_no: int
    local_no: int
    element: _Element
    etree: _Element
    manifest_id: str
    href: str
    mimetype: str


class EnumSelectorType(Enum):
    '''Selector type enumeration.

    .xpath:  Indicates that the selector type is XPath.
    .cssselect: Indicates that the selector type is CSS Selector.
    '''

    xpath  = 1
    XPath  = 1
    cssselect = 2
    CSS_Selector = 2

    @classmethod
    def of(enum_cls, value):
        val_cls = type(value)
        if val_cls is enum_cls:
            return value
        elif issubclass(val_cls, int):
            return enum_cls(value)
        elif issubclass(val_cls, str):
            try:
                return enum_cls[value]
            except KeyError as exc:
                raise ValueError(value) from exc
        raise TypeError(f"expected value's type in ({enum_cls!r}"
                        f", int, str), got {val_cls}")


def element_iter(
    path: Union[str, XPath], 
    bc: Optional[BookContainer] = None, 
    seltype: Union[int, str, EnumSelectorType] = EnumSelectorType.cssselect, 
    namespaces: Optional[Mapping] = None, 
    translator: Union[str, GenericTranslator] = 'xml',
    predicate: Optional[Callable[..., bool]] = None,
    wrap_yield: bool = True,
) -> Union[Generator[IterElementInfo, None, None], Generator[_Element, None, None]]:
    '''Traverse all (X)HTML files in epub, search the elements that match the path, 
    and return the relevant information of these elements one by one.

    :param path: A XPath expression or CSS Selector expression.
                 If its `type` is `str`, then it is a XPath expression or 
                 CSS Selector expression determined by `seltype`.
                 If its type is a subclass of 'lxml.etree.XPath'`, then 
                 parameters `seltype`, `namespaces`, `translator` are ignored.
    :param bc: `BookContainer` object. 
        An object of ePub book content provided by Sigil, 
        which can be used to access and operate the files in ePub.
    :param seltype: Selector type. It can be any value that can be 
                    accepted by `EnumSelectorType.of`, the return value called final value.
                    If its final value is `EnumSelectorType.xpath`, then parameter
                    `translator` is ignored.
    :param predicate: If it is a callable, it will receive parameters in order (if possible)
                      (`manifest_id`, `OPF_href`, `mimetype`), and then determine whether to 
                      continue processing.
    :param namespaces: Prefix-namespace mappings used by `path`.

        To use CSS namespaces, you need to pass a prefix-to-namespace
        mapping as ``namespaces`` keyword argument::

            >>> from lxml import cssselect, etree
            >>> rdfns = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
            >>> select_ns = cssselect.CSSSelector('root > rdf|Description',
            ...                                   namespaces={'rdf': rdfns})

            >>> rdf = etree.XML((
            ...     '<root xmlns:rdf="%s">'
            ...       '<rdf:Description>blah</rdf:Description>'
            ...     '</root>') % rdfns)
            >>> [(el.tag, el.text) for el in select_ns(rdf)]
            [('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}Description', 'blah')]

    :param translator: A CSS Selector expression to XPath expression translator object.
    :param wrap_yield: Determine whether to wrap the yield results

    :return: Generator, if wrap_yield yield `IterElementInfo` object, 
             else yield `Element` object.

    Example::
        def operations_on_element(element):
            ...

        for info in element_iter(css_selector, bc):
            operations_on_element(info.element)

        # OR equivalent to
        for element in element_iter(css_selector, bc, wrap_yield=False):
            operations_on_element(element)
    '''
    select: XPath
    if isinstance(path, str):
        if EnumSelectorType.of(seltype) is EnumSelectorType.cssselect:
            select = CSSSelector(
                path, namespaces=namespaces, translator=translator)
        else:
            select = XPath(path, namespaces=namespaces)
    else:
        select = path

    if bc is None:
        bc = cast(BookContainer, sys._getframe(1).f_globals['bc'])

    i: int = 0
    data: dict
    for data in edit_html_iter(bc, predicate=predicate, wrap_me=True): # type: ignore
        tree = data['etree']
        els = select(tree)
        if not els:
            del data['write_back']
            continue
        if wrap_yield:
            for i, (j, el) in enumerate(enumerate(els, 1), i + 1):
                yield IterElementInfo(
                    i, j, el, tree, data['manifest_id'], data['href'], data['mimetype'])
        else:
            yield from els


class EditStack(Mapping[str, T]):

    __context_factory__: Callable[[BookContainer, str], ContextManager] = \
        lambda bc, fid: ctx_edit(bc, fid, wrap_me=True)

    def __init__(self, bc: Optional[BookContainer] = None) -> None:
        if bc is None:
            bc = cast(BookContainer, sys._getframe(1).f_globals['bc'])
        self._edit_stack: ExitStack = ExitStack()
        self._data: Dict[str, T] = {}
        self._bc: BookContainer = bc

    @property
    def data(self) -> MappingProxyType:
        return MappingProxyType(self._data)

    def __len__(self) -> int:
        return len(self._bc._w.id_to_mime)

    def __iter__(self) -> Iterator[str]:
        for fid, *_ in self._bc.manifest_iter():
            yield fid

    def iteritems(self) -> Iterator[Tuple[str, T]]:
        for fid in self:
            yield fid, self[fid]

    def __enter__(self):
        return self

    def __exit__(self, *exc_info) -> None:
        self._data.clear()
        self._edit_stack.__exit__(*exc_info)

    def clear(self) -> None:
        self.__exit__(*sys.exc_info())

    __del__ = clear

    def __getitem__(self, fid) -> T:
        d = self._data
        if fid not in d:
            try:
                d[fid] = self._edit_stack.enter_context(
                    type(self).__context_factory__(self._bc, fid))
            except Exception as exc:
                raise KeyError(fid) from exc
        return d[fid]

    def read_id(self, key) -> T:
        '''Receive a file's manifest id, return the contents of the file, 
        otherwise raise KeyError'''
        return self[key]

    def read_href(self, key) -> T:
        '''Receive a file's OPF href, return the contents of the file, 
        otherwise raise KeyError'''
        try:
            return self[self._bc.href_to_id(key)]
        except Exception as exc:
            raise KeyError(key) from exc

    def read_basename(self, key) -> T:
        '''Receive a file's basename (with extension), return the contents of the file, 
        otherwise raise KeyError'''
        try:
            return self[self._bc.basename_to_id(key)]
        except Exception as exc:
            raise KeyError(key) from exc

    def read_bookpath(self, key) -> T:
        '''Receive a file's bookpath (aka 'book_href' aka 'bookhref'), 
        return the contents of the file, otherwise raise KeyError'''
        try:
            return self[self._bc.bookpath_to_id(key)]
        except Exception as exc:
            raise KeyError(key) from exc


class TextEtreeEditStack(EditStack[T]):

    __context_factory__ = ctx_edit_html

    def __iter__(self) -> Iterator[str]:
        for fid, *_ in self._bc.text_iter():
            yield fid

