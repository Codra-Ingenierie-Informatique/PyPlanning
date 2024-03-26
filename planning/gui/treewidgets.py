# -*- coding: utf-8 -*-
"""PyPlanning task tree widget"""

# pylint: disable=no-name-in-module
# pylint: disable=no-member


import datetime
import os
import re
import xml.etree.ElementTree as ET
from typing import Any, Callable, Generic, Optional, TypeVar, Union

from guidata import qthelpers
from guidata.configtools import get_icon
from guidata.qthelpers import add_actions, create_action, keybinding
from qtpy import QtCore as QC
from qtpy import QtGui as QG
from qtpy import QtWidgets as QW

from planning.config import MAIN_FONT_FAMILY, Conf, _
from planning.gui.long_text_editor import CustomTextEditor
from planning.gui.multi_selection_combobox import CheckableComboBox
from planning.model import (
    AbstractData,
    AbstractDataT,
    AbstractTaskData,
    AnyData,
    ChartData,
    DataItem,
    DTypes,
    LeaveData,
    MilestoneData,
    PlanningData,
    ProjectData,
    ResourceData,
    TaskData,
    TaskModes,
)

ItemEditor = Union[
    QW.QComboBox,
    QW.QCheckBox,
    QW.QSpinBox,
    QW.QDateEdit,
    QW.QLineEdit,
    CustomTextEditor,
    CheckableComboBox,
]

ItemEditorT = TypeVar(
    "ItemEditorT",
    bound=ItemEditor,
)

IS_DARK = qthelpers.is_dark_mode()


EMPTY_NAME = _("Untitled")


class TaskTreeDelegate(QW.QItemDelegate):
    """Task Tree Item Delegate"""

    def __init__(
        self,
        parent: "BaseTreeWidget",
        margin: int,
        parent_signals: dict[str, QC.Signal],
    ):
        QW.QItemDelegate.__init__(self, parent)
        self.margin = margin
        self.editor_opened = False
        self.parent_signals = parent_signals

    def sizeHint(self, option, index):  # pylint: disable=invalid-name
        """Reimplement Qt method"""
        size = super().sizeHint(option, index)
        font_height = QG.QFontMetrics(self.parent().font()).height()
        size.setHeight(font_height + self.margin)
        return size

    @staticmethod
    def item_from_index(index: QC.QModelIndex) -> QC.QModelIndex:
        """Return standard model item from index"""
        return index.model().itemFromIndex(index)

    def dataitem_from_index(self, index: QC.QModelIndex) -> DataItem:
        """Return data item for index"""
        return self.parent().item_data[id(self.item_from_index(index))]

    # pylint: disable=unused-argument,invalid-name
    def createEditor(
        self, parent: QW.QWidget, option: QW.QStyleOptionViewItem, index: QC.QModelIndex
    ) -> ItemEditor:
        """Reimplement Qt method"""
        self.editor_opened = True
        ditem = self.dataitem_from_index(index)
        if ditem.datatype == DTypes.DAYS:
            editor = QW.QSpinBox(parent)
            editor.setMaximum(1000)
            editor.editingFinished.connect(self.commitAndCloseEditor)
            return editor
        elif ditem.datatype == DTypes.DATE:
            editor = QW.QDateEdit(parent)
            dispfmt = editor.displayFormat()
            if dispfmt.endswith("yyyy"):
                editor.setDisplayFormat(dispfmt[:-2])
            editor.editingFinished.connect(self.commitAndCloseEditor)
            return editor
        elif ditem.datatype == DTypes.CHOICE:
            editor = QW.QComboBox(parent)
            choices = ditem.choice_values
            if len(choices) >= 0:
                editor.addItems(choices)
            editor.activated.connect(lambda index: self.commitAndCloseEditor())
            return editor
        elif ditem.datatype == DTypes.BOOLEAN:
            editor = QW.QCheckBox(parent)
            editor.setStyleSheet("QCheckBox {margin-left: 20px; }")
            editor.toggled.connect(lambda state: self.commitAndCloseEditor())
            return editor
        elif ditem.datatype == DTypes.COLOR:
            editor = QW.QComboBox(parent)
            editor.addItems(DataItem.COLORS.keys())
            editor.activated.connect(lambda index: self.commitAndCloseEditor())
            return editor
        elif ditem.datatype == DTypes.MULTIPLE_CHOICE:
            editor = CheckableComboBox(parent=parent)
            editor.addItems(ditem.choice_values, ditem.choice_keys)
            editor.setMinimumWidth(self.parent().columnWidth(index.column()))
            editor.lineEdit().editingFinished.connect(
                lambda: self.commitAndCloseEditor()
            )
            return editor
        elif ditem.datatype == DTypes.LONG_TEXT:
            editor = CustomTextEditor(parent)
            editor.setText(ditem.value or "")
            editor.setMinimumSize(self.parent().columnWidth(index.column()), 150)
            editor.setFocus()
            editor.finished.connect(self.commitAndCloseEditor)
            return editor

        editor = QW.QLineEdit(parent)
        editor.editingFinished.connect(self.commitAndCloseEditor)
        return editor

    def commitAndCloseEditor(self):  # pylint: disable=invalid-name
        """Reimplement Qt method"""
        self.editor_opened = False
        editor = self.sender()
        self.commitData.emit(editor)
        self.closeEditor.emit(editor)

    def setEditorData(
        self, editor: ItemEditor, index: QC.QModelIndex
    ):  # pylint: disable=invalid-name
        """Reimplement Qt method"""
        ditem = self.dataitem_from_index(index)
        value = ditem.to_widget_value()
        if ditem.datatype == DTypes.DAYS:
            editor.setValue(value)
        elif ditem.datatype == DTypes.DATE:
            editor.setDate(value)
        elif ditem.datatype == DTypes.CHOICE:
            editor.setCurrentText(ditem.get_choice_value() or "")
        elif ditem.datatype == DTypes.BOOLEAN:
            editor.setChecked(value)
        elif ditem.datatype == DTypes.COLOR:
            editor.setCurrentText(value)
        elif ditem.datatype == DTypes.MULTIPLE_CHOICE:
            editor.selectItems(ditem.value)
        else:
            editor.setText(value)

    # pylint: disable=unused-argument,invalid-name
    def setModelData(self, editor: ItemEditor, mdl, index: QC.QModelIndex):
        """Reimplement Qt method"""
        ditem = self.dataitem_from_index(index)
        validator = self.parent().VALIDATORS.get(ditem.name)
        sig = self.parent_signals.get(ditem.name)

        value: Any
        if ditem.datatype == DTypes.DAYS:
            value = editor.value() or None
        elif ditem.datatype == DTypes.DATE:
            qdate = editor.date()
            value = datetime.date(qdate.year(), qdate.month(), qdate.day())
            data = ditem.parent
            if (
                ditem.name == "start"
                and data.start.value is not None
                and data.stop.value is not None
            ):
                data.stop.value += value - data.start.value
        elif ditem.datatype == DTypes.CHOICE or ditem.datatype == DTypes.COLOR:
            value = editor.currentText()
        elif ditem.datatype == DTypes.BOOLEAN:
            value = editor.isChecked()
        elif ditem.datatype == DTypes.INTEGER:
            txt = editor.text()
            value = None if txt == "" else int(editor.text())
        elif ditem.datatype == DTypes.LIST:
            value = editor.text().split(",")
            value = [v for val in value if (v := val.strip())]
        elif ditem.datatype == DTypes.MULTIPLE_CHOICE:
            value = editor.currentData()
        else:
            value = editor.text()
            if ditem.name == "name" and len(value) == 0:
                value = EMPTY_NAME
            elif value == "":
                value = None
        if validator is not None and not validator(value):
            return

        if ditem.datatype == DTypes.CHOICE:
            ditem.set_choice_value(value)
        else:
            ditem.value = value

        if sig is not None:
            sig.emit(ditem)

        item = self.item_from_index(index)
        item.setText(ditem.to_display())
        self.parent().refresh()


