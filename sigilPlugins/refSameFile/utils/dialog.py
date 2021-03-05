__author__  = 'ChenyangGao <https://chenyanggao.github.io/>'
__version__ = (0, 0, 1)


__all__ = ['message_dialog']


try:
    from PyQt5.QtWidgets import QApplication, QMessageBox # type: ignore

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

import atexit

atexit.register(app.quit)

