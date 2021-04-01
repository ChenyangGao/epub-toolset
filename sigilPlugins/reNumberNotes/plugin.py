__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 3)

from lxml.etree import _Element # type: ignore
from lxml.html import tostring # type: ignore

from utils.form import ask_form
from utils.sigil_edit_file import DoNotWriteBack, ctx_edit_html


# TODO: 编号格式: 用 %d 指代编号，[%d]:1，表示从 1 开始，产生 [1], [2], ...


def replace_notelabel(
    el: _Element, 
    text: str,
) -> None:
    '修改脚注的标签'
    while el.tag != 'a':
        a = el.find('.//a')
        if a is None:
            el = el.getparent()
            if el is None:
                return
        else:
            el = a

    while len(el):
        el = el[0]

    el.text = text


def renumber_notes(
    tree: _Element, 
    start: int = 1,
    expr: str = '', 
    method: str = 'csssel',
    only_modify_text: bool = False,
) -> int:
    '批量对脚注标签进行编号'
    body = tree.body
    if method == 'csssel':
        notes = body.cssselect(expr)
    elif method == 'xpath':
        notes = body.xpath(expr)
    else:
        raise NotImplementedError('method %r is not implemented for %r' 
                                  % (method, renumber_notes))

    if not notes:
        raise DoNotWriteBack

    i = None
    for i, note in enumerate(notes, start):
        noteno = '[%d]' % i
        if only_modify_text:
            note.text = noteno
        else:
            replace_notelabel(note, noteno)
            note_href = note.attrib['href']
            id_idx = note_href.find('#') + 1
            if id_idx:
                noteref_id = note_href[id_idx:]
                noteref = body.find(".//*[@id='%s']" %noteref_id)
                if noteref is None:
                    print('没有（被）引用：', 
                        tostring(note, encoding='utf-8').strip().decode('utf-8'))
                else:
                    replace_notelabel(noteref, noteno)
    if i is None:
        return start
    return i + 1


def run(bc):
    state = ask_form()
    if not state.get('expr'):
        print('你好像没有输入表达式')
        return 1

    unique_strategy = state.pop('unique_strategy', 'inhtml')
    if unique_strategy == 'inhtml':
        for fid, href in bc.text_iter():
            print('处理文件：', href)
            with ctx_edit_html(bc, fid) as tree:
                renumber_notes(tree, **state)
    elif unique_strategy == 'inepub':
        i = 1
        for fid, href in bc.text_iter():
            print('处理文件：', href)
            with ctx_edit_html(bc, fid) as tree:
                i = renumber_notes(tree, start=i, **state)
    else:
        raise ValueError(f"unacceptable `unique_strategy`, expected value in "
                         "('inhtml', 'inepub'), got {unique_strategy!r}")

    return 0

