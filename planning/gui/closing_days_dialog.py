import datetime as dt
from copy import copy

# Qt imports
from qtpy import QtCore as QC
from qtpy import QtGui as QG
from qtpy import QtWidgets as QW

# Local imports
from planning.config import _
from planning.model import ClosingDayData, PlanningData


# pylint: ignore=invalid-name
class ClosingDaysModel(QC.QAbstractItemModel):
    """Model for interfacing closing days with TableView"""

    def __init__(
        self,
        planning,
        closing_days=[],
        parent=None,
    ):
        super().__init__(parent)
        self.planning: PlanningData = planning
        self.closing_days: list[ClosingDayData] = copy(closing_days)
        self.__changes = False
        self.sanitize_model()

    @property
    def changes(self):
        """Return if there was changes made in the model"""
        return self.__changes

    def parent(self, index=None):
        """Return parent index (no item hierarchy in our case)"""
        return QC.QModelIndex()

    def index(self, row, column, parent=None):
        """Return index for given row and column"""
        if not self.hasIndex(row, column, parent):
            return QC.QModelIndex()
        return self.createIndex(row, column)

    def rowCount(self, parent=QC.QModelIndex()):
        """Return closing periods count"""
        return len(self.closing_days)

    def columnCount(self, parent=QC.QModelIndex()):
        """Return column count"""
        return 2

    def insertRow(self, row, parent=QC.QModelIndex()):
        """Insert new closing day"""
        self.__changes = True

        cd = ClosingDayData(self.planning, _("Closing"))

        cd.start.value = QC.QDate.currentDate().toPyDate()
        cd.stop.value = None

        self.beginInsertRows(parent, row, row)
        self.closing_days.insert(row, cd)
        self.endInsertRows()

        index = self.createIndex(row, 0)
        self.dataChanged.emit(index, index)

    def removeRow(self, row, parent=QC.QModelIndex()):
        """Remove closing day"""
        self.__changes = True

        self.beginRemoveRows(parent, row, row)
        self.closing_days.pop(row)
        self.endRemoveRows()

        index = self.createIndex(row, 0)
        self.dataChanged.emit(index, index)

    def data(self, index, role=QC.Qt.EditRole):
        """Get closing day data from the model (cast from datetime.date)"""

        if not index.isValid():
            return QC.QVariant()

        closing_day = self.closing_days[index.row()]

        match index.column():

            case 0:  # start
                return closing_day.start.value.strftime("%d/%m/%y")

            case 1:  # stop
                return (
                    None
                    if closing_day.stop.value is None
                    else closing_day.stop.value.strftime("%d/%m/%y")
                )

        return QC.QVariant()

    def setData(self, index, value, role=QC.Qt.EditRole):
        """Set closing day data in the model (cast to datetime.date)"""

        if not index.isValid():
            return False

        closing_day = self.closing_days[index.row()]
        valid = False

        match index.column():

            case 0:  # start

                if not value:
                    closing_day.start.value = dt.datetime.today().date()
                    return True
                elif value == closing_day.stop.value:
                    closing_day.start.value = value
                    closing_day.stop.value = None
                    return True
                else:
                    valid = True

                if valid:
                    closing_day.start.value = value

            case 1:  # end

                if (
                    not value
                    or closing_day.start.value is None
                    or value == closing_day.start.value
                    or closing_day.start.value > value
                ):
                    closing_day.stop.value = None
                else:
                    valid = True

                if valid:
                    closing_day.stop.value = value

        self.dataChanged.emit(index, index)
        return valid

    def flags(self, index=QC.QModelIndex()):
        """Return flags: in our case, the view is always editable and selectable"""
        return QC.Qt.ItemIsEditable | QC.Qt.ItemIsEnabled | QC.Qt.ItemIsSelectable

    def headerData(self, section, orientation, role=QC.Qt.DisplayRole):
        """Return headers for the TableView"""
        if role == QC.Qt.DisplayRole:
            match orientation:
                case QC.Qt.Horizontal:
                    match section:
                        case 0:
                            return _("Period start / Single day")
                        case 1:
                            return _("Period end")
                case QC.Qt.Vertical:
                    return str(section)
        return None

    def sanitize_model(self):
        self.closing_days.sort(key=lambda cd: cd.start.value)
        # For the moment, we're permissive with the edition...
        # indexes_to_remove = []

        # for cd_index in range(len(self.closing_days) - 1):

        #     cd_last = self.closing_days[cd_index - 1] if cd_index > 0 else None
        #     cd = self.closing_days[cd_index]
        #     Removing strict duplicates (not legitimate possible overlapping periods)
        #     if (
        #         cd_last
        #         and cd_last.start.value == cd.start.value
        #         and cd_last.stop.value == cd.stop.value
        #     ):
        #         indexes_to_remove.append(cd_index)
        #         continue

        #     if cd.start.value is None:
        #         indexes_to_remove.append(cd_index)
        #         continue

        #     if cd.stop.value is not None:
        #         if cd.stop.value < cd.start.value:
        #             cd.stop.value = None

        # indexes_to_remove.sort(reverse=True)
        # for index in indexes_to_remove:
        #     self.closing_days.pop(index)


