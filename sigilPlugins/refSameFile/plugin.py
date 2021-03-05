__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 7)

from contextlib import ExitStack
from html import unescape
from os.path import basename
from urllib.parse import urldefrag, unquote

from utils.relationship import is_first_child, is_first_only_descendant
from utils.dialog import message_dialog
from utils.sigil_edit_file import ctx_edit_html


def _clean_space(s):
    return unescape(s).strip().replace('&nbsp;', '')


def run(bc):
    is_move_all = message_dialog('Message', '是否把所有脚注移动到末尾？')

    with ExitStack() as stack:
        path_item_map = {
            unquote(basename(path)):
                {'id': fid, 'data': stack.enter_context(ctx_edit_html(bc, fid))} 
            for fid, path in bc.text_iter()
        }

        for path_noteref, item_noteref in path_item_map.items():
            etree_noteref = item_noteref['data']

            # 只搜索 body 元素以下的节点
            body = etree_noteref.body
            if body is None:
                continue

            pending_to_move = []
            # 关键假设：脚注 和 脚注引用 应该存在相互的引用关系
            for noteref in body.xpath('.//*[@id]'):
                # 查找所有 脚注引用 的元素节点
                # 假设: 脚注引用 是一个有 id 属性元素，而且它不是它的祖先元素的 首位唯一后代
                # * 首位唯一后代：如果一个元素 el 没有父元素，或者可以找到它的一个祖先元素，这个
                #              祖先元素没有父元素，或者是其父元素的首位孩子且不是其父元素的唯一孩子，
                #              并且这个祖先元素的所有后代元素中从其子元素到 el 的都是唯一孩子。
                # * 首位孩子：如果一个元素 el 没有父元素，或者它的前面没有兄弟元素且
                #           如果前面有文本节点则只包含空白符号。
                # * 唯一孩子：如果一个元素 el 没有父元素，或者父元素只有它一个孩子元素，且它没有兄弟文字
                #           节点或者兄弟文字节点中只有空白符号。唯一孩子必是首位孩子。
                noteref_id = noteref.attrib['id']
                # 假设：某个脚注的 id 和 href 可能分别位于不同的元素节点中，必须保证包含 id 的元素节点
                #      **不位于**包含 href 的元素节点之外或者之后，如果互为兄弟节点则这两者是紧邻的
                #      （中间没有穿插其它元素节点）
                hrefs = noteref.xpath(
                    'descendant-or-self::*[local-name(.) = "a" and @href]/@href')
                if not hrefs:
                    noteref_next_sibling = noteref.getnext()
                    if noteref_next_sibling is None:
                        continue
                    hrefs = noteref_next_sibling.xpath(
                        'descendant-or-self::*[local-name(.) = "a" and @href]/@href')
                if hrefs:
                    noteref_href = hrefs[0]
                else:
                    continue

                # 我假设 脚注引用 不应该是首位唯一孩子，应该是某一元素节点或文本节点的后兄弟节点的唯一后代
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
                    for href in footnote.xpath(
                        'descendant-or-self::*[local-name(.) = "a" and @href]/@href'
                    ):
                        if noteref_id == urldefrag(href)[1]:
                            break
                    else:
                        for href in footnote.xpath(
                            '../descendant-or-self::*[local-name(.) = "a" and @href]/@href'
                        ):
                            if noteref_id == urldefrag(href)[1]:
                                footnote = footnote.getparent()
                                break
                        else:
                            continue
                    # 假设: footnote 是它父元素的首位孩子。如果它有兄弟文本节点包含除空白字符以外的其它字符
                    #      ，或者它有兄弟元素节点拥有与它不同的标签名，则它的父元素可以作为被引用的整体（递归）
                    while is_first_child(footnote):
                        p_footnote = footnote.getparent()
                        if p_footnote is None:
                            break
                        # 无论怎么说，它的父元素不应该是如下的特殊元素节点
                        if p_footnote.tag in ('body', 'head', 'html'):
                            break

                        following_text_nodes = footnote.xpath('following-sibling::text()')
                        if any(map(_clean_space, following_text_nodes)):
                            footnote = p_footnote
                            continue 
                        if (
                            len(p_footnote) == 1 or 
                            footnote.xpath('following-sibling::*[local-name(.) != "%s"]' %footnote.tag)
                        ):
                            footnote = p_footnote

                    # 或者更具体的：
                    # url = bc.id_to_href(item_footnote['id])
                    # noteref.attrib['href'] = url + '#' + footnote_id
                    noteref.attrib['href'] = '#' + footnote_id

                    pending_to_move.append(footnote)

            body.extend(pending_to_move)

        return 0

