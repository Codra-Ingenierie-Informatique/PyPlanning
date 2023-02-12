# -*- coding: utf-8 -*-

"""
PyPlanning Qt utilities
"""

import faulthandler
import functools
import logging
import os
import os.path as osp
import shutil
import sys
import traceback
from contextlib import contextmanager

import guidata
from guidata.widgets.codeeditor import CodeEditor
from qtpy import QtWidgets as QW

from planning.config import DATETIME_FORMAT, Conf, _, get_old_log_fname
from planning.utils.misc import to_string


class ErrorMessageBox(QW.QDialog):
    """Error message box"""

    def __init__(self, parent, funcname=None):
        super().__init__(parent)
        title = parent.window().objectName()
        self.setWindowTitle(title)
        self.editor = CodeEditor(self)
        self.editor.setReadOnly(True)
        self.editor.setPlainText(traceback.format_exc())
        bbox = QW.QDialogButtonBox(QW.QDialogButtonBox.Ok)
        bbox.accepted.connect(self.accept)
        layout = QW.QVBoxLayout()
        text = ""
        if funcname is not None:
            text += os.linesep.join(
                [
                    f"{_('An error has occured')} ({_('function')} `{funcname}`).",
                    "",
                    "",
                ]
            )
        text += _("Error message:")
        layout.addWidget(QW.QLabel(text))
        layout.addWidget(self.editor)
        layout.addSpacing(10)
        layout.addWidget(bbox)
        self.setLayout(layout)
        self.resize(800, 350)


def qt_try_except():
    """Try...except Qt widget method decorator"""

    def qt_try_except_decorator(func):
        """Try...except Qt widget method decorator"""

        @functools.wraps(func)
        def method_wrapper(*args, **kwargs):
            """Decorator wrapper function"""
            self = args[0]  # extracting 'self' from method arguments
            #  If "self" is a BaseProcessor, then we need to get the panel instance
            output = None
            try:
                output = func(*args, **kwargs)
            except Exception:  # pylint: disable=broad-except
                traceback.print_exc()
                ErrorMessageBox(self, func.__name__).exec()
            finally:
                QW.QApplication.restoreOverrideCursor()
            return output

        return method_wrapper

    return qt_try_except_decorator


QAPP_INSTANCE = None


def get_log_contents(fname):
    """Return True if file exists and something was logged in it"""
    if osp.exists(fname):
        with open(fname, "rb") as fdesc:
            return to_string(fdesc.read()).strip()
    return None


def initialize_log_file(fname):
    """Eventually keep the previous log file
    Returns True if there was a previous log file"""
    contents = get_log_contents(fname)
    if contents:
        try:
            shutil.move(fname, get_old_log_fname(fname))
        except Exception:  # pylint: disable=broad-except
            pass
        return True
    return False


def remove_empty_log_file(fname):
    """Eventually remove empty log files"""
    if not get_log_contents(fname):
        try:
            os.remove(fname)
        except Exception:  # pylint: disable=broad-except
            pass


@contextmanager
def qt_app_context(exec_loop=False, enable_logs=True):
    """Context manager handling Qt application creation and persistance"""
    global QAPP_INSTANCE  # pylint: disable=global-statement
    if QAPP_INSTANCE is None:
        QAPP_INSTANCE = guidata.qapplication()

    if enable_logs:
        # === Create a logger for standard exceptions ----------------------------------
        tb_log_fname = Conf.main.traceback_log_path.get()
        Conf.main.traceback_log_available.set(initialize_log_file(tb_log_fname))
        logger = logging.getLogger(__name__)
        fmt = "[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s"
        logging.basicConfig(
            filename=tb_log_fname,
            filemode="w",
            level=logging.CRITICAL,
            format=fmt,
            datefmt=DATETIME_FORMAT,
        )

        def custom_excepthook(exc_type, exc_value, exc_traceback):
            "Custom exception hook"
            logger.critical(
                "Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback)
            )
            return sys.__excepthook__(exc_type, exc_value, exc_traceback)

        sys.excepthook = custom_excepthook

    # === Use faulthandler for other exceptions ------------------------------------
    fh_log_fname = Conf.main.faulthandler_log_path.get()
    Conf.main.faulthandler_log_available.set(initialize_log_file(fh_log_fname))

    with open(fh_log_fname, "w", encoding="utf-8") as fh_log_fn:
        if enable_logs and Conf.main.faulthandler_enabled.get(True):
            faulthandler.enable(file=fh_log_fn)
        try:
            yield QAPP_INSTANCE
        finally:
            if exec_loop:
                QAPP_INSTANCE.exec()

    if enable_logs and Conf.main.faulthandler_enabled.get():
        faulthandler.disable()
    remove_empty_log_file(fh_log_fname)
    if enable_logs:
        logging.shutdown()
        remove_empty_log_file(tb_log_fname)
