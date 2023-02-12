# -*- coding: utf-8 -*-

"""
Planning
--------

"""

# pylint: disable=no-name-in-module

import sys

from guidata.configtools import get_image_file_path
from qtpy.QtCore import Qt
from qtpy.QtGui import QPixmap
from qtpy.QtWidgets import QSplashScreen

#  Local imports
from planning.gui.mainwindow import PlanningMainWindow
from planning.utils.qthelpers import qt_app_context


def run(fname=None):
    """Run PyPlanning"""
    if fname is None and len(sys.argv) > 1:
        fname = sys.argv[1]
    with qt_app_context(exec_loop=True):
        # Showing splash screen
        pixmap = QPixmap(get_image_file_path("planning.png"))
        splash = QSplashScreen(pixmap, Qt.WindowStaysOnTopHint)
        splash.show()
        window = PlanningMainWindow(fname)
        window.show()
        splash.finish(window)
        window.check_for_previous_crash()


if __name__ == "__main__":
    run()
