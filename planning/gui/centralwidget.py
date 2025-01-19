# -*- coding: utf-8 -*-
"""PyPlanning central widget"""

# pylint: disable=no-name-in-module
# pylint: disable=no-member

import os
import os.path as osp
import shutil
import traceback
import xml.etree.ElementTree as ET
from typing import Optional

from guidata.configtools import get_icon
from guidata.widgets.codeeditor import CodeEditor
from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import QSplitter, QStackedWidget, QTabWidget

from planning.config import DEBUG, Conf
from planning.gui.svgviewer import SVGViewer
from planning.gui.treewidgets import TreeWidgets
from planning.model import PlanningData


class PlanningEditor(QStackedWidget):
    """Planning editor widget"""

    def __init__(self, parent: "PlanningCentralWidget"):
        super().__init__(parent)
        self.code = CodeEditor(self, language="html")
        self.code.setLineWrapMode(CodeEditor.NoWrap)
        self.addWidget(self.code)
        self.trees = TreeWidgets(self)
        self.addWidget(self.trees)
        self.signals = [self.code.SIG_EDIT_STOPPED, self.trees.SIG_MODEL_CHANGED]
        self.slots = [parent.xml_code_changed, parent.tree_changed]
        self.currentChanged.connect(self.current_changed)
        self.current_changed()
        self.set_current_mode()

    @property
    def xml_mode(self):
        """Return True if XML mode is enabled"""
        return Conf.main.xml_mode.get(False)

    def current_changed(self, index: int | None = None):
        """Current widget has changed"""
        if index is None:
            index = self.currentIndex()
        else:
            self.signals[1 - index].disconnect(self.slots[1 - index])
        self.signals[index].connect(self.slots[index])

    def set_current_mode(self):
        """Set current mode"""
        self.setCurrentWidget(self.code if self.xml_mode else self.trees)

    def switch_mode(self, path):
        """Switch XML/Tree mode

        Returns True if mode has changed, False otherwise"""
        self.set_current_mode()
        if self.xml_mode:
            text = self.trees.planning.to_text()
        else:
            text = self.code.toPlainText()
        return self.set_text_and_path(text, path)

    def get_menu_actions(self):
        """Return menu actions"""
        return {
            "edit": self.trees.common_actions,
            "charts": self.trees.chart_tree.specific_actions,
            "tasks": self.trees.task_tree.specific_actions,
            "projects": self.trees.project_tree.specific_actions,
        }

    def clear_all(self):
        """Clear all contents"""
        self.trees.blockSignals(True)
        self.code.setPlainText(PlanningData().to_text())
        self.trees.setup(PlanningData())
        self.trees.blockSignals(False)

    def load_file(self, path):
        """Load data from file"""
        self.code.set_text_from_file(path)
        planning = PlanningData.from_filename(path)
        self.trees.setup(planning)

    def save_file(self, path):
        """Save data to file"""
        planning = self.trees.planning
        if planning is None:
            return

        default_charts_paths = [
            chart.fullname.value
            for chart in planning.chtlist
            if isinstance(chart.fullname.value, str) and chart.is_default_name
        ]
        for chart_path in default_charts_paths:
            if osp.exists(chart_path):
                shutil.copy(chart_path, osp.join(chart_path + ".tmp"))

        if self.xml_mode:
            text = self.code.toPlainText()
            with open(path, "wb") as fdesc:
                fdesc.write(text.encode("utf-8"))
        else:
            planning.to_filename(path)
            self.parent().update_planning_charts(planning, force=True)
            self.trees.chart_tree.repopulate()

        for chart_path in default_charts_paths:
            if not osp.exists(chart_path):
                if osp.exists(osp.join(chart_path + ".tmp")):
                    os.rename(osp.join(chart_path + ".tmp"), chart_path)
            else:
                os.remove(osp.join(chart_path + ".tmp"))

    def set_text_and_path(self, text, path):
        """Set text and path

        Returns True if planning was successfully updated, False otherwise"""
        if self.xml_mode:
            self.code.setPlainText(text)
        else:
            planning = PlanningData()
            try:
                planning = PlanningData.from_element(planning, ET.fromstring(text))
            except ET.ParseError:
                return False
            planning.set_filename(path)
            self.trees.setup(planning)
        return True