class BaseTreeWidget(QW.QTreeView):
    """Base tree widget for tasks and other things"""

    TITLE = None
    SIG_MODEL_CHANGED = QC.Signal()
    COLUMNS_TO_RESIZE = [0]
    COLUMN_WIDTH_MARGIN = 20
    COLUMNS_TO_EDIT_ON_CLICK = ()
    ATTRS: tuple[str | tuple[str, ...], ...] = ()

    # Validators are used to check if the value from an ItemEditor is valid
    VALIDATORS: dict[str, Callable[[Any], bool]] = {}

    # These functions are called when the value of a DataItem is changed. Can be used
    # to perform specific actions.
    FIELD_CHANGE_SIGNALS: dict[str, QC.Signal] = {}  # type: ignore

    def __init__(self, parent=None, debug=False):
        QW.QTreeView.__init__(self, parent)
        self.debug = debug
        self.planning: Optional[PlanningData] = None
        self.item_data: dict[int, QW.TreeWidgetItem] = {}
        self.item_rows = {}

        self.setWindowTitle(self.TITLE)

        self.setAlternatingRowColors(True)
        self.setUniformRowHeights(True)
        if IS_DARK:
            bg_color = QG.QColor(45, 45, 45)
            bg_color_light = QG.QColor(55, 55, 55)
            self.setStyleSheet(
                f"""
            QTreeView {{
                alternate-background-color: {bg_color_light.name()};
                background: {bg_color.name()};
            }}
            """
            )

        families = [MAIN_FONT_FAMILY, "Verdana"]
        nfont = Conf.tree.normal.get({"family": families, "size": 11})
        sfont = Conf.tree.small.get({"family": families, "size": 10})

        self.setFont(nfont)
        header = self.header()
        header.setFont(sfont)
        header.setDefaultAlignment(QC.Qt.AlignCenter)
        header.setStretchLastSection(True)

        model = QG.QStandardItemModel(0, 1)
        model.itemChanged.connect(self.model_item_changed)
        self.setModel(model)

        self.setItemDelegate(TaskTreeDelegate(self, 10, self.FIELD_CHANGE_SIGNALS))

        self.menu = QW.QMenu(self)

        self.edit_action = None
        self.remove_action = None
        self.up_action = None
        self.down_action = None
        self.reload_action = None
        self.always_enabled_actions = []
        self.specific_actions = self.setup_specific_actions()
        self.toolbar = self.create_toolbar()

        self.selectionModel().selectionChanged.connect(self.selection_changed)

        self.clicked.connect(self.item_was_clicked)
        self.collapsed.connect(lambda index: self.item_collapsed_expanded(index, True))
        self.expanded.connect(lambda index: self.item_collapsed_expanded(index, False))

    def setup(self, planning: PlanningData):
        """Setup widget"""
        self.planning = planning
        self.repopulate()

    def item_collapsed_expanded(self, index: QC.QModelIndex, collapsed: bool):
        """Item has been collapsed or expanded"""
        item = self.model().itemFromIndex(index)
        data_id = self.get_id_from_item(item)
        data = self.planning.get_data_from_id(data_id)
        if isinstance(data, ResourceData) and bool(data.collapsed.value) != collapsed:
            data.collapsed.value = collapsed
            self.SIG_MODEL_CHANGED.emit()

    def repopulate(self):
        """Clear and repopulate tree"""
        data_id = self.get_current_id()
        model = self.model()
        model.clear()
        self.item_data = {}
        self.item_rows: dict[str, list[QG.QStandardItem]] = {}
        self.populate_tree()
        model.setHorizontalHeaderLabels(self.NAMES)
        self.blockSignals(True)
        self.expandAll()
        for col in self.COLUMNS_TO_RESIZE:
            self.resizeColumnToContents(col)
            if col != 0:
                column_width = self.columnWidth(col)
                self.setColumnWidth(col, column_width + self.COLUMN_WIDTH_MARGIN)
        self.expandAll()
        self.blockSignals(False)
        # Iterate over resources and collapse nodes with collapsed data item to True:
        for data in self.planning.iterate_resource_data():
            if bool(data.collapsed.value):
                item_row = self.get_item_row_from_id(data.id.value)
                if item_row is not None:
                    self.setExpanded(item_row[0].index(), False)
        if data_id is not None:
            self.set_current_id(data_id, scroll_to=True)
        self.SIG_MODEL_CHANGED.emit()
        self.setFocus()

    def refresh(self):
        """Refresh tree (without clearing it)"""
        self.model().blockSignals(True)
        self.populate_tree()
        self.model().blockSignals(False)
        self.SIG_MODEL_CHANGED.emit()

    def create_toolbar(self):
        """Create toolbar"""
        toolbar = QW.QToolBar(self.TITLE)
        add_actions(toolbar, self.specific_actions)
        return toolbar

    def setup_specific_actions(self):
        """Setup context menu specific actions"""
        self.edit_action = create_action(
            self,
            _("Edit"),
            icon=get_icon("edit.svg"),
            shortcut=QC.Qt.Key_F2,
            triggered=self.edit_current_item,
        )
        self.remove_action = create_action(
            self,
            _("Delete"),
            icon=get_icon("libre-gui-trash.svg"),
            shortcut=keybinding("Delete"),
            triggered=self.remove,
        )
        self.up_action = create_action(
            self,
            _("Move up"),
            icon=get_icon("move_up.svg"),
            triggered=lambda delta=-1: self.move(delta),
        )
        self.down_action = create_action(
            self,
            _("Move down"),
            icon=get_icon("move_down.svg"),
            triggered=lambda delta=1: self.move(delta),
        )
        self.reload_action = create_action(
            self,
            title=_("Update tree"),
            icon=get_icon("libre-gui-refresh.svg"),
            triggered=self.repopulate,
        )
        return [
            self.edit_action,
            self.remove_action,
            None,
            self.up_action,
            self.down_action,
            None,
            self.reload_action,
        ]

    def set_specific_actions_state(self, state):
        """Set specific actions state"""
        for action in self.specific_actions:
            if action not in [None] + self.always_enabled_actions:
                action.setEnabled(state)

    def item_was_clicked(self, index):
        """Reimplement QAbstractItemView method"""
        item = self.model().itemFromIndex(index)
        if item.column() in self.COLUMNS_TO_EDIT_ON_CLICK:
            self.edit(index)

    def selection_changed(self, selected, deselected):
        """Selection has changed"""
        self.selected_indexes_changed(selected.indexes(), deselected.indexes())

    # pylint: disable=unused-argument
    def selected_indexes_changed(self, sel_indexes, desel_indexes):
        """Selected indexes have changed"""
        self.set_specific_actions_state(True)
        if sel_indexes:
            item = self.get_item_from_index(sel_indexes[0])
            parent = self.get_item_parent(item)
            self.up_action.setEnabled(item.row() > 0)
            # FIXME: The next condition is not sufficient for a task data because
            # down_action should be disabled if the next data is "LeaveData"
            self.down_action.setEnabled(item.row() < parent.rowCount() - 1)

    def update_menu(self):
        """Update context menu"""
        self.menu.clear()
        indexes = self.selectedIndexes()
        actions = self.get_actions_from_indexes(indexes)
        if actions:
            actions.append(None)
        actions += self.specific_actions
        add_actions(self.menu, actions)

    def contextMenuEvent(self, event):  # pylint: disable=C0103
        """Override Qt method"""
        self.update_menu()
        self.menu.popup(event.globalPos())

    # pylint: disable=unused-argument
    def get_actions_from_indexes(self, indexes):
        """Get actions from indexes"""
        # Right here: add other actions if necessary
        # (reimplement this method)
        return [self.edit_action]

    def get_item_from_index(self, index: QC.QModelIndex) -> QG.QStandardItem:
        """Get item from index"""
        item = self.model().itemFromIndex(index)
        if item is not None and item.column() > 0:
            parent = item.parent()
            if parent is None:
                return self.model().item(item.row(), 0)
            return parent.child(item.row(), 0)
        return item

    def get_current_item(self) -> QG.QStandardItem:
        """Return current item"""
        return self.get_item_from_index(self.currentIndex())

    def edit_current_item(self):
        """Edit current item (if possible)"""
        item = self.get_current_item()
        self.edit(item.index())

    def get_item_parent(self, item):
        """Return model item parent"""
        parent = item.parent()
        if parent is None:
            parent = self.model()
        return parent

    def get_item_row_from_id(self, data_id: int):
        """Return model item row from data id"""
        for node_id, item_row in self.item_rows.items():
            if node_id == data_id:
                return item_row
        return None

    def get_id_from_item(self, item):
        """Return data id from model item"""
        for data_id, item_row in self.item_rows.items():
            if item in item_row:
                return data_id
        return None

    def get_current_id(self):
        """Get current item associated data id"""
        return self.get_id_from_item(self.get_current_item())

    def get_current_data(self):
        """Get current item associated data"""
        current_id = self.get_current_id()
        return self.planning.get_data_from_id(current_id)

    def get_selected_data(self):
        """Get selected items associated data"""
        return [
            self.planning.get_data_from_id(
                self.get_id_from_item(self.get_item_from_index(index))
            )
            for index in self.selectedIndexes()
        ]

    def set_current_id(self, data_id, scroll_to=False):
        """Set current item by data id"""
        if self.itemDelegate().editor_opened:
            return
        item_row = self.get_item_row_from_id(data_id)
        if item_row is not None:
            index = item_row[0].index()
            self.setCurrentIndex(index)
            if scroll_to:
                self.scrollTo(index, QW.QTreeView.PositionAtCenter)

    def model_item_changed(self, item):
        """Model item has changed"""
        ditem = self.item_data[id(item)]
        ditem.from_display(item.text())
        self.SIG_MODEL_CHANGED.emit()

    @staticmethod
    def update_item_icon(item, ditem):
        """Update item state"""
        icon_name = ditem.parent.get_icon_name(ditem.name)
        if icon_name is None:
            item.setIcon(QG.QIcon())
        else:
            item.setIcon(get_icon(icon_name))

    # XXX: Unused method: still quite buggy
    def update_item_row_icons(self, item):
        """Update the whole item row icons for specified item"""
        parent = self.get_item_parent(item)
        row = item.row()
        for column in range(len(self.ATTRS)):
            item = parent.child(row, column)
            ditem = self.item_data.get(id(item))
            if ditem is not None:
                self.update_item_icon(item, ditem)

    def add_or_update_item_row(self, data: AbstractData, parent=None, group=False):
        """Add data item row to tree, or update it if already present"""
        update = data.id.value in self.item_rows
        items: list[QG.QStandardItem] = (
            self.item_rows[data.id.value or ""] if update else []
        )
        for column, attrs in enumerate(self.ATTRS):
            if not isinstance(attrs, tuple):
                attrs = (attrs,)

            ditems: list[DataItem | None] = [
                getattr(data, attr, None) for attr in attrs
            ]

            ditem: DataItem | None = None
            for ditem in ditems:
                if ditem is not None and ditem.value is not None:
                    break
            else:
                ditem = ditems[0]

            text: str = "" if ditem is None else ditem.to_display()

            if update:
                item = items[column]
                item.setText(text)
                if ditem is not None:
                    self.update_item_icon(item, ditem)
                    if ditem.datatype == DTypes.COLOR and ditem.value is not None:
                        color = ditem.get_html_color(ditem.value)
                        item.setBackground(QG.QBrush(QG.QColor(color)))
            else:
                item = QG.QStandardItem(text)
                self.item_data[id(item)] = ditem
                if column == 0 and group:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)

                if ditem is not None and data.is_read_only(ditem.name):
                    item.setForeground(QG.QBrush(QC.Qt.GlobalColor.gray))

                item.setEditable(
                    ditem is not None and not data.is_read_only(ditem.name)
                )
                if ditem is not None:
                    if ditem.datatype in (
                        DTypes.DATE,
                        DTypes.DAYS,
                        DTypes.BOOLEAN,
                        DTypes.COLOR,
                    ):
                        item.setTextAlignment(QC.Qt.AlignCenter)
                    if ditem.datatype == DTypes.COLOR and ditem.value is not None:
                        color = ditem.get_html_color(ditem.value)
                        item.setBackground(QG.QBrush(QG.QColor(color)))
                    self.update_item_icon(item, ditem)
                items.append(item)
        if not update:
            self.item_rows[data.id.value] = items
            if parent is None:
                parent = self.model()
            parent.appendRow(items)

    def populate_tree(self):
        """Populate tree"""
        raise NotImplementedError

    def move(self, delta_index):
        """Move up/down current item"""
        item = self.get_current_item()
        parent = self.get_item_parent(item)
        row = item.row()
        data_id = self.get_id_from_item(item)
        self.planning.move_data(data_id, delta_index)
        items = parent.takeRow(row)
        parent.insertRow(row + delta_index, items)
        self.repopulate()
        item_row = self.get_item_row_from_id(data_id)
        self.setCurrentIndex(item_row[0].index())

    def remove_item(self, item):
        """Remove item"""
        while item.hasChildren():
            self.remove_item(item.child(0))
        data_id = self.get_id_from_item(item)
        self.item_rows.pop(data_id)
        parent = self.get_item_parent(item)
        row = item.index().row()
        parent.removeRow(row)
        self.planning.remove_data(data_id)

    def remove(self):
        """Remove selected items"""
        item = self.get_current_item()
        if item is not None:
            self.remove_item(item)
            self.repopulate()


