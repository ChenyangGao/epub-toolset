__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 7)

from collections import namedtuple
from contextlib import contextmanager
from enum import Enum
from functools import partial
from inspect import getfullargspec, CO_VARARGS
from platform import system
from typing import (
    cast, Any, Callable, ContextManager, Dict, Generator, 
    Iterable, List, Mapping, Optional, Tuple, Union, 
)

from cssselect.xpath import GenericTranslator # type: ignore
from lxml.cssselect import CSSSelector # type: ignore
from lxml.etree import ( # type: ignore
    fromstring as _html_fromstring, tostring as _html_tostring, 
    _Element, _ElementTree, XPath, 
) 
from lxml.html import ( # type: ignore
    fromstring as xml_fromstring, tostring as xml_tostring, 
    Element, HtmlElement, HTMLParser, 
)


__all__ = [
    'WriteBack', 'DoNotWriteBack', 'xml_fromstring', 'xml_tostring', 
    'make_html_element', 'html_fromstring', 'html_tostring', 'edit', 
    'ctx_edit', 'ctx_edit_sgml', 'ctx_edit_html', 'edit_iter', 
    'edit_batch', 'edit_html_iter', 'edit_html_batch', 
    'IterElementInfo', 'EnumSelectorType', 'element_iter', 
]

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


def _posargcount(
    func: Callable,
    _T = namedtuple('Result', ('argcount', 'has_varargs')),
) -> Tuple[int, bool]:
    code = getattr(func, '__code__', None)
    if code:
        return _T(code.co_argcount, bool(code.co_flags & CO_VARARGS))
    try:
        argspec = getfullargspec(func)
    except:
        return _T(0, False)
    else:
        return _T(len(argspec.args), argspec.varargs is not None)


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


def make_html_element(
    tag: str, 
    text: Optional[str] = '', 
    children: Optional[List[HtmlElement]] = None,
    tail: Optional[str] = None, 
) -> HtmlElement:
    'Make a HtmlElement object'
    el = Element(tag)
    if text is not None:
        el.text = text
    if children is not None:
        el.extend(children)
    if tail is not None:
        el.tail = text
    return el


