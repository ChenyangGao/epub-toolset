__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 6)

from collections import namedtuple
from contextlib import contextmanager
from enum import Enum
from platform import system
from typing import (
    Any, Callable, Dict, Generator, Iterable, 
    List, Mapping, Optional, Tuple, Union, 
)

from cssselect.xpath import GenericTranslator # type: ignore
from lxml.cssselect import CSSSelector # type: ignore
from lxml.etree import _Element, _ElementTree, XPath # type: ignore
from lxml.html import fromstring, tostring, Element, HtmlElement, HTMLParser # type: ignore


__all__ = ['DoNotWriteBack', 'make_html_element', 'html_fromstring', 'html_tostring', 
           'edit_file','ctx_gen_edit', 'ctx_edit', 'ctx_edit_html', 'gen_edit', 
           'iter_edit', 'batch_edit', 'gen_edit_html', 'batch_edit_html', 
           'IterElementInfo', 'EnumSelectorType', 'iter_elements', ]

_PLATFORM_IS_WINDOWS = system() == 'Windows'
_HTML_DOCTYPE = b'<!DOCTYPE html>'
_XHTML_DOCTYPE = (b'<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" '
                  b'"http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">')
_HTML_PARSER = HTMLParser(default_doctype=False)


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
        return fromstring(
            b'<html>\n    <head/>\n    <body/>\n</html>', 
            parser=parser, **kwds)
    tree = fromstring(string, parser=parser, **kwds)
    # get root element
    for tree in tree.iterancestors(): pass
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
        b'doc': tostring(root, method=method, **kwds),
    }
    if _PLATFORM_IS_WINDOWS:
        string = string.replace(b'&#13;', b'')
    return string


def edit_file(
    bc,
    manifest_id: str,
    operate: Callable,
) -> None:
    '''Read the file data, operate on, and then write the changed data back

    :param bc: `BookContainer` object. 
        An object of ePub book content provided by Sigil, 
        which can be used to access and operate the files in ePub
    :param manifest_id: Manifest id, be located in content.opf file, 
        The XPath as following (the `namespace` depends on the specific situation):
        /namespace:package/namespace:manifest/namespace:item/@id
    :param operate: Take data in, operate on, and then return the changed data
    '''
    bc.writefile(manifest_id, operate(bc.readfile(manifest_id)))


@contextmanager
def ctx_gen_edit(bc, manifest_id: str):
    '''Read and yield the file data, and then take in and write back the changed data

    :param bc: `BookContainer` object. 
        An object of ePub book content provided by Sigil, 
        which can be used to access and operate the files in ePub
    :param manifest_id: Manifest id, be located in content.opf file, 
        The XPath as following (the `namespace` depends on the specific situation):
        /namespace:package/namespace:manifest/namespace:item/@id

    :return: The context manager that returns the `data`
        data := bc.readfile(manifest_id)

    Example::
        def operations_on_content(data_old):
            ...
            return data_new

        ctx = ctx_gen_edit(bc, manifest_id)
        with ctx as content:
            content_new = operations_on_content(content)
            if content != content_new:
                ctx.gen.send(content_new)
    '''
    try:
        result = yield bc.readfile(manifest_id)
    except DoNotWriteBack:
        yield None
    else:
        if result is not None:
            bc.writefile(manifest_id, result)
            yield None


@contextmanager
def ctx_edit(bc, manifest_id: str):
    '''Read and yield the file data, and then take in and write back the changed data

    :param bc: `BookContainer` object. 
        An object of ePub book content provided by Sigil, 
        which can be used to access and operate the files in ePub
    :param manifest_id: Manifest id, be located in content.opf file, 
        The XPath as following (the `namespace` depends on the specific situation):
        /namespace:package/namespace:manifest/namespace:item/@id

    :return: The context manager that returns the `data`
        data := {'manifest_id': manifest_id, 'data': bc.readfile(manifest_id)}

    Example::
        def operations_on_content(data_old):
            ...
            return data_new

        with ctx_edit(bc, manifest_id) as data:
            content = data['data']
            content_new = operations_on_content(content)
            if content == content_new:
                del data['data']
                # OR raise DoNotWriteBack
            else:
                data['data'] = content_new
    '''
    data = {'manifest_id': manifest_id, 'data': bc.readfile(manifest_id)}
    try:
        if (yield data) is not None or data.get('data') is None:
            raise DoNotWriteBack
    except DoNotWriteBack:
        pass
    else:
        bc.writefile(manifest_id, data['data'])


@contextmanager
def ctx_edit_html(bc, manifest_id: str):
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


