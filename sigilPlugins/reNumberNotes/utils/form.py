from lxml.etree import XPath
from lxml.cssselect import CSSSelector
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QDialog, QGridLayout, QLabel, 
    QLineEdit, QMessageBox, QRadioButton
)


__all__ = ['AskForm']


if not getattr(__builtins__, '_qtapp_initialized', False):
    __import__('atexit').register(
        QApplication(__import__('sys').argv).quit
    )


class AskForm(QDialog):

    def __init__(self):
        super().__init__()
        self.state = {}
        self._init()
        self.show()

    def _init(self):
        self.setWindowTitle('搜索脚注标签')
    
        grid = QGridLayout()
        self.setLayout(grid)

        sel_label = QLabel('<strong>请选择一个<u>选择器类型</u></strong>')
        sel_label.setToolTip('只能选择其中一个<strong><u>选择器类型</u></strong>，<br/>'
                             '输入框中的文字会按相应<strong><u>选择器类型</u></strong>解释')
        grid.addWidget(sel_label, 0, 0, 1, 2)

        rb1 = self.rb1 = QRadioButton('CSS选择器')
        rb1.setToolTip('<a href="https://developer.mozilla.org/zh-CN/docs/Web/CSS/CSS_Selectors">MDN | CSS 选择器</a><br />查找 HTML 中的元素')
        rb2 = self.rb2 = QRadioButton('XPath')
        rb2.setToolTip('<a href="https://developer.mozilla.org/zh-CN/docs/Web/XPath">MDN | XPath</a><br />XML 路径语言')
        rb1.setChecked(True)

        grid.addWidget(rb1, 1, 0)
        grid.addWidget(rb2, 1, 1)

        le_label = QLabel('<strong>输入<u>表达式</u>后按回车</strong>')
        le_label.setToolTip('<strong><u>空表达式</u></strong>和语法错误的'
                            '<strong><u>表达式</u></strong>不会被接受')
        grid.addWidget(le_label, 2, 0, 1, 2)

        le_expr = self.le_expr = QLineEdit()
        le_expr.setToolTip('请输入合法的 <strong><u>CSS选择器</u></strong> 或 <strong><u>XPath</u></strong> 表达式')
        le_expr.returnPressed.connect(self.accept_expr)
        grid.addWidget(le_expr, 3, 0, 1, 2)

        le_label = QLabel('<strong>编号格式</strong>')
        le_label.setToolTip('编号的文本格式，比如编号格式为 [%d] ，那么实际的编号为 [1], [2], ...')
        grid.addWidget(le_label, 4, 0, 1, 2)

        le_numfmt = self.le_numfmt = QLineEdit()
        le_numfmt.setText('[%d]')
        le_numfmt.setToolTip('请用占位符 <strong>%d</strong> 或者 <strong>%s</strong> 指代要插入的编号')
        le_numfmt.returnPressed.connect(self.accept_expr)
        grid.addWidget(le_numfmt, 5, 0, 1, 2)

        cb1 = self.cb1 = QCheckBox('仅此元素')
        cb1.setToolTip('勾选此项后，不会检查脚注和脚注引用的相互引用关系，<br/>'
                       '而且直接修改找出元素的文字（不再寻找临近的&lt;a&gt;元素）')
        grid.addWidget(cb1, 6, 0)

        cb2 = self.cb2 = QCheckBox('全局唯一')
        cb2.setToolTip('勾选此项后，唯一编号不仅仅在(x)html文件中唯一，<br/>'
                       '在整个epub文件中都是唯一的')
        grid.addWidget(cb2, 6, 1)

    def accept_expr(self):
        method = 'csssel' if self.rb1.isChecked() else 'xpath'
        expr = self.le_expr.text().strip()
        if not expr:
            QMessageBox.warning(
                self, "警告", '表达式不可为空', QMessageBox.Cancel)
            self.le_expr.setFocus()
        elif method == 'csssel':
            try:
                self.state['select'] = CSSSelector(expr)
                self.close()
            except:
                QMessageBox.warning(
                    self, "警告", '错误的 CSS选择器 表达式', QMessageBox.Cancel)
                self.le_expr.setFocus()
        elif method == 'xpath':
            try:
                self.state['select'] = XPath(expr)
                self.close()
            except:
                QMessageBox.warning(
                    self, "警告", '错误的 XPath 表达式', QMessageBox.Cancel)
                self.le_expr.setFocus()
        else:
            raise NotImplementedError('unsupported method %r' % expr)

        self.state['numfmt'] = self.le_numfmt.text()

        self.state['only_modify_text'] = self.cb1.isChecked()
        self.state['unique_strategy'] = 'inepub' if self.cb2.isChecked() else 'inhtml'

    @classmethod
    def ask(cls):
        '弹出一个对话框，询问搜索脚注标签'
        form = AskForm()
        form.exec_()
        return form.state