class PlanningPreview(QTabWidget):
    """Planning preview widget"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.__path = None
        self.views: dict[str, SVGViewer] = {}
        self.clear_all_tabs()

    def clear_all_tabs(self):
        """Clear all tabs"""
        self.__path = None
        self.views.clear()
        for index in reversed(range(self.count())):
            self.removeTab(index)

    def update_tabs(self, fnames: list[str]):
        """Update tabs"""
        old_current = self.tabText(self.currentIndex())
        bnames = [osp.basename(fname) for fname in fnames]
        if fnames:
            self.__path = osp.dirname(fnames[0])
        for to_remove in set(self.views.keys()) - set(bnames):
            for index in reversed(range(self.count())):
                if to_remove == self.tabText(index):
                    self.removeTab(index)
                    pop = None
                    if to_remove in self.views:
                        pop = self.views.pop(to_remove)
                    if (
                        pop is not None
                        and self.__path is not None
                        and osp.exists(
                            path_to_remove := osp.join(self.__path, to_remove)
                        )
                    ):
                        os.remove(path_to_remove)
        for i, (fname, bname) in enumerate(zip(fnames, bnames)):
            if bname in self.views:
                viewer = self.views[bname]
            else:
                self.views[bname] = viewer = SVGViewer()
                index = self.insertTab(i, viewer, get_icon("chart.svg"), bname)
                self.setTabToolTip(index, fname)
            viewer.load(fname)
            if bname == old_current:
                self.setCurrentWidget(viewer)

    def update_tab(self, index: int, fname: str):
        """Updates a single SVG preview tab.

        Args:
            index: tab index to update
            fname: filame to rename the tab
        """
        if self.count() == 0:
            return
        new_bname = osp.basename(fname)
        prev_bname = self.tabText(index)
        if (
            new_bname != prev_bname
            and self.__path is not None
            and osp.exists(path_to_remove := osp.join(self.__path, prev_bname))
        ):
            os.remove(path_to_remove)
        viewer = self.views.pop(prev_bname)
        viewer.load(fname)
        self.views[new_bname] = viewer
        self.setTabText(index, new_bname)
        self.setTabToolTip(index, fname)


class PlanningCentralWidget(QSplitter):
    """PyPlanning central widget"""

    SIG_MODIFIED = Signal()
    SIG_MESSAGE = Signal(str, int)

    def __init__(self):
        super().__init__()
        self.setMinimumSize(850, 400)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setOrientation(Qt.Horizontal)
        self.path = None
        self.xml_code = None

        self.editor = PlanningEditor(self)
        self.preview = PlanningPreview(self)
        self.editor.trees.chart_tree.SIG_CHART_CHANGED.connect(
            self.preview.setCurrentIndex
        )
        self.preview.currentChanged.connect(self.current_tab_changed)
        self.addWidget(self.preview)

        self.setCollapsible(0, False)
        self.setCollapsible(1, False)
        self.setStretchFactor(0, 2)
        self.setStretchFactor(1, 1)

        self.editor.trees.chart_tree.SIG_CHART_NAME_CHANGED.connect(
            lambda _ditem: self.update_planning_charts(self.planning)
        )

    @property
    def planning(self) -> PlanningData:
        """Return PlanningData instance"""
        return self.editor.trees.planning

    @planning.setter
    def planning(self, planning: PlanningData):
        """Return PlanningData instance"""
        self.editor.trees.planning = planning

    @property
    def is_in_xml_mode(self) -> bool:
        """Return True if XML mode is enabled"""
        return self.editor.xml_mode

    def get_toolbars(self):
        """Return toolbars"""
        return self.editor.trees.toolbars

    def _print_do_not_panic(self):
        """Print 'do not panic' message in console"""
        tbtext = traceback.format_exc()
        self.SIG_MESSAGE.emit(tbtext, 10000)
        if DEBUG >= 3:
            raise  # pylint: disable=misplaced-bare-raise
        if DEBUG >= 1:
            print("")
            print("*** This is just logging, for debugging purpose. ***")
            print(tbtext)

    def xml_code_changed(self):
        """XML code has changed"""
        self.SIG_MODIFIED.emit()
        xmlcode = self.editor.code.toPlainText()
        try:
            ET.fromstring(xmlcode)
        except ET.ParseError:
            return
        try:
            planning = PlanningData.from_element(PlanningData(), ET.fromstring(xmlcode))
            planning.set_filename(self.path)
            self.update_planning_charts(planning)
        except (ValueError, KeyError, AssertionError, TypeError, AttributeError):
            self._print_do_not_panic()

    def tree_changed(self):
        """Tree widget has changed"""
        self.SIG_MODIFIED.emit()
        try:
            self.update_planning_charts()

        except (ValueError, KeyError, AssertionError, TypeError, AttributeError):
            self._print_do_not_panic()

    def current_tab_changed(self, index: int):
        """Updates plannings charts

        Args:
            index: index of the current tab. Not used, it's a slot for Qt).
        """
        self.update_planning_charts(self.planning)

    def update_planning_charts(
        self, planning: Optional[PlanningData] = None, force=False
    ):
        """Update charts. Generates all of them if there are new ones,
        or just the current one if it already exists.

        Args:
            planning: PlanningData instance to update. If None, the current
                planning is used.
        """
        if planning is None and (planning := self.planning) is None:
            return
        planning.update_chart_names()
        chart_count = len(planning.chtlist)
        if self.preview.count() != chart_count or force:
            planning.generate_charts()
            self.preview.update_tabs(planning.chart_filenames)
        elif chart_count != 0:
            index = self.preview.currentIndex()
            planning.generate_current_chart(index)
            self.preview.update_tab(index, planning.chart_filenames[index])

    def new_file(self):
        """New file"""
        self.editor.clear_all()
        self.preview.clear_all_tabs()

    def __adjust_sizes(self):
        """Adjust QSplitter sizes"""
        width = self.size().width() // 2
        self.setSizes([width, width])

    def load_file(self, path: str):
        """Load file"""
        self.path = path
        self.editor.clear_all()
        self.preview.clear_all_tabs()
        self.editor.load_file(path)
        self.__adjust_sizes()

    def save_file(self, path: str):
        """Save file"""
        self.path = path
        self.editor.save_file(path)

    def set_text_and_path(self, text: str, path: str):
        """Set text and path"""
        self.path = path
        self.editor.set_text_and_path(text, path)
        self.__adjust_sizes()
