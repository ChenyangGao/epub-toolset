__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 6)

from contextlib import ExitStack
from os.path import basename
from urllib.parse import urldefrag, unquote

from utils.sigil_edit_file import ctx_edit_xhtml

try:
    from PyQt5.QtWidgets import QApplication, QMessageBox

    app = QApplication([])

    def message_dialog(title: str= 'Message', message: str = 'Yes or No') -> bool:
        reply = QMessageBox.question(None, title, message, QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        return reply == QMessageBox.Yes
except ImportError:
    from tkinter import Tk, messagebox 

    app = Tk()
    app.withdraw()

    def message_dialog(title: str= 'Message', message: str = 'Yes or No') -> bool:
        return messagebox.askyesno(title, message)
finally:
    import atexit

    atexit.register(app.quit)


def is_only_child(el):
    'determine whether an element is the only child (including text nodes) of its parent'
    pel = el.getparent()
    if pel is None:
        return True
    if len(pel) > 1:
        return False
    pred_text = el.xpath('preceding::text()[1]')
    if pred_text and pred_text[0].strip():
        return False
    folw_text = el.xpath('following::text()[1]')
    if folw_text and folw_text[0].strip():
        return False
    return True


def is_first_child(el):
    'determine whether an element is the first child (including text nodes) of its parent'
    pred_text = el.xpath('preceding::text()[1]')
    if pred_text and pred_text[0].strip():
        return False
    pel = el.getparent()
    if pel is None:
        return True
    return pel[0] is el


def is_first_only_descendant(el):
    ''
    while is_only_child(el):
        el = el.getparent()
    return is_first_child(el)


def run(bc):
    is_move_all = message_dialog('Message', '是否把所有脚注移动到末尾？')

    with ExitStack() as stack:
        path_item_map = {
            unquote(basename(path)):
                {'id': fid, 'data': stack.enter_context(ctx_edit_xhtml(bc, fid))} 
            for fid, path in bc.text_iter()
        }

        for path_noteref, item_noteref in path_item_map.items():
            etree_noteref = item_noteref['data']

            body = etree_noteref.body
            if body is None:
                continue
            for noteref in body.xpath('.//*[@id]'):
                # 查找所有 引用 注释的标签
                # 假设: 引用脚注 是一个有 id 属性元素，而且它不是它的祖先元素的 首位唯一后代
                # * 首位唯一后代：如果一个元素 el 没有父元素，或者可以找到它的一个祖先元素，这个
                #              祖先元素没有父元素，或者是其父元素的首位孩子且不是其父元素的唯一孩子，
                #              并且这个祖先元素的所有后代元素中从其子元素到 el 的都是唯一孩子。
                # * 首位孩子：如果一个元素 el 没有父元素，或者它的前面没有兄弟元素且
                #           如果前面有文本节点则只包含空白符号。
                # * 唯一孩子：如果一个元素 el 没有父元素，或者父元素只有它一个孩子元素，且它没有兄弟文字
                #           节点或者兄弟文字节点中只有空白符号。唯一孩子必是首位孩子。
                noteref_id = noteref.attrib['id']
                # 假设：某个脚注的 id 和 href 可能分别位于不同的元素节点中，必须保证包含 id 的标签**不位于**
                #      包含 href 的标签之外或者之后，如果互为兄弟节点则这两者是紧邻的（中间没有穿插其它元素节点）
                hrefs = noteref.xpath('descendant-or-self::a/@href')
                if not hrefs:
                    noteref_next_sibling = noteref.getnext()
                    hrefs = noteref_next_sibling.xpath('descendant-or-self::a/@href')
                if hrefs:
                    noteref_href = hrefs[0]
                else:
                    continue

                if is_first_only_descendant(noteref):
                    continue

                url, footnote_id = urldefrag(noteref_href)

                if (
                    url              # url 不为空，否则 footnoot 在同一个文件
                    and footnote_id  # hashtag 不为空，否则点击并不会发生跳转
                ):
                    path_footnote = unquote(basename(url))

                    if not is_move_all:
                        # 如果 noteref 和 footnote 在同一个文件，则跳过
                        if path_noteref == path_footnote: 
                            continue

                    try:
                        item_footnote = path_item_map[path_footnote]
                    except KeyError: # 引用了一个不存在的文件
                        print('WARN::', 'invalid href:', noteref_href, 
                              'at file:', path_noteref)
                        continue
                    else:
                        etree_footnote = item_footnote['data']
                    # 假设: 被引用注释是任意元素 x，它内部有一个<a>元素，它也引用了引用它的元素，
                    #   并且 x 是它父元素的首位孩子，则它的父元素可以作为 footnote 整体（递归）
                    # 需要被引用注释存在，如果不存在，则跳过
                    footnote = etree_footnote.find('.//*[@id="%s"]' % footnote_id)
                    if footnote is None:
                        continue
                    # 必须：footnote 也引用 noteref，否则跳过
                    for href in footnote.xpath('descendant-or-self::a/@href'):
                        if noteref_id == urldefrag(href)[1]:
                            break
                    else:
                        for href in footnote.xpath('../descendant-or-self::a/@href'):
                            if noteref_id == urldefrag(href)[1]:
                                footnote = footnote.getparent()
                                break
                        else:
                            continue
                    # 假设: footnote 是它父元素的首位孩子，并且它至少有一个兄弟元素节点与
                    #      它拥有不同的标签名，则它的父元素可以作为被引用的整体（递归）
                    while is_first_child(footnote):
                        if footnote.xpath('following-sibling::*[local-name(.) != "%s"]' % footnote.tag):
                            break
                        p_footnote = footnote.getparent()
                        # 无论怎么说，它的父元素不应该是如下的特殊标签
                        if p_footnote.tag in ('body', 'html', 'head'):
                            break
                        footnote = p_footnote
                    body.append(footnote)
                    # 或者更具体的：
                    # url = bc.id_to_href(item_footnote['id])
                    # noteref.attrib['href'] = url + '#' + footnote_id
                    noteref.attrib['href'] = '#' + footnote_id

        return 0

