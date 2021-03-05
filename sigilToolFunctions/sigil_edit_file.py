__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 2)

from platform import system
from contextlib import contextmanager
from typing import (
    Any, Callable, Dict, Generator, Iterable, 
    Optional, Tuple, Union, 
)

from lxml.etree import _Element, _ElementTree # type: ignore
from lxml.html import fromstring, tostring, HTMLParser # type: ignore


__all__ = ['DoNotWriteBack', 'html_fromstring', 'html_tostring', 'edit_file',
           'ctx_edit_file', 'ctx_edit_html', 'iter_edit', 'gen_edit', 
           'batch_edit', 'gen_edit_html', 'batch_edit_html']

_PLATFORM_IS_WINDOWS = system() == 'Windows'
_HTML_DOCTYPE = b'<!DOCTYPE html>'
_XHTML_DOCTYPE = (b'<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" '
                  b'"http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">')
_HTML_PARSER = HTMLParser(default_doctype=False)


class DoNotWriteBack(Exception):
    '如果对文件改动不需要写回文件，则抛出此异常'


def _ensure_bytes(o: Any) -> bool:
    if isinstance(o, bytes):
        return o
    elif isinstance(o, str):
        return bytes(o, encoding='utf-8')
    else:
        return bytes(o)


def html_fromstring(
    string: Union[str, bytes], 
    parser = _HTML_PARSER,
    **kwds
) -> _Element:
    '把一个字符串转换成 lxml.etree._Element 对象'
    return fromstring(string, parser=parser, **kwds)


