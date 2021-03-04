import platform

from contextlib import contextmanager
from typing import (
    Any, Callable, Dict, Generator, Iterable, 
    Optional, Tuple, Union, 
)

from lxml.etree import ElementBase # type: ignore
from lxml.html import fromstring, tostring # type: ignore


__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 2)


__all__ = ['DoNotWriteBack', 'xhtml_fromstring', 'xhtml_tostring', 'edit_file',
           'ctx_edit_file', 'ctx_edit_xhtml', 'iter_edit', 'gen_edit', 
           'batch_edit', 'gen_edit_xhtml', 'batch_edit_xhtml']


_PLATFORM_IS_WINDOWS = platform.system() == 'Windows'


class DoNotWriteBack(Exception):
    '如果对文件改动不需要写回文件，则抛出此异常'


def xhtml_fromstring(
    text: Union[str, bytes], **kwds
) -> ElementBase:
    '把一个字符串转换成 lxml.etree.ElementBase 对象'
    return fromstring(text, **kwds)


def xhtml_tostring(
    el: ElementBase, **kwds
) -> bytes:
    '把一个 lxml.etree.ElementBase 对象的根元素节点转换成字符串'
    roottree = el.getroottree()
    docinfo  = roottree.docinfo
    encoding = docinfo.encoding or 'utf-8'
    xml_version = docinfo.xml_version or '1.0'
    kwds.setdefault('method', 'xml')
    if docinfo.doctype:
        kwds.setdefault('doctype', docinfo.doctype)
    result = b'<?xml version="%s" encoding="%s"?>\n%s' % (
        xml_version.encode(),
        encoding.encode(),
        tostring(roottree.getroot(), encoding=encoding, **kwds),
    )
    # Because on windows, '\r' will be converted to '&#13;', this may seem redundant
    if _PLATFORM_IS_WINDOWS:
        result = result.replace(b'&#13;', b'')
    return result


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
def ctx_edit_xhtml(
    bc, 
    manifest_id: str, 
    fromstring: Callable[..., ElementBase] = xhtml_fromstring, 
    tostring: Callable[[ElementBase], bytes] = xhtml_tostring,
):
    '''上下文管理器，可用于修改 Text/*.xhtml，由 xhtml 文件得到一个
    xml 树对象，对它的任何修改，在结束时都会保存到原文件，除非期间发生异常。

    :param bc: BookContainer 对象，由 Sigil 提供的 epub 书籍内容的一个对象，
        可以利用它访问并操作 epub 内的文件
    :param manifest_id: 清单id，位于 content.opf 文件内，
        xpath 定位为（下面的 namespace 视具体情况而定）：
        /namespace:package/namespace:manifest/namespace:item/@id
    :param fromstring: 把字节字符串（或字符串）转化成 xhtml 树对象 
    :param tostring: 把 xhtml 树对象转化成字节字符串

    使用方式形如：
        with edit_xhtml(bc, manifest_id) as etree:
            operations_on_etree(etree)
    '''
    tree = fromstring(bc.readfile(manifest_id).encode('utf-8'))
    try:
        yield tree
    except DoNotWriteBack:
        pass
    else:
        bc.writefile(manifest_id, tostring(tree).decode('utf-8'))


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
        except DoNotWriteBack:
            success_status[fid] = True
        except:
            success_status[fid] = False
        else:
            success_status[fid] = True
    return success_status


def gen_edit_xhtml(
    bc,
    fromstring: Callable[..., ElementBase] = xhtml_fromstring, 
    tostring: Callable[[ElementBase], bytes] = xhtml_tostring,
) -> Generator[ElementBase, Any, None]:
    '''用于逐个处理 ePub 文件中的 xhtml 文件

    :param bc: BookContainer 对象，由 Sigil 提供的 epub 书籍内容的一个对象，
        可以利用它访问并操作 epub 内的文件
    :param fromstring: 把字节字符串（或字符串）转化成 xhtml 树对象 
    :param tostring: 把 xhtml 树对象转化成字节字符串

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
        tree = fromstring(bc.readfile(fid).encode('utf-8'))
        try:
            op = yield tree
        except DoNotWriteBack:
            yield
        else:
            if op is not None:
                yield
            else:
                bc.writefile(fid, tostring(tree).decode('utf-8'))


def batch_edit_xhtml(
    bc, 
    operate: Callable[[ElementBase], Any],
    fromstring: Callable[..., ElementBase] = xhtml_fromstring, 
    tostring: Callable[[ElementBase], bytes] = xhtml_tostring,
) -> Dict[str, bool]:
    '''用于逐个处理 ePub 文件中的 xhtml 文件

    :param bc: BookContainer 对象，由 Sigil 提供的 epub 书籍内容的一个对象，
        可以利用它访问并操作 epub 内的文件
    :param operate: 对 xhtml 树对象进行处理
    :param fromstring: 把字节字符串（或字符串）转化成 xhtml 树对象 
    :param tostring: 把 xhtml 树对象转化成字节字符串

    使用方式形如：
        batch_edit_xhtml(bc, operations_on_tree)
    '''
    success_status: Dict[str, bool] = {}
    for fid, _ in bc.text_iter():
        try:
            with ctx_edit_xhtml(
                bc, fid, fromstring=fromstring, tostring=tostring
            ) as tree:
                operate(tree)
        except:
            success_status[fid] = False
        else:
            success_status[fid] = True
    return success_status

