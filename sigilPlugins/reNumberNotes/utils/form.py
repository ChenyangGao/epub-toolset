import atexit
import sys

from lxml.etree import XPath # type: ignore
from lxml.cssselect import CSSSelector # type: ignore
from PyQt5.QtWidgets import ( # type: ignore
    QApplication, QCheckBox, QDialog, QGridLayout, QLabel, 
    QLineEdit, QMessageBox, QRadioButton
)
from PyQt5.QtCore import QCoreApplication # type: ignore


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
        sel_label.setToolTip('只能选择其中一个选择器类型，<br/>'
                             '输入框中的文字会按相应选择器类型解释')
        grid.addWidget(sel_label, 0, 0, 1, 2)

        self.rb1 = QRadioButton('css选择器')
        self.rb2 = QRadioButton('xpath')
        self.rb1.setChecked(True)

        grid.addWidget(self.rb1, 1, 0)
        grid.addWidget(self.rb2, 1, 1)

        le_label = QLabel('<strong>输入表达式后按回车</strong>')
        le_label.setToolTip('空表达式和语法错误的表达式不会被接受')
        grid.addWidget(le_label, 2, 0, 1, 2)

        self.lineedit = QLineEdit()
        self.lineedit.returnPressed.connect(self.accept_expr)
        grid.addWidget(self.lineedit, 3, 0, 1, 2)

        cb1 = self.cb1 = QCheckBox('仅此元素')
        cb1.setToolTip('勾选此项后，不会检查脚注和脚注引用的相互引用关系，<br/>'
                       '而且直接修改找出元素的文字（不再寻找临近的&lt;a&gt;元素）')
        grid.addWidget(cb1, 4, 0)

        cb2 = self.cb2 = QCheckBox('全局唯一')
        cb2.setToolTip('勾选此项后，唯一编号不仅仅在(x)html文件中唯一，<br/>'
                       '在整个epub文件中都是唯一的')
        grid.addWidget(cb2, 4, 1)

        self.show()

    def accept_expr(self):
        self.state['only_modify_text'] = self.cb1.isChecked()
        self.state['unique_strategy'] = 'inepub' if self.cb2.isChecked() else 'inhtml'

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
    return form.state.copy()

