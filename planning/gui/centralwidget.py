# -*- coding: utf-8 -*-
"""PyPlanning central widget"""

# pylint: disable=no-name-in-module
# pylint: disable=no-member

import os
import os.path as osp
import traceback
import xml.etree.ElementTree as ET

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

    def __init__(self, parent=None):
        super().__init__(parent)
        self.code = CodeEditor(self, language="html")
        self.code.setLineWrapMode(CodeEditor.NoWrap)
        self.addWidget(self.code)
        self.trees = TreeWidgets(self)
        self.addWidget(self.trees)
        self.signals = [self.code.textChanged, self.trees.SIG_MODEL_CHANGED]
        self.slots = [parent.xml_code_changed, parent.tree_changed]
        self.currentChanged.connect(self.current_changed)
        self.current_changed()
        self.set_current_mode()

    @property
    def xml_mode(self):
        """Return True if XML mode is enabled"""
        return Conf.main.xml_mode.get(False)

    def current_changed(self, index=None):
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
        """Switch XML/Tree mode"""
        self.set_current_mode()
        if self.xml_mode:
            text = self.trees.planning.to_text()
        else:
            text = self.code.toPlainText()
        self.set_text_and_path(text, path)

    def get_menu_actions(self):
        """Return menu actions"""
        return {
            "edit": self.trees.common_actions,
            "charts": self.trees.chart_tree.specific_actions,
            "tasks": self.trees.task_tree.specific_actions,
        }

    def clear_all(self):
        """Clear all contents"""
        if self.xml_mode:
            self.code.setPlainText(PlanningData().to_text())
        else:
            self.trees.setup(PlanningData())

    def load_file(self, path):
        """Load data from file"""
        if self.xml_mode:
            self.code.set_text_from_file(path)
        else:
            planning = PlanningData.from_filename(path)
            self.trees.setup(planning)

    def save_file(self, path):
        """Save data to file"""
        if self.xml_mode:
            text = self.code.toPlainText()
            with open(path, "wb") as fdesc:
                fdesc.write(text.encode("utf-8"))
        else:
            self.trees.planning.to_filename(path)
            self.trees.chart_tree.repopulate()

    def set_text_and_path(self, text, path):
        """ "Set text and path"""
        if self.xml_mode:
            self.code.setPlainText(text)
        else:
            planning = PlanningData()
            try:
                planning = PlanningData.from_element(planning, ET.fromstring(text))
            except ET.ParseError:
                pass
            planning.set_filename(path)
            self.trees.setup(planning)


class PlanningPreview(QTabWidget):
    """Planning preview widget"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.__path = None
        self.views = None
        self.clear_all_tabs()

    def clear_all_tabs(self):
        """Clear all tabs"""
        self.__path = None
        self.views = {}
        for index in reversed(range(self.count())):
            self.removeTab(index)

    def update_tabs(self, fnames):
        """Update tabs"""
        old_current = self.tabText(self.currentIndex())
        bnames = [osp.basename(fname) for fname in fnames]
        if fnames:
            self.__path = osp.dirname(fnames[0])
        for to_remove in set(self.views.keys()) - set(bnames):
            for index in reversed(range(self.count())):
                if to_remove == self.tabText(index):
                    self.removeTab(index)
                    self.views.pop(to_remove)
                    if self.__path is not None:
                        os.remove(osp.join(self.__path, to_remove))
        for fname, bname in zip(fnames, bnames):
            if bname in self.views:
                viewer = self.views[bname]
            else:
                self.views[bname] = viewer = SVGViewer()
                index = self.addTab(viewer, get_icon("chart.svg"), bname)
                self.setTabToolTip(index, fname)
            viewer.load(fname)
            if bname == old_current:
                self.setCurrentWidget(viewer)


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
        self.addWidget(self.preview)

        self.setCollapsible(0, False)
        self.setCollapsible(1, False)
        self.setStretchFactor(0, 2)
        self.setStretchFactor(1, 1)

    @property
    def planning(self):
        """Return PlanningData instance"""
        return self.editor.trees.planning

    def get_toolbars(self):
        """Return toolbars"""
        return self.editor.trees.toolbars

    def _print_do_not_panic(self):
        """Print 'do not panic' message in console"""
        tbtext = traceback.format_exc()
        self.SIG_MESSAGE.emit(tbtext, 10000)
        if DEBUG >= 3:
            raise  # pylint: disable=misplaced-bare-raise
        print("")
        print("+-------------------------------------------------------+")
        print("| Please do not panic: this is not an error message     |")
        print("| (otherwise it would be written in red...).            |")
        print("| This is not a bug.                                    |")
        print("| This is just logging, for debugging purpose.          |")
        print("+-------------------------------------------------------+")
        print("")
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
            planning.generate_charts()
            self.preview.update_tabs(planning.chart_filenames)
        except (ValueError, KeyError, AssertionError, TypeError):
            self._print_do_not_panic()

    def tree_changed(self):
        """Tree widget has changed"""
        self.SIG_MODIFIED.emit()
        try:
            self.planning.generate_charts()
            self.preview.update_tabs(self.planning.chart_filenames)
        except (ValueError, KeyError, AssertionError, TypeError, AttributeError):
            self._print_do_not_panic()

    def new_file(self):
        """New file"""
        self.editor.clear_all()
        self.preview.clear_all_tabs()

    def __adjust_sizes(self):
        """Adjust QSplitter sizes"""
        width = self.size().width() // 2
        self.setSizes([width, width])

    def load_file(self, path):
        """Load file"""
        self.path = path
        self.preview.clear_all_tabs()
        self.editor.load_file(path)
        self.__adjust_sizes()

    def save_file(self, path):
        """Save file"""
        self.path = path
        self.editor.save_file(path)

    def set_text_and_path(self, text, path):
        """Set text and path"""
        self.path = path
        self.editor.set_text_and_path(text, path)
        self.__adjust_sizes()
