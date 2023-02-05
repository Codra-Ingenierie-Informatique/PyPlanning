# -*- coding: utf-8 -*-

"""
PyPlanning Qt utilities
"""

import functools
import os
import traceback

from guidata.widgets.codeeditor import CodeEditor
from qtpy import QtWidgets as QW

from planning.config import _


class ErrorMessageBox(QW.QDialog):
    """Error message box"""

    def __init__(self, parent, funcname=None):
        super().__init__(parent)
        title = parent.window().objectName()
        self.setWindowTitle(title)
        self.editor = CodeEditor(self)
        self.editor.setReadOnly(True)
        self.editor.setPlainText(traceback.format_exc())
        bbox = QW.QDialogButtonBox(QW.QDialogButtonBox.Ok)
        bbox.accepted.connect(self.accept)
        layout = QW.QVBoxLayout()
        text = ""
        if funcname is not None:
            text += os.linesep.join(
                [
                    f"{_('An error has occured')} ({_('function')} `{funcname}`).",
                    "",
                    "",
                ]
            )
        text += _("Error message:")
        layout.addWidget(QW.QLabel(text))
        layout.addWidget(self.editor)
        layout.addSpacing(10)
        layout.addWidget(bbox)
        self.setLayout(layout)
        self.resize(800, 350)


def qt_try_except():
    """Try...except Qt widget method decorator"""

    def qt_try_except_decorator(func):
        """Try...except Qt widget method decorator"""

        @functools.wraps(func)
        def method_wrapper(*args, **kwargs):
            """Decorator wrapper function"""
            self = args[0]  # extracting 'self' from method arguments
            #  If "self" is a BaseProcessor, then we need to get the panel instance
            output = None
            try:
                output = func(*args, **kwargs)
            except Exception:  # pylint: disable=broad-except
                traceback.print_exc()
                ErrorMessageBox(self, func.__name__).exec()
            finally:
                QW.QApplication.restoreOverrideCursor()
            return output

        return method_wrapper

    return qt_try_except_decorator
