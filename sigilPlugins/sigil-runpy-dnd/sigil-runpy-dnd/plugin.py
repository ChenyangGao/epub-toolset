#!/usr/bin/env python3
# coding: utf-8

__author__  = "ChenyangGao <https://chenyanggao.github.io/>"

import sys

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QAbstractItemView, QApplication, QListWidget, QMainWindow


class DragDropList(QListWidget):
    task_data_Signal = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._dropLeaveItems = []

    def dragLeaveEvent(self, event):
        items = self.selectedItems()
        for i in items:
            self.takeItem(self.indexFromItem(i).row())
        self._dropLeaveItems.extend(items)

    def dragMoveEvent(self, event):
        super().dragMoveEvent(event)

    def dragEnterEvent(self, event):
        if event.source() is not self:
            self._dropLeaveItems.clear()
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event):
        pos = event.pos()
        current_item = self.itemAt(pos)
        current_index = self.indexFromItem(current_item)
        current_row = current_index.row()

        sourceWidget = event.source()
        if sourceWidget is None:
            for url in event.mimeData().urls():
                self.addItem(url.toLocalFile())
        else:
            items = sourceWidget.selectedItems()
            if sourceWidget is self and not items:
                for i in self._dropLeaveItems:
                    self.insertItem(current_row, i)
                self._dropLeaveItems.clear()
            else:
                for i in items:
                    sourceWidget.takeItem(sourceWidget.indexFromItem(i).row())
                    self.insertItem(current_row, i)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Backspace, Qt.Key_Delete):
            items = self.selectedItems()
            for i in items:
                self.takeItem(self.indexFromItem(i).row())
        elif event.modifiers() & Qt.ControlModifier and event.key() == Qt.Key_A:
            for i in range(self.count()):
                self.item(i).setSelected(True)


class MainWidget(QMainWindow):

    def __init__(self, config):
        super().__init__()
        self.setWindowTitle("Please add some Python scripts")
        ddlist = self.ddlist = DragDropList(self)
        ddlist.addItems(config["path"])
        self.setCentralWidget(ddlist)
        self.config = config

    def closeEvent(self, event):
        ddlist = self.ddlist
        self.config["path"] = [ddlist.item(i).text() for i in range(ddlist.count())]
        event.accept()


def run(bc):
    prefs = bc.getPrefs()
    if "config" not in prefs:
        prefs["config"] = {"path": []}
    app = QApplication(sys.argv)
    m = MainWidget(prefs["config"])
    m.show()
    retcode = app.exec_()
    if retcode == 0:
        bc.savePrefs(prefs)
    return retcode

# TODO: 支持选项：在终端执行
# TODO: 支持按钮，点击运行
# TODO: 支持界面，命令输出
