__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 1)

from lxml.etree import ElementBase

from utils.form import ask_form
from utils.sigil_edit_file import DoNotWriteBack, ctx_edit_xhtml


def replace_notelabel(el: ElementBase, text: str) -> None:
    '修改脚注的标签'
    while el.tag != 'a':
        el = el.getparent()
        if el.tag != 'a':
            a = el.find('.//a')
            if a is not None:
                el = a

    while len(el):
        el = el[0]

    el.text = text


def renumber_notes(tree: ElementBase, expr: str, method='csssel') -> None:
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

    for i, note in enumerate(notes, 1):
        noteno = '[%d]' % i
        replace_notelabel(note, noteno)
        note_href = note.attrib['href']
        id_idx = note_href.index('#') + 1
        if id_idx:
            noteref_id = note_href[id_idx:]
            noteref = body.find(".//*[@id='%s']" %noteref_id)
            replace_notelabel(noteref, noteno)


def run(bc):
    state = ask_form()
    if not state.get('expr'):
        print('你好像没有输入表达式')
        return 1

    for fid, _ in bc.text_iter():
        with ctx_edit_xhtml(bc, fid) as tree:
            renumber_notes(tree, **state)

    return 0

