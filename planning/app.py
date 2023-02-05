# -*- coding: utf-8 -*-

"""
Planning
--------

"""

# pylint: disable=no-name-in-module

import sys

from guidata import qapplication
from guidata.configtools import get_image_file_path
from qtpy.QtCore import Qt
from qtpy.QtGui import QPixmap
from qtpy.QtWidgets import QSplashScreen

#  Local imports
from planning.gui.mainwindow import PlanningMainWindow


def run(fname=None):
    """Run PyPlanning"""
    app = qapplication()

    # Showing splash screen
    pixmap = QPixmap(get_image_file_path("planning.png"))
    splash = QSplashScreen(pixmap, Qt.WindowStaysOnTopHint)
    splash.show()

    if fname is None and len(sys.argv) > 1:
        fname = sys.argv[1]

    window = PlanningMainWindow(fname)
    splash.finish(window)
    window.show()
    app.exec()


if __name__ == "__main__":
    run()
