__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 4)

from lxml.html import tostring

from utils.form import AskForm
from utils.edithtml import DoNotWriteBack, ctx_edit_html


def replace_notelabel(el, text):
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
    tree,
    select,
    start=1,
    numfmt='[%d]',
    only_modify_text=False,
):
    '批量对脚注标签进行编号'
    body = tree.body
    notes = select(body)

    if not notes:
        raise DoNotWriteBack

    i = None
    for i, note in enumerate(notes, start):
        noteno = numfmt % i
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
    state = AskForm.ask()
    if not state:
        print('已取消')
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
        raise ValueError("Unacceptable `unique_strategy`, expected value in "
                         "('inhtml', 'inepub'), got %r" % unique_strategy)

    return 0

