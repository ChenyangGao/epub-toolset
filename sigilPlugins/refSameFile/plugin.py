__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 1)
__revision__ = 0

import posixpath

from contextlib import ExitStack
from copy import copy
from html import unescape
from urllib.parse import urldefrag, unquote

from util.relationship import is_first_child, is_first_only_descendant
from util.dialog import message_dialog
from util.edit import ctx_edit_html
from util.path import startswith_protocol
from util.iter_detailed_refer import get_reverse_refer


# TODO: 以后会支持移动任何元素，而不仅仅只能移动 脚注
# TODO: 运行插件后，会弹出一个 GUI 的对话框，你可以配置一些选项，可以更好地指导程序完成你的目标
# TODO: 把插件 reNumberNotes 的功能也整合进来，通过增加开始时的 GUI 界面选项实现
# TODO: 对脚注的识别，提供 人工写选择器 和 自动判断（现在的方式） 的选项，勾选 人工写选择器 的复选框，
#       GUI 界面会多出一个输入框，用于输入选择器
# TODO: 首先应该查找有 href 的 a 元素，它未必有 id 属性
# TODO: [x] 限定双向引用 [x] 移动包括在同一页 🔘 罗列引用关系(导出为csv)
# TODO: 增加一些断言 [] 脚注为 a 元素 [] 脚注的 id 和 href 在同一元素 [] 引用的 id 和 href 在同一元素
# TODO: 单选，到底是移动时复制还是移动后删除
# TODO: footnote 和 noteref 分别支持自行编写 xpath 或 css，不勾选复选框（默认），lineedit 是灰色
# TODO: 移动后还是保留原来但id（可能导致冲突），还是需要重新编号id（一些 默认策略 以及 自写函数）
# TODO: 移动策略 页面配置：
#       [ ] 包括在同一文件 
#       [ ] 包括不在同一文件
#       [ ] 是否也包括单向引用
#       [ ] 脚注移动到哪里（默认为引用所在页面的 body 元素末尾，但可自己写 css选择器 或 xpath，可以指定具体页面，或者写一个函数）
#       [ ] 是否要以及如何对被移动注释进行包装或者转换
#       [ ] 对注释进行断言的策略（一些 默认策略 或者 自写函数）
#       [ ] 对引用进行断言的策略（一些 默认策略 或者 自写函数）
# TODO: 支持 xlink，即能处理这类属性 xlink:href
# TODO：假设：在 脚注 和 引用 中，必须保证
#           ① 文件存在：锚点链接 href 锚向的文件也是存在的
#           ② id 存在：锚点链接 href 中所提供的 id 在对应文件中是存在的
#           ③ footnote 至少单向引用：引用 的 href 引用 脚注 的 id
#           ④ rearnote 相互引用：引用 的 href 引用 脚注 的 id，脚注 的 href 引用 引用 的 id


def _strip_space(s):
    return unescape(s).strip()


def _clean_space(s, _cre=__import__('re').compile('\s')):
    return _cre.sub('', unescape(s))




# def is_footnote


def is_noteref(noteref) -> bool:
    # 假设：因为在 引用 前面有对应的被注释的文本，所以在这个文本后面直接相邻的元素才是某个 引用 的整体
    parent_el = noteref.getparent()
    while (
        parent_el is not None 
        and len(parent_el) == 1 
        and not (parent_el.text and parent_el.text.strip())
    ):
        noteref, parent_el = parent_el, noteref.getparent()

    # 假设：引用前面应该有文本节点
    # TODO: 质疑：文本也可以直接包含在某个标签内，或许应该判断，父节点下面有不同元素类型存在
    prev_el = noteref.getprevious()
    if prev_el is not None:
        if not (prev_el.tail and prev_el.tail.strip()):
            return False
    else:
        if parent_el is None or not (parent_el.text and parent_el.text.strip()):
            return False

    # 我假设 引用 不应该是首位唯一孩子，应该是某一元素节点或文本节点的后兄弟节点的唯一后代
    if is_first_only_descendant(noteref):
        return False

    return True


def get_full_footnote_el(predicated_footnote_el):
    # 假设: footnote 是它父元素的首位孩子。如果它有兄弟文本节点包含除空白字符以外的其它字符
    #      ，或者它有兄弟元素节点拥有与它不同的标签名，则它的父元素可以作为被引用的整体（递归）
    footnote = predicated_footnote_el
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
            continue
        break
    return footnote


