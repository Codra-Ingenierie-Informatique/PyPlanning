# -*- coding: utf-8 -*-
"""Testing PyPlanning central widget"""

import os.path as osp

from planning.config import TESTPATH
from planning.gui.centralwidget import PlanningCentralWidget
from planning.utils.qthelpers import qt_app_context


def test_central_widget(fname):
    """Test central widget"""
    widget = PlanningCentralWidget()
    widget.setWindowTitle("Planning editor")
    widget.show()
    widget.load_file(fname)


def test_different_projects():
    """Test different projects"""
    example_path = osp.join(TESTPATH, osp.pardir, osp.pardir, "examples")
    with qt_app_context(exec_loop=True):
        for fname in (
            osp.join(TESTPATH, "test_v2.xml"),
            osp.join(example_path, "project_planning.xml"),
        ):
            test_central_widget(fname)


if __name__ == "__main__":
    test_different_projects()
