import atexit
import sys

from lxml.etree import XPath
from lxml.cssselect import CSSSelector
from PyQt5.QtWidgets import (
    QApplication, QDialog, QGridLayout, QLabel, QLineEdit, 
    QMessageBox, QRadioButton
)
from PyQt5.QtCore import QCoreApplication


__all__ = ['ask_form']


app = QApplication(sys.argv)
atexit.register(app.quit)


class Form(QDialog):

    def __init__(self):
        super().__init__()
        self.state = {}

        self.setWindowTitle('搜索脚注标签')

        grid = QGridLayout()
        self.setLayout(grid)

        sel_label = QLabel('<strong>请选择一个选择器</strong>')
        grid.addWidget(sel_label, 0, 0, 1, 2)

        self.rb1 = QRadioButton('css选择器')
        self.rb2 = QRadioButton('xpath')
        self.rb1.setChecked(True)

        grid.addWidget(self.rb1, 1, 0)
        grid.addWidget(self.rb2, 1, 1)

        le_label = QLabel('<strong>输入表达式后按回车</strong>')
        grid.addWidget(le_label, 2, 0, 1, 2)

        self.lineedit = QLineEdit()
        self.lineedit.returnPressed.connect(self.accept_expr)
        grid.addWidget(self.lineedit, 3, 0, 1, 2)

        self.show()

    def accept_expr(self):
        method = 'csssel' if self.rb1.isChecked() else 'xpath'
        expr = self.lineedit.text()
        if not expr.strip():
            QMessageBox.warning(self, "警告", '表达式不可为空', QMessageBox.Cancel)
        elif method == 'csssel':
            try:
                CSSSelector(expr)
            except:
                QMessageBox.warning(self, "警告", '错误的 CSS选择器 表达式', QMessageBox.Cancel)
            else:
                self.state.update(method=method, expr=expr)
                self.close()
        elif method == 'xpath':
            try:
                XPath(expr)
            except:
                QMessageBox.warning(self, "警告", '错误的 XPath 表达式', QMessageBox.Cancel)
            else:
                self.state.update(method=method, expr=expr)
                self.close()
        else:
            raise NotImplementedError


def ask_form():
    '弹出一个对话框，询问搜索脚注标签'
    form = Form()
    form.exec_()
    return form.state