# TODO: 允许自行指定 xpath，cssselector 或者 python 函数来搜索元素
# TODO: 相互引用时，脚注的 href 和 id 不在同一个元素上，分几种情况来识别整体：
#       1. href 是 id 的后代，暂取 id
#       2. id 是 href 的后代，暂取 href
#       3. 否则，取 id 和 href 最近的公共上级，但如果这个公共上级也是其他 href-id 组公共上级，则通过实际情况进行分析到底要怎么取，我觉得最好还是根据在同一个文件中的那些注释所在，分析一下他们的构造，找出类似的结构（假设：脚注的结构都是近似的）
def run(bc):
    '''
    Rationale 理论

    我定义了两类待处理待元素节点 引用(noteref) 和 脚注(footnote) 
    - 引用：一个 a 元素，具有 href 属性，并且它是严格首位孩子。
    - 脚注：

    * 首位孩子：
        如果一个元素没有父元素，或者它的前面没有兄弟元素且如果前面有文本节点则只包含空白符号。
    * 严格首位孩子：
        如果一个元素有父元素，并且它还是首位孩子。
    * 唯一孩子：
        如果一个元素 el 没有父元素，或者父元素只有它一个孩子元素，且它没有兄弟文字
        节点或者兄弟文字节点中只有空白符号。唯一孩子必是首位孩子。
    * 严格唯一孩子：
        如果一个元素有父元素，并且它还是唯一孩子：。
    * 首位唯一后代：
        如果一个元素 el 没有父元素，或者可以找到它的一个祖先元素，这个
        祖先元素没有父元素，或者是其父元素的首位孩子且不是其父元素的唯一孩子，
        并且这个祖先元素的所有后代元素中从其子元素到 el 的都是唯一孩子。
    '''
    move_even_in_same_file = message_dialog('Message', '是否把所有脚注移动到末尾？')

    # TODO: 先把要移动的元素进行标记，然后批量进行移动，如果出现多对一的情况，需要进行提示
    # 问题：脚注 和 引用 应该存在相互的引用关系，两者是否需要有一一对应关系
    with ExitStack() as stack:
        path_item_map = {
            path: stack.enter_context(ctx_edit_html(bc, fid))
            for fid, path in bc.text_iter()
        }

        for book_href, etree_noteref in path_item_map.items():
            # 只搜索 body 元素以下的节点
            body = etree_noteref.body
            if body is None:
                continue

            pending_to_move = []
            for noteref in body.findall('.//*[@href]'):
                # NOTE: 观点：作为 引用 的部分，里面有且只能有 1 个 href，不然的话，它会锚向多个地方，这是不合适的
                # NOTE: 观点：引用 应该是比较简单的，它只不过是<a>元素锚向了脚注，只有单纯的文本，
                #             或者一个子元素为图形(<canvas>)或图像(<img>)元素
                # NOTE: 观点：在 引用 前，应该有一些文本，也就是说，它前面要么有文本，
                #             要么它不是它的父元素的第一个子元素
                # NOTE: 假设：如果某个 引用 的 id 和 href 可能分别位于不同的元素节点中，必须保证包含 id 的元素节点
                #             **不位于**包含 href 的元素节点之外或者之后，如果互为兄弟节点则这两者是紧邻的
                #            （中间没有穿插其它元素节点）

                if noteref.tag != 'a':
                    continue

                href = unquote(noteref.attrib['href'])
                # 如果 href 带有协议头，说明是 uri，非本地文件，要跳过
                if startswith_protocol(href):
                    continue

                footnote_link, footnote_id = urldefrag(href)
                if footnote_link == '':
                    footnote_link = book_href
                else:
                    footnote_link = relative_path(footnote_link, book_href, posixpath)

                # 如果没有这个文件，则跳过（并会打印一个文件缺失）
                if footnote_link not in path_item_map:
                    print('WARN::', ' unavailable href:', href, 
                          'in file:', book_href)
                    continue

                # 如果没有指向某个页面的一个 id 元素，则跳过
                if footnote_id == '':
                    continue

                # 如果 move_even_in_same_file 为真，则当 noteref 和 footnote 
                # 在同一个文件时也需要移动 footnote 到 body 元素末尾
                if not move_even_in_same_file and noteref_href == footnote_href: 
                    continue

                # 如果不是 noteref，则跳过
                if not is_noteref(noteref):
                    continue

                tree_where_footnote_is = path_item_map[footnote_link]
                footnote = tree_where_footnote_is.find('.//*[@id="%s"]' % footnote_id)

                # 如果相应文件中没有这个 id 对应的元素，则跳过
                if footnote is None:
                    print('WARN::', ' unavailable id:', footnote_id, 
                          'in file:', footnote_link)
                    continue

                # TODO: 收集所有的引用关系，然后分析共同的结构特征，相邻位置，共同上级，等，以便正确地获取 full_footnote
                # TODO: 有些是很规范的，按照 epub3 来组织，这个可以直接分析得到这种情况，直接做出正确决定

                # 假设: 注释是任意元素 x，它内部有一个<a>元素，它也引用了引用它的元素
                # TODO: 判断两者是否具有相互引用关系
                noteref_id, footnote_href = get_reverse_refer(noteref, book_href, footnote, footnote_link)

                print(noteref, noteref_id, footnote, footnote_id)

                #footnote = get_full_footnote_el(footnote)

                # 或者更具体的：
                # noteref.attrib['href'] = noteref_href + '#' + footnote_id
                #noteref.attrib['href'] = '#' + footnote_id

                #pending_to_move.append(footnote)

            #body.extend(pending_to_move)

        return 0



