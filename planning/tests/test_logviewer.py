# -*- coding: utf-8 -*-

"""
Log viewer test
"""

from guidata.qthelpers import qt_app_context

from planning.gui.logviewer import exec_logviewer_dialog

SHOW = True  # Show test in GUI-based test launcher


def test_log_viewer():
    """Test log viewer window"""
    with qt_app_context():
        exec_logviewer_dialog()


if __name__ == "__main__":
    test_log_viewer()
