# -*- coding: utf-8 -*-
"""Testing PyPlanning central widget"""

import os.path as osp

from guidata import qapplication

from planning.config import TESTPATH
from planning.gui.centralwidget import PlanningCentralWidget


def test():
    """Test central widget"""
    app = qapplication()
    widget = PlanningCentralWidget()
    widget.setWindowTitle("Planning editor")
    widget.show()
    widget.load_file(osp.join(TESTPATH, "test.xml"))
    app.exec_()


if __name__ == "__main__":
    test()