class ClosingDaysDelegate(QW.QItemDelegate):
    """Delegate for editing closing days"""

    def __init__(
        self,
        parent=None,
    ):
        QW.QItemDelegate.__init__(self, parent)

    def createEditor(self, parent, option, index):
        editor = QW.QDateEdit(parent)
        editor.setDisplayFormat("dd/MM/yy")
        return editor

    def setEditorData(self, editor, index):
        value = index.model().data(index, QC.Qt.EditRole)  # str
        try:
            editor.setDate(dt.datetime.strptime(value, "%d/%m/%y"))
        except Exception:
            editor.setDate(QC.QDate())

    def setModelData(self, editor, model, index):
        value = editor.date() or QC.QDate.currentDate()
        model.setData(index, value.toPython(), QC.Qt.EditRole)


class ClosingDaysDialog(QW.QDialog):
    """
    A little dialog allowing user to edit global closing days
    """

    def __init__(self, parent=None, debug=False):
        super().__init__(parent)

        self.debug: bool = debug
        self.planning: PlanningData = None

        self.setWindowTitle(_("Edit global closing days"))
        self.setModal(True)
        self.resize(500, 500)

    # Button handlers

    def __add_item(self):
        self.model.insertRow(self.model.rowCount())
        self.tbl_view.scrollToBottom()

    def __remove_item(self):
        selected_rows = [
            index.row() for index in self.tbl_view.selectionModel().selectedIndexes()
        ]
        selected_rows.sort(reverse=True)
        for row in selected_rows:
            self.model.removeRow(row)

    # Dialog closing handlers

    def __accept(self):
        """Accept edition and close dialog"""
        if not self.model.changes:
            self.reject()
            return
        self.planning.clolist = self.model.closing_days
        self.accept()

    def __reject(self):
        """Reject edition and close dialog"""
        self.model.closing_days = copy(self.planning.clolist)
        self.reject()

    def closeEvent(self, event):
        """Close handler"""
        self.__reject()
        event.accept()

    # Integrated TableView handlers

    def __tableview_selection_changed(self):
        """Selection change handler"""
        self.btn_remove.setEnabled(self.tbl_view.selectionModel().hasSelection())

    # Init methods

    # pylint: disable=attribute-defined-outside-init
    def __init(self, planning: PlanningData):
        """Populate planning data and prepare dialog UI"""
        if not planning:
            return

        self.planning = planning
        self.model = ClosingDaysModel(self.planning, self.planning.clolist)
        self.__define_ui()

    # pylint: disable=attribute-defined-outside-init
    def __define_ui(self):
        """ """
        self.layout = QW.QVBoxLayout(self)

        self.intro = QW.QLabel()
        self.intro.setText(
            _(
                "To edit existing closing day, double-click on the date (or the empty box).\nTo remove an end date, set it to any date equal/prior to start.\nThe closing period is considered as a single day if the second column is empty."
            )
        )
        self.layout.addWidget(self.intro)

        self.tbl_view = QW.QTableView()
        self.tbl_view.setModel(self.model)
        self.tbl_view.setItemDelegate(ClosingDaysDelegate())

        self.tbl_view.horizontalHeader().setSectionResizeMode(QW.QHeaderView.Stretch)
        self.tbl_view.horizontalHeader().setSectionsMovable(False)
        self.tbl_view.horizontalHeader().setSectionsClickable(False)
        self.tbl_view.horizontalHeader().setStretchLastSection(True)

        self.tbl_view.selectionModel().selectionChanged.connect(
            self.__tableview_selection_changed
        )

        self.layout.addWidget(self.tbl_view)

        btn_layout = QW.QHBoxLayout()
        self.btn_add = QW.QPushButton(_("Add period/day"))
        self.btn_remove = QW.QPushButton(_("Remove selected period/day"))
        self.btn_remove.setEnabled(False)
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_remove)
        self.layout.addLayout(btn_layout)

        self.btn_box = QW.QDialogButtonBox(
            QW.QDialogButtonBox.Ok | QW.QDialogButtonBox.Cancel
        )
        self.layout.addWidget(self.btn_box)

        self.btn_add.clicked.connect(self.__add_item)
        self.btn_remove.clicked.connect(self.__remove_item)
        self.btn_box.accepted.connect(self.__accept)
        self.btn_box.rejected.connect(self.__reject)

    def exec_(self, planning: PlanningData):
        """Show dialog and return its result (accepted/rejected)"""
        self.__init(planning)
        self.model.layoutChanged.emit()
        return super().exec_()