def html_tostring(
    el: Union[_Element, _ElementTree], method='html', **kwds
) -> bytes:
    '把一个 lxml.etree._Element 对象的根元素节点转换成字符串'
    roottree: _ElementTree = el.getroottree() if isinstance(el, _Element) else el
    root: _Element = roottree.getroot()
    docinfo  = roottree.docinfo
    encoding = kwds.get('encoding', docinfo.encoding)
    kwds.setdefault('encoding', encoding)
    doctype = kwds.pop('doctype', docinfo.doctype)
    if not doctype:
        if method == 'html':
            doctype = _HTML_DOCTYPE
        elif method == 'xml':
            doctype = _XHTML_DOCTYPE
    string = (
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
    '''读取文件的数据，进行操作，然后把改动后的数据写回

    :param bc: BookContainer 对象，由 Sigil 提供的 epub 书籍内容的一个对象，
        可以利用它访问并操作 epub 内的文件
    :param manifest_id: 清单id，位于 content.opf 文件内，
        xpath 定位为（下面的 namespace 视具体情况而定）：
        /namespace:package/namespace:manifest/namespace:item/@id
    :param operate: 对数据进行操作，然后返回改动后的数据
    '''
    bc.writefile(manifest_id, operate(bc.readfile(manifest_id)))


@contextmanager
def ctx_edit_file(bc, manifest_id: str):
    '''上下文管理器，可用于修改文件内容，对文件的修改会在结束时都会保存到原文件，
    除非期间发生异常。

    :param bc: BookContainer 对象，由 Sigil 提供的 epub 书籍内容的一个对象，
        可以利用它访问并操作 epub 内的文件
    :param manifest_id: 清单id，位于 content.opf 文件内，
        xpath 定位为（下面的 namespace 视具体情况而定）：
        /namespace:package/namespace:manifest/namespace:item/@id

    使用方式形如：
        with edit_file(bc, manifest_id) as data:
            content = data['data']
            content_new = operations_on_content(content)
            if content == content_new:
                raise DoNotWriteBack
            data['data'] = content_new
    '''
    data = {'manifest_id': manifest_id, 'data': bc.readfile(manifest_id)}
    try:
        yield data
    except DoNotWriteBack:
        pass
    else:
        if data.get('data') is not None:
            bc.writefile(manifest_id, data['data'])


@contextmanager
def ctx_edit_html(bc, manifest_id: str):
    '''上下文管理器，可用于修改 Text/*.xhtml，由 xhtml 文件得到一个
    xml 树对象，对它的任何修改，在结束时都会保存到原文件，除非期间发生异常。

    :param bc: BookContainer 对象，由 Sigil 提供的 epub 书籍内容的一个对象，
        可以利用它访问并操作 epub 内的文件
    :param manifest_id: 清单id，位于 content.opf 文件内，
        xpath 定位为（下面的 namespace 视具体情况而定）：
        /namespace:package/namespace:manifest/namespace:item/@id

    使用方式形如：
        with edit_xhtml(bc, manifest_id) as etree:
            operations_on_etree(etree)
    '''
    tree = html_fromstring(bc.readfile(manifest_id).encode('utf-8'))
    try:
        yield tree
    except DoNotWriteBack:
        pass
    else:
        method = 'xml' if 'xhtml' in bc.id_to_mime(manifest_id) else 'html'
        bc.writefile(
            manifest_id, 
            html_tostring(tree, method=method).decode('utf-8')
        )


def iter_edit(
    bc, manifest_id_s: Iterable[str]
) -> Generator[dict, Any, None]:
    '''用于逐个处理在 ePub 文件中的一组指定文件

    :param bc: BookContainer 对象，由 Sigil 提供的 epub 书籍内容的一个对象，
        可以利用它访问并操作 epub 内的文件
    :param manifest_id_s: 一组清单 id，清单 id 位于 content.opf 文件内，
        xpath 定位为（下面的 namespace 视具体情况而定）：
        /namespace:package/namespace:manifest/namespace:item/@id

    使用方式形如：
        for data in iter_edit(bc, ('id1', 'id2')):
            content = data['data']
            content_new = operations_on_content(content)
            if content == content_new:
                del data['data']
            else:
                data['data'] = content_new
    '''
    for fid in manifest_id_s:
        with ctx_edit_file(bc, fid) as data:
            yield data


def gen_edit(
    bc, manifest_id_s: Iterable[str]
) -> Generator[Union[bytes, str], Optional[Union[bytes, str]], None]:
    '''用于逐个处理在 ePub 文件中的一组指定文件

    :param bc: BookContainer 对象，由 Sigil 提供的 epub 书籍内容的一个对象，
        可以利用它访问并操作 epub 内的文件
    :param manifest_id_s: 一组清单 id，清单 id 位于 content.opf 文件内，
        xpath 定位为（下面的 namespace 视具体情况而定）：
        /namespace:package/namespace:manifest/namespace:item/@id

    使用方式形如：
        edit_worker = iter_edit(bc, ('id1', 'id2'))
        for content in edit_worker:
            content_new = operations_on_content(content)
            if content != content_new:
                edit_worker.send(content_new)
    '''
    for fid in manifest_id_s:
        try:
            result = yield bc.readfile(fid)
        except DoNotWriteBack:
            yield ''
        else:
            if result is not None:
                bc.writefile(fid, result)
                yield ''


def batch_edit(
    bc, 
    manifest_id_s: Iterable[str], 
    operate: Callable,
) -> Dict[str, bool]:
    '''用于逐个处理在 ePub 文件中的一组指定文件

    :param bc: BookContainer 对象，由 Sigil 提供的 epub 书籍内容的一个对象，
        可以利用它访问并操作 epub 内的文件
    :param manifest_id_s: 一组清单 id，清单 id 位于 content.opf 文件内，
        xpath 定位为（下面的 namespace 视具体情况而定）：
        /namespace:package/namespace:manifest/namespace:item/@id
    :param operate: 对数据进行操作，然后返回改动后的数据

    使用方式形如：
        batch_edit(bc, ('id1', 'id2'), operations_on_content)
    '''
    success_status: Dict[str, bool] = {}
    for fid in manifest_id_s:
        try:
            result = operate(bc.readfile(fid))
            if result is not None:
                bc.writefile(fid, result)
            success_status[fid] = True
        except DoNotWriteBack:
            success_status[fid] = True
        except:
            success_status[fid] = False
    return success_status


def gen_edit_html(bc) -> Generator[_Element, Any, None]:
    '''用于逐个处理 ePub 文件中的 xhtml 文件

    :param bc: BookContainer 对象，由 Sigil 提供的 epub 书籍内容的一个对象，
        可以利用它访问并操作 epub 内的文件

    使用方式形如：
        edit_worker = gen_edit_xhtml(bc, ('id1', 'id2'))
        for tree in edit_worker:
            operations_on_tree(tree)
            ## if no need to write back
            # edit_worker.throw(DoNotWriteBack)
            ## OR
            # edit_worker.send(1)
    '''
    for fid, _ in bc.text_iter():
        tree = html_fromstring(bc.readfile(fid).encode('utf-8'))
        try:
            op = yield tree
        except DoNotWriteBack:
            yield
        else:
            if op is not None:
                yield
            else:
                method = 'xml' if 'xhtml' in bc.id_to_mime(fid) else 'html'
                bc.writefile(
                    fid, 
                    html_fromstring(tree, method=method).decode('utf-8')
                )


def batch_edit_html(
    bc, 
    operate: Callable[[_Element], Any],
) -> Dict[str, bool]:
    '''用于逐个处理 ePub 文件中的 xhtml 文件

    :param bc: BookContainer 对象，由 Sigil 提供的 epub 书籍内容的一个对象，
        可以利用它访问并操作 epub 内的文件
    :param operate: 对 xhtml 树对象进行处理

    使用方式形如：
        batch_edit_xhtml(bc, operations_on_tree)
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