class TaskTreeWidget(BaseTreeWidget):
    """Tasks Browser Tree Widget"""

    TITLE = _("Task tree")
    NAMES = (
        _("Name"),
        _("Start"),
        _("Duration"),
        _("End"),
        "%",
        _("Color"),
        _("#"),
        _("Depends on"),
        _("Project"),
    )
    ATTRS = (
        ("fullname", "name"),
        ("start", "start_calc"),
        "duration",
        ("stop", "stop_calc"),
        "percent_done",
        "color",
        "task_number",
        "depends_on_task_number",
        "project",
    )
    TYPES = (
        DTypes.TEXT,
        DTypes.DATE,
        DTypes.DAYS,
        DTypes.DATE,
        DTypes.INTEGER,
        DTypes.COLOR,
        DTypes.TEXT,
        DTypes.MULTIPLE_CHOICE,
        DTypes.CHOICE,
    )
    COLUMNS_TO_RESIZE = (0, 1, 3, 4, 5, 6, 7)
    COLUMNS_TO_EDIT_ON_CLICK = ()
    FIELD_CHANGE_SIGNALS = {}

    SIG_UPDATE_IDS_ON_CHANGE = QC.Signal(DataItem)
    SIG_TASK_NANE_CHANGED = QC.Signal(DataItem)

    def __init__(self, parent=None, debug=False):
        self.reload_action = None
        self.new_resource_action = None
        self.new_task_action = None
        self.duplicate_task_action = None
        self.new_milestone_action = None
        self.new_leave_action = None
        self.task_mode_action = None
        BaseTreeWidget.__init__(self, parent, debug)

        self.VALIDATORS["percent_done"] = (
            lambda value: value is None or 0 <= value <= 100
        )

        # Correct a bug where an empty name is accepted. Then if the user sets a new
        # name, it wouldn't be set in the "name" dataitem, but in fullname. The result
        # is taht the name propety cannot be edited anymore and all the previews
        # disappear.
        self.VALIDATORS["name"] = lambda new_name: new_name != ""

        self.SIG_UPDATE_IDS_ON_CHANGE.connect(self._update_ids_on_change)
        self.SIG_TASK_NANE_CHANGED.connect(self._update_choices_on_change)

        self.FIELD_CHANGE_SIGNALS["depends_on_task_number"] = (
            self.SIG_UPDATE_IDS_ON_CHANGE
        )
        self.FIELD_CHANGE_SIGNALS["name"] = self.SIG_TASK_NANE_CHANGED

    def _update_ids_on_change(self, ditem: DataItem[str]):
        if isinstance(ditem.parent, AbstractTaskData):
            ditem.parent.update_depends_on_from_task_number()

    def _update_choices_on_change(self, ditem: DataItem[str]):
        """Update choices on change"""
        if isinstance(ditem.parent, AbstractTaskData) and self.planning:
            self.planning.task_choices(True)
            for data in self.planning.iterate_task_data():
                data.update_task_choices()

    def setup_specific_actions(self):
        """Setup context menu specific actions"""
        self.new_resource_action = create_action(
            self,
            _("New resource"),
            icon=get_icon("new_resource.svg"),
            triggered=self.new_resource,
        )
        self.new_task_action = create_action(
            self,
            _("New task"),
            icon=get_icon("new_task.svg"),
            triggered=self.new_task,
        )
        self.duplicate_task_action = create_action(
            self,
            _("Duplicate task"),
            icon=get_icon("duplicate_task.svg"),
            triggered=self.duplicate_task,
        )
        self.new_milestone_action = create_action(
            self,
            _("New milestone"),
            icon=get_icon("new_milestone.svg"),
            triggered=self.new_milestone,
        )
        self.new_leave_action = create_action(
            self,
            _("New leave"),
            icon=get_icon("new_leave.svg"),
            triggered=self.new_leave,
        )
        self.task_mode_action = create_action(
            self, _("Duration mode"), toggled=self.enable_duration_mode
        )
        self.remove_start_action = create_action(
            self, _("Remove start date"), triggered=self.remove_start
        )
        self.always_enabled_actions += [
            self.new_resource_action,
            self.new_task_action,
            self.duplicate_task_action,
            self.new_milestone_action,
        ]
        return [
            self.new_resource_action,
            self.new_task_action,
            self.duplicate_task_action,
            self.new_milestone_action,
            self.new_leave_action,
            None,
        ] + super().setup_specific_actions()

    def selected_indexes_changed(self, sel_indexes, desel_indexes):
        """Selected indexes have changed"""
        super().selected_indexes_changed(sel_indexes, desel_indexes)
        if self.planning is not None:
            data = self.get_current_data()
            self.new_leave_action.setEnabled(
                isinstance(data, (ResourceData, LeaveData))
                or (isinstance(data, TaskData) and not data.no_resource)
            )

            is_task = isinstance(data, AbstractTaskData)
            self.duplicate_task_action.setEnabled(is_task)

    def get_actions_from_indexes(self, indexes):
        """Get actions from indexes"""
        actions = super().get_actions_from_indexes(indexes)
        if indexes:
            item = self.model().itemFromIndex(indexes[0])
            data_id = self.get_id_from_item(item)
            data = self.planning.get_data_from_id(data_id)
            if isinstance(data, TaskData):
                state = data.get_mode() is TaskModes.DURATION
                tma = self.task_mode_action
                tma.blockSignals(True)
                tma.setChecked(state)
                tma.blockSignals(False)
                tma.setEnabled(data.is_mode_switchable())
                other_actions = [tma]
                prevdata = data.get_previous()
                if (
                    prevdata is not None
                    and data.has_start
                    and (prevdata.has_stop or prevdata.has_duration)
                ):
                    other_actions += [self.remove_start_action]
                actions = other_actions + actions
        return actions

    def enable_duration_mode(self, state):
        """Enable duration mode for current task (if current is a task)"""
        data = self.get_current_data()
        if isinstance(data, TaskData) and (data.has_duration or data.has_stop):
            data.set_mode(TaskModes.DURATION if state else TaskModes.STOP)
            self.repopulate()

    def remove_start(self):
        """Remove start date"""
        data = self.get_current_data()
        data.start.value = None
        self.repopulate()

    def new_resource(self):
        """New resource item"""
        data = ResourceData(self.planning, EMPTY_NAME)
        self.planning.add_resource(data, after_data=self.get_current_data())
        self.__add_resourceitem(data)
        self.set_current_id(data.id.value)
        self.repopulate()
        self.edit(self.currentIndex())

    def new_task(self):
        """New task item"""
        item = self.get_current_item()
        data = TaskData(self.planning, EMPTY_NAME)
        data.start.value = datetime.date.today()
        data.duration.value = 1
        current_data = self.get_current_data()
        if self.planning is None:
            return
        if isinstance(current_data, ResourceData):
            resids = [current_data.id.value]
        else:
            if item is None or item.parent() is None:
                resids = []
            else:
                resids = [self.get_id_from_item(item.parent())]

            if current_data is not None:
                data.project.value = current_data.project.value

            if isinstance(current_data, AbstractTaskData):
                data.depends_on.value = [current_data.id.value]
                data.start.value = (
                    current_data.stop_calc.value
                    if isinstance(current_data, TaskData)
                    else current_data.stop.value
                )
                data.duration.value = 1

            elif len(resids) == 1:
                current_data = list(self.planning.iterate_task_data(resids))[-1]
                data.start.value = current_data.stop.value or current_data.start.value
                data.duration.value = 1

        data.set_resource_ids(resids)
        self.planning.add_task(data, after_data=current_data)
        self.__add_taskitem(data)
        self.set_current_id(data.id.value)
        self.repopulate()
        self.edit(self.currentIndex())

    def duplicate_task(self):
        """Duplicates the selected task."""
        current_data: AbstractData | None = self.get_current_data()
        if isinstance(current_data, AbstractTaskData):
            data = current_data.duplicate()
            self.planning.add_task(data, after_data=current_data)
            self.__add_taskitem(data)
            self.set_current_id(data_id=data.id.value)
            self.repopulate()
            self.edit(self.currentIndex())

    def new_milestone(self):
        """New milestone item"""
        item = self.get_current_item()
        if item is not None:
            data = MilestoneData(self.planning, EMPTY_NAME)
            self.planning.add_task(data, after_data=self.get_current_data())
            self.__add_taskitem(data)
            self.set_current_id(data.id.value)
            self.repopulate()
            self.edit(self.currentIndex())

    def new_leave(self):
        """New leave item"""
        item = self.get_current_item()
        if item is not None:
            resnode = item if item.parent() is None else item.parent()
            data = LeaveData(self.planning)
            data.set_resource_id(self.get_id_from_item(resnode))
            self.planning.add_leave(data, after_data=self.get_current_data())
            self.__add_leaveitem(data)
            self.set_current_id(data.id.value)
            self.repopulate()
            item_row = self.get_item_row_from_id(data.id.value)
            self.edit(item_row[1].index())

    def __add_resourceitem(self, data: ResourceData):
        """Add resource item to tree"""
        self.add_or_update_item_row(data, group=True)

    def __add_taskitem(self, data: MilestoneData | TaskData):
        """Add task/milestone item to tree"""
        if isinstance(data, MilestoneData):
            self.add_or_update_item_row(data)
        else:
            for resid in data.iterate_resource_ids():
                parent_row = self.get_item_row_from_id(resid)[0]
                self.add_or_update_item_row(data, parent_row)
            if data.no_resource:
                self.add_or_update_item_row(data)

    def __add_leaveitem(self, data: LeaveData):
        """Add leave item to tree"""
        parent_row = self.get_item_row_from_id(data.get_resource_id())[0]
        self.add_or_update_item_row(data, parent_row)

    def populate_tree(self):
        """Populate tree"""
        self.SIG_MODEL_CHANGED.emit()
        if self.planning is None:
            return
        # add resources
        for data in self.planning.iterate_resource_data():
            self.__add_resourceitem(data)
        # add tasks
        for data in self.planning.iterate_task_data():
            self.__add_taskitem(data)
        # add vacations
        for data in self.planning.iterate_leave_data():
            self.__add_leaveitem(data)

    def remove_item(self, item):
        """Remove item"""
        data = self.planning.get_data_from_id(self.get_id_from_item(item))
        if (
            isinstance(data, TaskData)
            and data.has_start
            and (data.has_stop or data.has_duration)
        ):
            prev_data = data.get_previous()
            next_data = data.get_next()
            if (prev_data is None) and (
                next_data is not None and not next_data.has_start
            ):
                if data.has_duration:
                    duration = datetime.timedelta(days=data.duration.value)
                    next_data.start.value = data.start.value + duration
                else:
                    duration = datetime.timedelta(days=1)
                    next_data.start.value = data.stop.value + duration
                while next_data.start.value.weekday() in (5, 6):
                    next_data.start.value += datetime.timedelta(days=1)
        super().remove_item(item)


