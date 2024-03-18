from typing import Generic, Iterable, Optional, TypeVar

from qtpy.QtCore import QEvent, QObject, Qt, QTimerEvent
from qtpy.QtGui import QFontMetrics, QStandardItem
from qtpy.QtWidgets import QComboBox, QStyledItemDelegate

T = TypeVar("T")


class _CheckableComboDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        size.setHeight(20)
        return size


class CheckableComboBox(QComboBox, Generic[T]):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Make the combo editable to set a custom text, but readonly
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)

        # Use custom delegate
        self.setItemDelegate(_CheckableComboDelegate())

        # Update the text when an item is toggled
        self.model().dataChanged.connect(self.updateText)

        # Hide and show popup when clicking the line edit
        self.lineEdit().installEventFilter(self)
        self.closeOnLineEditClick = False

        self.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        # Prevent popup from closing when clicking on an item
        self.view().viewport().installEventFilter(self)

    def resizeEvent(self, e: QEvent):
        # Recompute text to elide as needed
        self.updateText()
        super().resizeEvent(e)

    def eventFilter(self, obj: QObject, event: QEvent):

        if obj == self.lineEdit():
            if event.type() == QEvent.Type.MouseButtonRelease:
                if self.closeOnLineEditClick:
                    self.hidePopup()
                else:
                    self.showPopup()
                return True
            return False

        if (
            obj == self.view().viewport()
            and event.type() == QEvent.Type.MouseButtonRelease
        ):
            index = self.view().indexAt(event.pos())
            item = self.model().item(index.row())

            if item.checkState() == Qt.CheckState.Checked:
                item.setCheckState(Qt.CheckState.Unchecked)
            else:
                item.setCheckState(Qt.CheckState.Checked)
            return True
        return False

    def showPopup(self):
        super().showPopup()
        # When the popup is displayed, a click on the lineedit should close it
        self.closeOnLineEditClick = True

    def hidePopup(self):
        super().hidePopup()
        # Used to prevent immediate reopening when clicking on the lineEdit
        self.startTimer(100)
        # Refresh the display text when closing
        self.updateText()

    def timerEvent(self, event: QTimerEvent):
        # After timeout, kill timer, and reenable click on line edit
        self.killTimer(event.timerId())
        self.closeOnLineEditClick = False

    def updateText(self):
        texts = []
        for i in range(self.model().rowCount()):
            if self.model().item(i).checkState() == Qt.Checked:
                texts.append(self.model().item(i).text())
        text = ", ".join(texts)

        # Compute elided text (with "...")
        metrics = QFontMetrics(self.lineEdit().font())
        elidedText = metrics.elidedText(text, Qt.ElideRight, self.lineEdit().width())
        self.lineEdit().setText(elidedText)

    def addItem(self, text, data: Optional[T] = None):
        item = QStandardItem()
        item.setText(text)
        if data is None:
            item.setData(text)
        else:
            item.setData(data)
        item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
        item.setData(Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)
        self.model().appendRow(item)

    def addItems(self, texts, datalist: Optional[Iterable[T]] = None):
        datalist_ = datalist if datalist is not None else [None] * len(texts)
        for text, data in zip(texts, datalist_):
            self.addItem(text, data)

    def currentData(self, _=None) -> list[T]:
        # Return the list of selected items data
        res = []
        for i in range(self.model().rowCount()):
            if self.model().item(i).checkState() == Qt.CheckState.Checked:
                res.append(self.model().item(i).data())
        return res

    def selectItems(self, datalist: Optional[Iterable[T]]):
        """Select items in the combobox based on their data."""
        if not datalist:
            return
        dataset = set(datalist)
        last_selected_idx = 0
        for i in range(self.model().rowCount()):
            if self.model().item(i).data() in dataset:
                self.model().item(i).setCheckState(Qt.CheckState.Checked)
                last_selected_idx = i

        if self.model().rowCount() > 0:
            self.setCurrentIndex(last_selected_idx)
