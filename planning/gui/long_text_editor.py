from typing import Optional

from qtpy import QtCore as QC
from qtpy import QtGui as QG
from qtpy import QtWidgets as QW


class _CustomTextEditWidget(QW.QTextEdit):
    def __init__(self, parent: QW.QDialog):
        super().__init__(parent)
        self.parent_diag = parent

    def focusOutEvent(self, e: QG.QFocusEvent) -> None:
        super().focusOutEvent(e)
        self.parent_diag.accept()


class CustomTextEditor(QW.QDialog):
    # editingFinished = QC.Signal()

    def __init__(self, parent: Optional[QW.QWidget] = None):
        super().__init__(parent)
        self.text_edit = _CustomTextEditWidget(self)
        layout = QW.QVBoxLayout(self)
        layout.addWidget(self.text_edit)
        if parent is not None:
            self.move(parent.mapToGlobal(parent.rect().topLeft()))
        self.setWindowFlags(QC.Qt.WindowStaysOnTopHint | QC.Qt.FramelessWindowHint)

    def setText(self, text: str):
        self.text_edit.setText(text)

    def text(self) -> str:
        return self.text_edit.toPlainText()
