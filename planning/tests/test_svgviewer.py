# -*- coding: utf-8 -*-
"""Testing SVG Viewer widget"""

import os.path as osp

from guidata import qapplication

from planning.config import TESTPATH
from planning.gui.svgviewer import SVGViewer


def test():
    """Test features"""
    fname = osp.join(TESTPATH, "test00.svg")
    app = qapplication()
    widget = SVGViewer()
    widget.show()
    widget.load(fname)
    widget.resize(1000, 500)
    app.exec_()


if __name__ == "__main__":
    test()