class ChartTreeWidget(BaseTreeWidget):
    """Chart Tree Widget"""

    SIG_CHART_CHANGED = QC.Signal(int)

    TITLE = _("Chart tree")
    NAMES = (
        _("Name"),
        _("Start"),
        _("Today"),
        _("End"),
        _("Type"),
        _("Scale"),
        _("T0 mode"),
        _("Projects"),
    )
    ATTRS = ("name", "start", "today", "stop", "type", "scale", "t0mode", "projects")
    COLUMNS_TO_RESIZE = (0, 1, 2, 3, 6)
    COLUMNS_TO_EDIT_ON_CLICK = (4, 5, 6)
    TYPES = (
        DTypes.TEXT,
        DTypes.DATE,
        DTypes.DATE,
        DTypes.DATE,
        DTypes.TEXT,
        DTypes.TEXT,
        DTypes.BOOLEAN,
        DTypes.MULTIPLE_CHOICE,
    )
    FIELD_CHANGE_SIGNALS = {}

    SIG_CHART_NAME_CHANGED = QC.Signal(DataItem)
    SIG_PROJECT_SELECTION_CHANGED = QC.Signal(DataItem)

    def __init__(self, parent=None, debug=False):
        self.new_chart_action = None
        self.set_today_action = None
        BaseTreeWidget.__init__(self, parent, debug)
        self.setSelectionMode(QW.QTreeView.ExtendedSelection)
        self.VALIDATORS["name"] = self.validate_chart_name

        self.FIELD_CHANGE_SIGNALS["name"] = self.SIG_CHART_NAME_CHANGED
        self.FIELD_CHANGE_SIGNALS["projects"] = self.SIG_PROJECT_SELECTION_CHANGED

        self.SIG_CHART_NAME_CHANGED.connect(self.check_default_svg_name)

    def check_default_svg_name(self, ditem: DataItem[str]):
        parent = ditem.parent
        if self.planning is None or not isinstance(parent, ChartData):
            return
        parent.set_is_default_name()
        if (
            parent.is_default_name
            and self.planning is not None
            and self.planning.filename is not None
        ):
            index = self.currentIndex().row() + 1
            parent.set_chart_filename(self.planning.filename, index)

    def setup_specific_actions(self):
        """Setup context menu common actions"""
        self.set_today_action = create_action(
            self,
            _("Set current date to today"),
            icon=get_icon("today.svg"),
            triggered=self.set_today,
        )
        self.new_chart_action = create_action(
            self,
            _("New chart"),
            icon=get_icon("new_chart.svg"),
            triggered=self.new_chart,
        )
        self.always_enabled_actions += [self.new_chart_action]
        return [
            self.set_today_action,
            None,
            self.new_chart_action,
        ] + super().setup_specific_actions()

    def selected_indexes_changed(self, sel_indexes, desel_indexes):
        """Selected indexes have changed"""
        super().selected_indexes_changed(sel_indexes, desel_indexes)
        self.set_today_action.setEnabled(len(sel_indexes) > 0)
        if sel_indexes:
            self.SIG_CHART_CHANGED.emit(sel_indexes[0].row())

    def set_today(self):
        """Set today to... today"""
        for data in self.get_selected_data():
            data.set_today()
        self.repopulate()

    def new_chart(self):
        """New chart item"""
        data = ChartData(self.planning, EMPTY_NAME)
        data.is_default_name = True
        data.set_chart_filename(self.planning.filename, self.currentIndex().row() + 1)
        self.planning.add_chart(data, after_data=self.get_current_data())
        self.__add_chartitem(data)
        self.set_current_id(data.id.value)
        self.repopulate()

    def __add_chartitem(self, data: ChartData):
        """Add chart item to tree"""
        self.add_or_update_item_row(data)

    def validate_chart_name(self, new_name: str):
        """Check duplicate name and if name is valid for a chart name (Only letters and
        numbes, dash, underscore and dot allowed)."""

        if self.planning is None:
            return False

        for data in self.planning.iterate_chart_data():
            if data.name.value == new_name:
                return False
        validation_regex = re.compile(r"^[a-zA-Z0-9_-.]+$")
        return bool(validation_regex.match(new_name))

    def populate_tree(self):
        """Populate tree"""
        # add charts
        if self.planning is None:
            return
        for data in self.planning.iterate_chart_data():
            self.__add_chartitem(data)


