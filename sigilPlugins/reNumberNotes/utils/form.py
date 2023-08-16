#!/usr/bin/env python3
# coding: utf-8

import builtins

from lxml.etree import XPath
from lxml.cssselect import CSSSelector
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QDialog, QGridLayout, QLabel, 
    QLineEdit, QMessageBox, QRadioButton
)


__all__ = ['AskForm']


if not getattr(builtins, '_qtapp_initialized', False):
    __import__('atexit').register(
        QApplication(__import__('sys').argv).quit
    )
    builtins._qtapp_initialized = True


class AskForm(QDialog):

    def __init__(self):
        super().__init__()
        self.state = {}
        self.initUI()

    def initUI(self):
        self.setWindowTitle('搜索脚注标签')

        label_sel = QLabel('<strong>请选择一个<u>选择器类型</u></strong>')
        label_sel.setToolTip('只能选择其中一个<strong><u>选择器类型</u></strong>，<br/>'
                             '输入框中的文字会按相应<strong><u>选择器类型</u></strong>解释')

        rb_sel_css = self.rb_sel_css = QRadioButton('CSS选择器')
        rb_sel_css.setToolTip('<a href="https://developer.mozilla.org/zh-CN/docs/Web/CSS/CSS_Selectors">'
                              'MDN | CSS 选择器</a><br />查找 HTML 中的元素')

        rb_sel_xpath = self.rb_sel_xpath = QRadioButton('XPath')
        rb_sel_xpath.setToolTip('<a href="https://developer.mozilla.org/zh-CN/docs/Web/XPath">MDN'
                                ' | XPath</a><br />XML 路径语言')

        rb_sel_css.setChecked(True)

        label_expr = QLabel('<strong>输入<u>表达式</u>后按<u>回车</u>或<u>关闭</u>窗口</strong>')
        label_expr.setToolTip('<strong><u>空表达式</u></strong>和语法错误的'
                              '<strong><u>表达式</u></strong>不会被接受。'
                              '<br />输入<u>!</u>会被视为不作修改直接退出，'
                              '或者你直接按<u>ESC</u>键也可直接退出。<br />'
                              '<strong>⚠️注意：</strong>找到的元素未必就是最终用于插入编号文本的元素，'
                              '除非勾选 ☑️即此元素 ，否则最终用于插入编号文本的元素，是上述找到元素的自己、'
                              '上级、下级中的某个&lt;a&gt;元素。')

        le_expr = self.le_expr = QLineEdit()
        le_expr.setPlaceholderText('!')
        le_expr.setToolTip('请输入合法的 <strong><u>CSS选择器</u></strong> 或 '
                           '<strong><u>XPath</u></strong> 表达式')
        le_expr.returnPressed.connect(self.acceptOptions)

        label_numfmt = QLabel('<strong>编号格式</strong>')
        label_numfmt.setToolTip('编号的文本格式，基于 str.format 方法实现格式化。<br />'
                                '可用 {0} 或 {n} 指代编号，例如编号格式为 [{}] 或 [{n}] ，'
                                '那么实际的编号为 [1], [2], ...')

        le_numfmt = self.le_numfmt = QLineEdit()
        le_numfmt.setText('[{n}]')
        le_numfmt.setToolTip('请用占位符 <strong>{0}</strong> 或者 <strong>{n}</strong> 或者 <strong>{}</strong>(不推荐) 指代要插入的编号')
        le_numfmt.returnPressed.connect(self.acceptOptions)

        cb_just_this_el = self.cb_just_this_el = QCheckBox('即此元素')
        cb_just_this_el.setToolTip('勾选此项后，不会检查脚注和脚注引用的相互引用关系，<br/>'
                                   '而且直接修改找出元素（不再寻找临近的&lt;a&gt;元素）')

        cb_global_num = self.cb_global_num = QCheckBox('全局唯一')
        cb_global_num.setToolTip('勾选此项后，唯一编号不仅仅在(x)html文件中唯一，<br/>'
                                 '在整个epub文件中都是唯一的')

        cb_as_element = self.cb_as_element = QCheckBox('视为元素')
        cb_as_element.setToolTip('勾选此项后，会把编号的文本视为元素节点进行解析，否则视为文本节点。<br />'
                                 '视为元素节点时，会插入到目标元素的第一个子节点（如果有的话）')

        cb_clear_element = self.cb_clear_element = QCheckBox('清理元素')
        cb_clear_element.setToolTip('勾选此项后，会先把待插入编号文本的元素节点进行<strong>清理</strong>，'
                                    '删除它的所有的子节点，然后再把编号文本写入')

        grid = QGridLayout()
        grid.addWidget(label_sel, 0, 0, 1, 2)
        grid.addWidget(rb_sel_css, 1, 0)
        grid.addWidget(rb_sel_xpath, 1, 1)
        grid.addWidget(label_expr, 2, 0, 1, 2)
        grid.addWidget(le_expr, 3, 0, 1, 2)
        grid.addWidget(label_numfmt, 4, 0, 1, 2)
        grid.addWidget(le_numfmt, 5, 0, 1, 2)
        grid.addWidget(cb_just_this_el, 6, 0)
        grid.addWidget(cb_global_num, 6, 1)
        grid.addWidget(cb_as_element, 7, 0)
        grid.addWidget(cb_clear_element, 7, 1)

        self.setLayout(grid)
        self.show()

    def acceptOptions(self) -> bool:
        method = 'csssel' if self.rb_sel_css.isChecked() else 'xpath'
        expr = self.le_expr.text().strip()
        if not expr:
            QMessageBox.warning(
                self, "警告", '表达式不可为空，如果想要退出，要先输入!，再退出', QMessageBox.Cancel)
            self.le_expr.setFocus()
            return False
        elif expr == '!':
            self.state['select'] = '!'
            self.close()
            return True
        elif method == 'csssel':
            try:
                self.state['select'] = CSSSelector(expr)
            except Exception as exc:
                QMessageBox.warning(
                    self, "警告", f'错误的 CSS选择器 表达式，原因：\n{exc!r}', QMessageBox.Cancel)
                self.le_expr.setFocus()
                return False
        elif method == 'xpath':
            try:
                self.state['select'] = XPath(expr)
            except Exception as exc:
                QMessageBox.warning(
                    self, "警告", f'错误的 XPath 表达式，原因：\n{exc!r}', QMessageBox.Cancel)
                self.le_expr.setFocus()
                return False
        else:
            raise NotImplementedError('unsupported method %r' % expr)

        self.state['numfmt'] = self.le_numfmt.text()
        self.state['is_just_this_el'] = self.cb_just_this_el.isChecked()
        self.state['is_global_num'] = 'inepub' if self.cb_global_num.isChecked() else 'inhtml'
        self.state['is_as_elements'] = self.cb_as_element.isChecked()
        self.state['is_clear_element'] = self.cb_clear_element.isChecked()

        self.close()
        return True

    def closeEvent(self, event):
        if self.acceptOptions():
            event.accept()
        else:
            event.ignore()

    @classmethod
    def ask(cls):
        '弹出一个对话框，询问搜索脚注标签'
        form = AskForm()
        form.exec_()
        return form.state

