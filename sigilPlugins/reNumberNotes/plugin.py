#!/usr/bin/env python3
# coding: utf-8

__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 5)

import posixpath

from itertools import chain
from urllib.parse import urlsplit
from lxml.html import fromstring

from utils.form import AskForm
from utils.edithtml import DoNotWriteBack, ctx_edit_html


def replace_el_inner(el, text, config):
    '修改脚注的标签'
    is_as_elements = config['is_as_elements']
    is_clear_element = config['is_clear_element']
    if is_clear_element:
        el.clear(keep_tail=True)
    if is_as_elements:
        div = fromstring('<div>%s</div>' % text)
        if div.text:
            el.text = div.text
        for i, cel in enumerate(div.getchildren()):
            el.insert(i, cel)
    else:
        el.text = text


def iter_href_ids(el, basename, use_descendants=True, use_ancestors=False):
    '''帮助函数，用于获取这个元素的上下文（自己，前驱，后继）中 a 元素的 href 
    属性锚向的在同一文件中的 id'''
    els = (el,)
    if use_descendants:
        els = chain(els, el.xpath('descendant::a[@href]'))
    if use_ancestors:
        els = chain(els, el.iterancestors('a'))
    for el in els:
        href = el.attrib.get('href')
        if not href:
            continue
        href_split = urlsplit(href)
        if (
            href_split.scheme == ''
            and href_split.fragment
            and (
                href_split.path == '' or 
                posixpath.basename(href_split.path) == basename
            )
        ):
            yield href_split.fragment


def renumber_notes(href, tree, config, start=1):
    '批量对脚注标签进行编号'
    body = tree.body
    refs = config['select'](body)

    if not refs:
        raise DoNotWriteBack

    numfmt = config['numfmt']
    is_just_this_el = config['is_just_this_el']
    basename = posixpath.basename(href)

    n = start
    for ref in refs:
        num_str = numfmt.format(n, n=n)
        if is_just_this_el: # NOTE: 不会检查是否相互引用
            replace_el_inner(ref, num_str, config)
        else:
            top = ref

            ids = {el.attrib['id'] for el in top.xpath('descendant-or-self::*[@id]')}
            if not ids:
                continue

            href_to_ids = [*iter_href_ids(top, basename)]

            if not href_to_ids:
                continue

            for refby_id in href_to_ids:
                refby = body.find('.//*[@id="%s"]' %refby_id)
                if (
                    refby is not None and 
                    any(el in ids for el in iter_href_ids(refby, basename, True, True))
                ):
                    replace_el_inner(refby, num_str, config)
                    break
            else:
                continue

        n += 1

    return n


def run(bc):
    config = AskForm.ask()
    if not config or config['select'] == '!':
        print('已取消')
        return 0
    is_global_num = config.pop('is_global_num', False)
    n = 1
    for fid, href in bc.text_iter():
        with ctx_edit_html(bc, fid) as tree:
            m = renumber_notes(href, tree, config, start=n)
            if m == n:
                raise DoNotWriteBack
            print('改动文件：', href)
            if is_global_num:
                n = m
    return 0