class ProjectTreeWidget(BaseTreeWidget):
    """Chart Tree Widget"""

    TITLE = _("Project tree")
    NAMES = (
        _("Name"),
        _("color"),
        _("Show description"),
        _("Description"),
    )
    ATTRS = (
        "name",
        "color",
        "show_description",
        "description",
    )
    COLUMNS_TO_RESIZE = (0, 1, 2)
    COLUMNS_TO_EDIT_ON_CLICK = (2,)
    TYPES = (
        DTypes.TEXT,
        DTypes.COLOR,
        DTypes.BOOLEAN,
        DTypes.LONG_TEXT,
    )
    FIELD_CHANGE_SIGNALS = {}
    SIG_PROJECT_NANE_CHANGED = QC.Signal(DataItem)

    def __init__(self, parent: Optional[QW.QWidget] = None, debug=False):
        BaseTreeWidget.__init__(self, parent, debug)
        self.new_project_action: Optional[QW.QAction] = None  # type: ignore
        self.FIELD_CHANGE_SIGNALS["name"] = self.SIG_PROJECT_NANE_CHANGED

        self.SIG_PROJECT_NANE_CHANGED.connect(self._update_project_names)

    def setup_specific_actions(self):
        """Setup context menu common actions"""
        self.new_project_action = create_action(
            self,
            _("New project"),
            icon=get_icon("new_chart.svg"),
            triggered=self.new_project,
        )
        self.remove_action = create_action(
            self,
            _("Delete"),
            icon=get_icon("libre-gui-trash.svg"),
            shortcut=keybinding("Delete"),
            triggered=self.remove,
        )
        self.always_enabled_actions += [self.new_project_action]
        return [self.new_project_action, None] + super().setup_specific_actions()

    def _update_project_names(self):
        """Update project names"""
        if self.planning is None:
            return

        self.planning.project_choices(force=True)
        for chart in self.planning.iterate_chart_data():
            chart.update_project_choices()
        for task in self.planning.iterate_task_data():
            task.update_project_choice()

    def new_project(self):
        """New chart item"""
        if self.planning is not None:
            project = ProjectData(self.planning, EMPTY_NAME)
            current_data = self.get_current_data()
            if not isinstance(current_data, ProjectData):
                current_data = None
            self.planning.add_project(project, current_data)
            self.__add_projectitem(project)
            self.set_current_id(project.id.value)
            self.repopulate()
            self._update_project_names()

    def remove(self):
        """Remove selected items"""
        item = self.get_current_item()
        project_id = self.get_id_from_item(item)
        if self.planning is not None and project_id is not None:
            project_to_delete = self.planning.projects.pop(project_id)
            self.planning.prjlist.remove(project_to_delete)
            self._update_project_names()
            self.repopulate()

    def __add_projectitem(self, data: ProjectData):
        """Add chart item to tree"""
        self.add_or_update_item_row(data)

    def populate_tree(self):
        """Populate tree"""
        # add charts
        if self.planning is None:
            return
        for data in self.planning.iterate_project_data():
            self.__add_projectitem(data)


