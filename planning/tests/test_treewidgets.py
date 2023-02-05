# -*- coding: utf-8 -*-
"""Testing PyPlanning task tree widget"""

import os.path as osp

from guidata import qapplication
from qtpy import QtWidgets as QW

from planning.config import TESTPATH
from planning.gui.treewidgets import TreeWidgets
from planning.model import PlanningData


class TestWidget(QW.QMainWindow):
    """Test widget"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.trees = TreeWidgets(self, debug=True)
        self.trees.SIG_MODEL_CHANGED.connect(self.tree_changed)
        self.setup = self.trees.setup
        self.setCentralWidget(self.trees)
        for toolbar in self.trees.toolbars:
            self.addToolBar(toolbar)

    def tree_changed(self):
        """Tree has changed"""
        try:
            self.trees.planning.generate_charts()
            print("PlanningData.generate_charts ===> OK")
        except (ValueError, KeyError, AssertionError, TypeError):
            print("PlanningData.generate_charts ===> Error !!!")


def test():
    """Test task tree widget"""
    fname = osp.join(TESTPATH, "test.xml")
    planning = PlanningData.from_filename(fname)
    app = qapplication()
    widget = TestWidget()
    widget.setup(planning)
    widget.show()
    widget.resize(1000, 500)
    app.exec_()


if __name__ == "__main__":
    test()