def gen_edit(
    bc, manifest_id_s: Iterable[str]
) -> Generator[Union[None, bytes, str], Optional[Union[bytes, str]], None]:
    '''Used to process a collection of specified files in ePub file one by one

    :param bc: `BookContainer` object. 
        An object of ePub book content provided by Sigil, 
        which can be used to access and operate the files in ePub
    :param manifest_id_s: Manifest id collection, be located in content.opf file,
        The XPath as following (the `namespace` depends on the specific situation):
        /namespace:package/namespace:manifest/namespace:item/@id

    Example::
        def operations_on_content(data_old):
            ...
            return data_new

        edit_worker = gen_edit(bc, ('id1', 'id2'))
        for content in edit_worker:
            content_new = operations_on_content(content)
            if content != content_new:
                edit_worker.send(content_new)
    '''
    for fid in manifest_id_s:
        try:
            result = yield bc.readfile(fid)
        except DoNotWriteBack:
            yield None
        else:
            if result is not None:
                bc.writefile(fid, result)
                yield None


def iter_edit(
    bc, manifest_id_s: Iterable[str]
) -> Generator[Optional[dict], Any, None]:
    '''Used to process a collection of specified files in ePub file one by one

    :param bc: `BookContainer` object. 
        An object of ePub book content provided by Sigil, 
        which can be used to access and operate the files in ePub
    :param manifest_id_s: Manifest id collection, be located in content.opf file,
        The XPath as following (the `namespace` depends on the specific situation):
        /namespace:package/namespace:manifest/namespace:item/@id

    Example::
        def operations_on_content(data_old):
            ...
            return data_new

        for data in iter_edit(bc, ('id1', 'id2')):
            content = data['data']
            content_new = operations_on_content(content)
            if content == content_new:
                del data['data']
            else:
                data['data'] = content_new
    '''
    for fid in manifest_id_s:
        op = 0
        with ctx_edit(bc, fid) as data:
            op = yield data
            if op is not None:
                raise DoNotWriteBack
        while op is not None:
            op = yield None


def batch_edit(
    bc, 
    manifest_id_s: Iterable[str], 
    operate: Callable,
) -> Dict[str, bool]:
    '''Used to process a collection of specified files in ePub file one by one

    :param bc: `BookContainer` object. 
        An object of ePub book content provided by Sigil, 
        which can be used to access and operate the files in ePub
    :param manifest_id_s: Manifest id collection, be located in content.opf file,
        The XPath as following (the `namespace` depends on the specific situation):
        /namespace:package/namespace:manifest/namespace:item/@id
    :param operate: Take data in, operate on, and then return the changed data

    Example::
        def operations_on_content(data_old):
            ...
            return data_new

        batch_edit(bc, ('id1', 'id2'), operations_on_content)
    '''
    success_status: Dict[str, bool] = {}
    for fid in manifest_id_s:
        try:
            with ctx_edit(bc, fid) as data:
                data['data'] = operate(data['data'])
            success_status[fid] = True
        except:
            success_status[fid] = False
    return success_status


def gen_edit_html(bc) -> Generator[Optional[_Element], Any, None]:
    '''Used to process a collection of specified html files in ePub file one by one

    :param bc: `BookContainer` object. 
        An object of ePub book content provided by Sigil, 
        which can be used to access and operate the files in ePub

    Example::
        def operations_on_etree(etree):
            ...

        edit_worker = gen_edit_html(bc)
        for etree in edit_worker:
            operations_on_etree(etree)
            ## if no need to write back
            # edit_worker.throw(DoNotWriteBack)
            ## OR
            # edit_worker.send(0)
    '''
    for fid, _ in bc.text_iter():
        op = 0
        with ctx_edit_html(bc, fid) as tree:
            op = yield tree
            if op is not None:
                raise DoNotWriteBack
        while op is not None:
            op = yield None


def batch_edit_html(
    bc, 
    operate: Callable[[_Element], Any],
) -> Dict[str, bool]:
    '''Used to process a collection of specified html files in ePub file one by one

    :param bc: `BookContainer` object. 
        An object of ePub book content provided by Sigil, 
        which can be used to access and operate the files in ePub.
    :param operate: Take etree object in, operate on

    Example::
        def operations_on_etree(etree):
            ...

        batch_edit_html(bc, operations_on_etree)
    '''
    success_status: Dict[str, bool] = {}
    for fid, _ in bc.text_iter():
        try:
            with ctx_edit_html(bc, fid) as tree:
                operate(tree)
            success_status[fid] = True
        except:
            success_status[fid] = False   
    return success_status


IterElementInfo = namedtuple(
    'IterElementInfo', 
    ('global_no', 'local_no', 'el', 'etree', 'manifest_id', 'href'),
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


def iter_elements(
    bc, 
    path: Union[str, XPath], 
    seltype: Union[int, str, EnumSelectorType] = EnumSelectorType.cssselect, 
    namespaces: Optional[Mapping] = None, 
    translator: Union[str, GenericTranslator] = 'xml',
) -> Generator[IterElementInfo, None, None]:
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

    :return: Generator, yield `IterElementInfo` object.
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

    i = 0
    for fid, href in bc.text_iter():
        with ctx_edit_html(bc, fid) as tree:
            els = select(tree)
            if not els:
                raise DoNotWriteBack
            for i, (j, el) in enumerate(enumerate(els, 1), i + 1):
                yield IterElementInfo(i, j, el, tree, fid, href)