class TreeWidgets(QW.QSplitter):
    """Task/Chart tree widgets"""

    TITLE = _("General")
    SIG_MODEL_CHANGED = QC.Signal()
    MAX_SNAPSHOTS = 50

    def __init__(self, parent=None, debug=False):
        QW.QSplitter.__init__(self, parent)
        self.setOrientation(QC.Qt.Vertical)
        self.__snapshot_index = None
        self.__snapshots = []
        self.__snapshots_lock = False
        self.planning: Optional[PlanningData] = None

        self.project_tree = ProjectTreeWidget(self, debug=debug)
        self.chart_tree = ChartTreeWidget(self, debug=debug)
        self.task_tree = TaskTreeWidget(self, debug=debug)
        self.forest = [self.chart_tree, self.task_tree, self.project_tree]
        for tree in self.forest:
            tree.SIG_MODEL_CHANGED.connect(self.model_has_changed)
            tree.pressed.connect(self.tree_pressed)
            self.addWidget(tree)

        self.undo_action = None
        self.redo_action = None
        self.collapse_all_action = None
        self.expand_all_action = None
        self.common_actions = self.setup_common_actions()

        self.toolbars = self.create_toolbars()

        # Task tree is default
        self.task_tree.setFocus()
        self.chart_tree.set_specific_actions_state(False)
        self.chart_tree.toolbar.hide()

        self.setCollapsible(0, False)
        self.setCollapsible(1, False)
        self.setStretchFactor(0, 1)
        self.setStretchFactor(1, 4)

        # self.task_tree.FIELD_CHANGE_SIGNALS["project"] = self.SIG_MODEL_CHANGED

        # (
        #     lambda ditem: self.chart_tree.repopulate()
        # )

    def tree_pressed(self):
        """A mouse button was pressed on tree view"""
        for tree in self.forest:
            if tree is not self.sender():
                tree.clearSelection()
                tree.set_specific_actions_state(False)
            tree.toolbar.setVisible(tree is self.sender())

    def get_focus_tree(self):
        """Return tree widget which has focus"""
        for tree in self.forest:
            if tree.hasFocus():
                return tree
        return self.task_tree

    def setup_common_actions(self):
        """Setup context menu common actions"""
        self.undo_action = create_action(
            self,
            _("Undo"),
            icon=get_icon("libre-gui-undo.svg"),
            shortcut=keybinding("Undo"),
            triggered=self.undo,
        )
        self.redo_action = create_action(
            self,
            _("Redo"),
            icon=get_icon("libre-gui-redo.svg"),
            shortcut=keybinding("Redo"),
            triggered=self.redo,
        )
        self.collapse_all_action = create_action(
            self,
            _("Collapse all"),
            icon=get_icon("collapse.svg"),
            triggered=lambda: self.get_focus_tree().collapseAll(),
        )
        self.expand_all_action = create_action(
            self,
            _("Expand all"),
            icon=get_icon("expand.svg"),
            triggered=lambda: self.get_focus_tree().expandAll(),
        )
        return [
            self.undo_action,
            self.redo_action,
            None,
            self.collapse_all_action,
            self.expand_all_action,
        ]

    def create_toolbars(self):
        """Create toolbars"""
        toolbar = QW.QToolBar(self.TITLE)
        add_actions(toolbar, self.common_actions)
        toolbars = [toolbar]
        for tree in self.forest:
            toolbars.append(tree.toolbar)
        return toolbars

    def __set_toolbars_state(self):
        """Set toolbars enabled state depending on widget visibility"""
        for toolbar in self.toolbars:
            toolbar.setEnabled(self.isVisible())

    def showEvent(self, event):  # pylint: disable=invalid-name,unused-argument
        """Reimplement QWidget method"""
        self.__set_toolbars_state()

    def hideEvent(self, event):  # pylint: disable=invalid-name,unused-argument
        """Reimplement QWidget method"""
        self.__set_toolbars_state()

    def setup(self, planning):
        """Setup tree widgets"""
        self.planning = planning
        self.planning.process_gantt()
        for tree in self.forest:
            tree.setup(planning)

    def __restore_snapshot(self):
        """Restore snapshot"""
        snapshot = self.__snapshots[self.__snapshot_index]
        planning = PlanningData.from_element(PlanningData(), ET.fromstring(snapshot))
        planning.set_filename(self.planning.filename)
        self.__snapshots_lock = True
        self.setup(planning)
        self.__snapshots_lock = False

    def undo(self):
        """Undo"""
        if len(self.__snapshots) > 1:
            if self.__snapshot_index is None:
                self.__snapshot_index = len(self.__snapshots) - 2
            elif self.__snapshot_index == 0:
                return
            else:
                self.__snapshot_index -= 1
            self.__restore_snapshot()

    def redo(self):
        """Redo"""
        if self.__snapshot_index is not None:
            self.__snapshot_index += 1
            self.__restore_snapshot()
            if self.__snapshot_index == len(self.__snapshots) - 1:
                self.__snapshot_index = None

    def model_has_changed(self):
        """Model has changed"""
        if not self.__snapshots_lock:
            snapshot = ET.tostring(self.planning.to_element())
            if self.__snapshot_index is not None:
                self.__snapshots = self.__snapshots[: self.__snapshot_index]
                self.__snapshot_index = None
            if not self.__snapshots or snapshot != self.__snapshots[-1]:
                self.__snapshots.append(snapshot)
                if len(self.__snapshots) > self.MAX_SNAPSHOTS:
                    self.__snapshots.pop(0)
        self.SIG_MODEL_CHANGED.emit()