def html_fromstring(
    string: Union[str, bytes], 
    parser = _HTML_PARSER,
    **kwds
) -> _Element:
    '''Convert a string to `lxml.etree._Element` object 
    by using `lxml.html.fromstring` function

    Tips: Please refer the following documentation(s) for details
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
    el: Union[_Element, _ElementTree], method='html', **kwds
) -> bytes:
    '''Convert a root element node to string 
    by using `lxml.html.tostring` function

    Tips: Please refer the following documentation(s) for details
        - lxml.html.tostring
        - lxml.etree.tostring

    :param method: Defines the output method.
        It defaults to 'html', but can also be 'xml' or 'xhtml' for xhtml output, 
        or 'text' to serialise to plain text without markup.
    :param kwds: Keyword arguments `kwds` will be passed to 
        `lxml.html.tostring` function

    :return: An HTML string representation of the document
    '''
    roottree: _ElementTree = el.getroottree() if isinstance(el, _Element) else el
    root: _Element = roottree.getroot()
    docinfo  = roottree.docinfo
    encoding = kwds.get('encoding', docinfo.encoding)
    kwds.setdefault('encoding', encoding)
    doctype = kwds.pop('doctype', docinfo.doctype)

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
    bc,
    manifest_id: str,
    operate: Callable,
) -> bool:
    '''Read the file data, operate on, and then write the changed data back

    :param bc: `BookContainer` object. 
        An object of ePub book content provided by Sigil, 
        which can be used to access and operate the files in ePub
    :param manifest_id: Manifest id, be located in content.opf file, 
        The XPath as following (the `namespace` depends on the specific situation):
        /namespace:package/namespace:manifest/namespace:item/@id
    :param operate: Take data in, operate on, and then return the changed data

    :return: Is it successful?
    '''
    try:
        bc.writefile(manifest_id, operate(bc.readfile(manifest_id)))
    except:
        return False
    else:
        return True


@contextmanager
def ctx_edit(
    bc, 
    manifest_id: str,
    wrap_me: bool = False,
    extra_data: Optional[Mapping] = None,
):
    '''Read and yield the file data, and then take in and write back the changed data.

    :param bc: `BookContainer` object. 
        An object of ePub book content provided by Sigil, 
        which can be used to access and operate the files in ePub
    :param manifest_id: Manifest id, be located in content.opf file, 
        The XPath as following (the `namespace` depends on the specific situation):
        /namespace:package/namespace:manifest/namespace:item/@id
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

        with ctx_gen_edit(bc, manifest_id) as content:
            content_new = operations_on_content(content)
            if content != content_new:
                raise WriteBack(content_new)

        # OR equivalent to
        with ctx_edit(bc, manifest_id, wrap_me=True) as data:
            content = data['data']
            content_new = operations_on_content(content)
            if content == content_new:
                del data['data']
                # OR raise DoNotWriteBack
            else:
                data['data'] = content_new
    '''
    try:
        if wrap_me:
            data = {
                'manifest_id': manifest_id, 
                'data': bc.readfile(manifest_id),
                'write_back': True,
            }
            if extra_data:
                data.update(extra_data)
            while (yield data) is not None:
                pass
            if data.get('data') is None or not data.get('write_back'):
                raise DoNotWriteBack
            bc.writefile(manifest_id, data['data'])
        else:
            data = yield bc.readfile(manifest_id)
            if data is None:
                raise DoNotWriteBack
            while (yield None) is not None:
                pass
            bc.writefile(manifest_id, data)
    except WriteBack as exc:
        bc.writefile(manifest_id, exc.data)
    except DoNotWriteBack:
        pass


@contextmanager
def ctx_edit_sgml(
    bc, 
    manifest_id: str,
    fromstring: Callable = xml_fromstring,
    tostring: Callable[..., Union[bytes, bytearray, str]] = xml_tostring,
):
    '''Read and yield the etree object (parsed from a xml file), 
    and then write back the above etree object.

    :param bc: `BookContainer` object. 
        An object of ePub book content provided by Sigil, 
        which can be used to access and operate the files in ePub
    :param manifest_id: Manifest id, be located in content.opf file, 
        The XPath as following (the `namespace` depends on the specific situation):
        /namespace:package/namespace:manifest/namespace:item/@id
    :param fromstring: Parses an XML or SGML document or fragment from a string.
                       Returns the root node (or the result returned by a parser target).
    :param fromstring: Serialize an element to an encoded string representation of its XML
                       or SGML tree.

    Example::
        def operations_on_etree(etree):
            ...

        with ctx_edit_xml(bc, manifest_id) as etree:
            operations_on_etree(etree)
    '''
    tree = fromstring(bc.readfile(manifest_id).encode('utf-8'))
    try:
        if (yield tree) is not None:
            raise DoNotWriteBack
    except WriteBack as exc:
        content = exc.data
        if not isinstance(content, (bytes, bytearray, str)):
            content = tostring(content)
    except DoNotWriteBack:
        return
    else:
        content = tostring(tree)

    if isinstance(content, (bytes, bytearray)):
        content = content.decode('utf-8')
    bc.writefile(manifest_id, content)


def ctx_edit_html(bc, manifest_id: str) -> ContextManager:
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
    return ctx_edit_sgml(
        bc, 
        manifest_id, 
        html_fromstring, 
        partial(
            html_tostring, 
            method='xhtml' if 'xhtml' in bc.id_to_mime(manifest_id) else 'html',
        ),
    )


def edit_iter(
    bc, 
    manifest_id_s: Optional[Iterable[str]] = None,
    predicate: Optional[Callable[..., bool]] = None,
    wrap_me: bool = False,
    yield_cm: bool = False,
) -> Generator:
    '''Used to process a collection of specified files in ePub file one by one

    :param bc: `BookContainer` object. 
        An object of ePub book content provided by Sigil, 
        which can be used to access and operate the files in ePub
    :param manifest_id_s: Manifest id collection, be located in content.opf file,
        The XPath as following (the `namespace` depends on the specific situation):
        /namespace:package/namespace:manifest/namespace:item/@id
    :param predicate: If it is a callable, it will receive parameters in order (if possible)
                      (`manifest_id`, `href`, `mimetype`), and then determine whether to 
                      continue processing.
    :param wrap_me: Will pass to function ctx_edit as keyword argument.
    :param yield_cm: Determines whether each iteration returns the context manager.

    Example::
        def operations_on_content(data_old):
            ...
            return data_new

        edit_worker = edit_iter(bc, ('id1', 'id2'))
        for content in edit_worker:
            content_new = operations_on_content(content)
            if content != content_new:
                edit_worker.send(content_new)

        # OR equivalent to
        for cm in edit_iter(bc, ('id1', 'id2'), yield_cm=True):
            with cm as content:
                content_new = operations_on_content()
                if content != content_new:
                    raise WriteBack(content_new)

        # OR equivalent to
        for data in edit_iter(bc, ('id1', 'id2'), wrap_me=True):
            content = data['data']
            content_new = operations_on_content(content)
            if content == content_new:
                del data['data']
            else:
                data['data'] = content_new
    '''
    predicate = _make_standard_predicate(predicate)

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
    bc, 
    operate: Callable,
    manifest_id_s: Optional[Iterable[str]] = None,
    predicate: Optional[Callable[..., bool]] = None,
) -> Dict[str, bool]:
    '''Used to process a collection of specified files in ePub file one by one

    :param bc: `BookContainer` object. 
        An object of ePub book content provided by Sigil, 
        which can be used to access and operate the files in ePub
    :param manifest_id_s: Manifest id collection, be located in content.opf file,
        The XPath as following (the `namespace` depends on the specific situation):
        /namespace:package/namespace:manifest/namespace:item/@id
    :param operate: Take data in, operate on, and then return the changed data
    :param predicate: If it is a callable, it will receive parameters in order (if possible)
                      (`manifest_id`, `href`, `mimetype`), and then determine whether to 
                      continue processing.

    Example::
        def operations_on_content(data_old):
            ...
            return data_new

        edit_batch(bc, operations_on_content, ('id1', 'id2'))
    '''
    predicate = _make_standard_predicate(predicate)

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
            with ctx_edit(bc, fid, wrap_me=True) as data:
                data['data'] = operate(data['data'])
            success_status[fid] = True
        except:
            success_status[fid] = False
    return success_status


def edit_html_iter(
    bc,
    predicate: Optional[Callable[..., bool]] = None,
    wrap_me: bool = False,
) -> Generator[Union[None, _Element, dict], Any, None]:
    '''Used to process a collection of specified html files in ePub file one by one

    :param bc: `BookContainer` object. 
        An object of ePub book content provided by Sigil, 
        which can be used to access and operate the files in ePub
    :param predicate: If it is a callable, it will receive parameters in order (if possible)
                      (`manifest_id`, `href`, `mimetype`), and then determine whether to 
                      continue processing.
    :param wrap_me: Whether to wrap up object, if True, return a dict containing keys 
                    ('manifest_id', 'href', 'mimetype', 'etree', 'write_back')

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
        for data in edit_html_iter(bc, True):
            operations_on_etree(data['etree'])
            ## if no need to write back
            # data['write_back'] = False
            ## OR
            # del data['write_back']
    '''
    predicate = _make_standard_predicate(predicate)

    for fid, href in bc.text_iter():
        mime = bc.id_to_mime(fid)
        if not predicate(fid, href, mime):
            continue
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
                while (yield data) is not None:
                    pass


def edit_html_batch(
    bc, 
    operate: Callable[[_Element], Any],
    predicate: Optional[Callable[..., bool]] = None,
) -> Dict[str, bool]:
    '''Used to process a collection of specified html files in ePub file one by one

    :param bc: `BookContainer` object. 
        An object of ePub book content provided by Sigil, 
        which can be used to access and operate the files in ePub.
    :param operate: Take etree object in, operate on
    :param predicate: If it is a callable, it will receive parameters in order (if possible)
                      (`manifest_id`, `href`, `mimetype`), and then determine whether to 
                      continue processing.

    Example::
        def operations_on_etree(etree):
            ...

        edit_html_batch(bc, operations_on_etree)
    '''
    predicate = _make_standard_predicate(predicate)

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


IterElementInfo = namedtuple(
    'IterElementInfo', 
    ('global_no', 'local_no', 'element', 'etree', 'manifest_id', 'href'),
)


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
    bc, 
    path: Union[str, XPath], 
    seltype: Union[int, str, EnumSelectorType] = EnumSelectorType.cssselect, 
    namespaces: Optional[Mapping] = None, 
    translator: Union[str, GenericTranslator] = 'xml',
    predicate: Optional[Callable[..., bool]] = None,
    wrap_yield: bool = True,
) -> Union[Generator[IterElementInfo, None, None], Generator[_Element, None, None]]:
    '''Traverse all (X)HTML files in epub, search the elements that match the path, 
    and return the relevant information of these elements one by one.

    :param bc: `BookContainer` object. 
        An object of ePub book content provided by Sigil, 
        which can be used to access and operate the files in ePub.
    :param path: A XPath expression or CSS Selector expression.
                 If its `type` is `str`, then it is a XPath expression or 
                 CSS Selector expression determined by `seltype`.
                 If its type is a subclass of 'lxml.etree.XPath'`, then 
                 parameters `seltype`, `namespaces`, `translator` are ignored.
    :param seltype: Selector type. It can be any value that can be 
                    accepted by `EnumSelectorType.of`, the return value called final value.
                    If its final value is `EnumSelectorType.xpath`, then parameter
                    `translator` is ignored.
    :param predicate: If it is a callable, it will receive parameters in order (if possible)
                      (`manifest_id`, `href`, `mimetype`), and then determine whether to 
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

        for info in element_iter(bc):
            operations_on_element(info.element)
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
                    i, j, el, tree, data['manifest_id'], data['href'])
        else:
            yield from els

