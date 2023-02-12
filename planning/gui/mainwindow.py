# -*- coding: utf-8 -*-

"""
planning.gui.mainwindow
-----------------------

"""

# pylint: disable=no-name-in-module
# pylint: disable=no-member
# pylint: disable=invalid-name  # Allows short reference names like x, y, ...

import os
import os.path as osp
import platform

from guidata import __version__ as GUIDATA_VERSION_STR
from guidata.configtools import get_icon
from guidata.qthelpers import add_actions, create_action, win32_fix_title_bar_background
from guidata.widgets.console import DockableConsole
from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy.compat import getopenfilename, getsavefilename

#  Local imports
from planning import __version__
from planning.config import APP_DESC, APP_NAME, DATAPATH, DEBUG, Conf, _
from planning.gui.centralwidget import PlanningCentralWidget
from planning.gui.logviewer import exec_logviewer_dialog
from planning.utils import qthelpers as qth


class PlanningMainWindow(QW.QMainWindow):
    """Planning main window"""

    MAX_RECENT_FILES = 10
    DEFAULT_NAME = _("untitled") + ".xml"

    def __init__(self, fname=None):
        """Initialize main window"""
        super().__init__()
        self.setObjectName(APP_NAME)

        win32_fix_title_bar_background(self)
        self.setWindowIcon(get_icon("planning.svg"))

        self._last_basedir = None
        self._is_modified = None
        self.filename = None
        self.recent_files = Conf.main.recent_files.get()

        self.console = DockableConsole(
            self, namespace={"win": self}, message="", debug=DEBUG >= 1
        )
        dockwidget, location = self.console.create_dockwidget("Console")
        self.addDockWidget(location, dockwidget)
        dockwidget.hide()

        self.central_widget = PlanningCentralWidget()

        def modified_callback():
            self.set_modified(True)

        self.central_widget.SIG_MODIFIED.connect(modified_callback)
        self.central_widget.SIG_MESSAGE.connect(self.process_status_message)
        self.setCentralWidget(self.central_widget)

        self.xmlmode_act = None
        self.separator_act = None
        self.new_act = None
        self.open_act = None
        self.open_recent_menu = None
        self.diropen_act = None
        self.save_act = None
        self.save_as_act = None
        self.exit_act = None
        self.about_act = None
        self.file_menu = None
        self.edit_menu = None
        self.charts_menu = None
        self.tasks_menu = None
        self.help_menu = None

        self.create_actions()
        self.create_menus()
        self.create_toolbars()
        self.statusBar().showMessage(_("Welcome to %s!") % APP_NAME, 5000)

        self.check_recent_files()
        if fname is None and self.recent_files:
            fname = self.recent_files[0]
        ok = False
        if fname is not None:
            ok = self.open_file(osp.abspath(fname))
        if not ok:
            self.new_file()
            self.set_modified(False)

        self.__restore_pos_and_size()

    def check_for_previous_crash(self):  # pragma: no cover
        """Check for previous crash"""
        if Conf.main.faulthandler_log_available.get(
            False
        ) or Conf.main.traceback_log_available.get(False):
            txt = "<br>".join(
                [
                    _("Log files were generated during last session."),
                    "",
                    _("Do you want to see available log files?"),
                ]
            )
            btns = QW.QMessageBox.StandardButton.Yes | QW.QMessageBox.StandardButton.No
            choice = QW.QMessageBox.warning(self, APP_NAME, txt, btns)
            if choice == QW.QMessageBox.StandardButton.Yes:
                self.show_log_viewer()

    def __restore_pos_and_size(self):
        """Restore main window position and size from configuration"""
        maximized = Conf.main.window_maximized.get(None)
        if maximized:
            self.setWindowState(QC.Qt.WindowMaximized)
        pos = Conf.main.window_position.get(None)
        if pos is not None:
            posx, posy = pos
            self.move(QC.QPoint(posx, posy))
        size = Conf.main.window_size.get(None)
        if size is not None:
            width, height = size
            self.resize(QC.QSize(width, height))
        if pos is not None and size is not None:
            sgeo = self.screen().availableGeometry()
            out_inf = posx < -int(0.9 * width) or posy < -int(0.9 * height)
            out_sup = posx > int(0.9 * sgeo.width()) or posy > int(0.9 * sgeo.height())
            if len(QW.QApplication.screens()) == 1 and (out_inf or out_sup):
                #  Main window is offscreen
                posx = min(max(posx, 0), sgeo.width() - width)
                posy = min(max(posy, 0), sgeo.height() - height)
                self.move(QC.QPoint(posx, posy))

    def __save_pos_and_size(self):
        """Save main window position and size to configuration"""
        is_maximized = self.windowState() == QC.Qt.WindowMaximized
        Conf.main.window_maximized.set(is_maximized)
        if not is_maximized:
            size = self.size()
            Conf.main.window_size.set((size.width(), size.height()))
            pos = self.pos()
            Conf.main.window_position.set((pos.x(), pos.y()))

    def sizeHint(self):  # pylint: disable=C0103,R0201
        """Reimplement QWidget method"""
        return QC.QSize(1200, 600)

    def minimumSizeHint(self):  # pylint: disable=C0103,R0201
        """Reimplement QWidget method"""
        return QC.QSize(400, 200)

    def process_status_message(self, text, timeout):
        """Process status message"""
        lines = text.splitlines()
        if len(lines) > 1:
            text = lines[-1]
        self.statusBar().showMessage(text, timeout)

    def set_modified(self, state):
        """Set file modified state"""
        self._is_modified = state
        self.update_actions()
        self.update_title()

    def show_notimplemented_message(self):
        """Show not implemented error message"""
        QW.QMessageBox.critical(
            self,
            _("Error"),
            _(
                """This feature is not yet available.
Thanks for your patience."""
            ),
        )

    def update_title(self):
        """Update window title"""
        if self.filename is None:
            name = self.DEFAULT_NAME
        else:
            name = osp.basename(self.filename)
        if self._is_modified:
            name = name + "*"
        debugtxt = f" [DEBUG={DEBUG}]" if DEBUG else ""
        self.setWindowTitle(f"{APP_NAME}{debugtxt} - {name}")

    def create_actions(self):
        """Create actions"""
        self.separator_act = create_action(self, "")
        self.separator_act.setSeparator(True)

        self.xmlmode_act = create_action(
            self, _("Advanced XML mode"), toggled=self.switch_xml_mode
        )
        self.xmlmode_act.setChecked(Conf.main.xml_mode.get(False))

        self.new_act = create_action(
            self,
            _("&New"),
            shortcut="Ctrl+N",
            icon=get_icon("libre-gui-file.svg"),
            triggered=self.new_file,
        )
        self.open_act = create_action(
            self,
            _("&Open..."),
            shortcut="Ctrl+O",
            icon=get_icon("libre-gui-folder-open.svg"),
            triggered=self.open_file,
        )
        self.diropen_act = create_action(
            self,
            _("Open working directory"),
            icon=get_icon("libre-gui-folder.svg"),
            triggered=self.open_workdir,
        )
        self.save_act = create_action(
            self,
            _("&Save"),
            shortcut="Ctrl+S",
            icon=get_icon("libre-gui-save.svg"),
            triggered=self.save_file,
        )
        self.save_as_act = create_action(
            self,
            _("Save as..."),
            shortcut="Ctrl+Shift+S",
            triggered=self.save_as_file,
        )
        self.exit_act = create_action(
            self,
            _("Quit"),
            shortcut="Ctrl+Q",
            icon=get_icon("libre-gui-close.svg"),
            triggered=QW.QApplication.instance().closeAllWindows,
        )
        self.about_act = create_action(
            self,
            _("About..."),
            icon=get_icon("libre-gui-about.svg"),
            triggered=self.about,
        )

    def update_actions(self):
        """Update actions"""
        self.save_act.setEnabled(self._is_modified)

    def create_menus(self):
        """Create menus"""
        self.file_menu = self.menuBar().addMenu(_("&File"))
        self.open_recent_menu = QW.QMenu(_("Open recent file"))
        add_actions(
            self.file_menu,
            (
                self.new_act,
                self.open_act,
                self.diropen_act,
                self.open_recent_menu,
                None,
                self.save_act,
                self.save_as_act,
                None,
                self.xmlmode_act,
                None,
                self.exit_act,
            ),
        )
        self.file_menu.aboutToShow.connect(self.update_menu)
        actions = self.central_widget.editor.get_menu_actions()
        self.edit_menu = self.menuBar().addMenu(_("&Edit"))
        add_actions(self.edit_menu, actions["edit"])
        self.tasks_menu = self.menuBar().addMenu(_("&Tasks"))
        add_actions(self.tasks_menu, actions["tasks"])
        self.charts_menu = self.menuBar().addMenu(_("&Charts"))
        add_actions(self.charts_menu, actions["charts"])
        self.menuBar().addSeparator()
        help_menu = self.menuBar().addMenu("?")
        logv_act = create_action(
            self,
            _("Show log files..."),
            icon=get_icon("logs.svg"),
            triggered=self.show_log_viewer,
        )
        add_actions(
            help_menu,
            self.createPopupMenu().actions() + [None, logv_act, self.about_act],
        )

    def update_menu(self):
        """Update menu"""
        self.open_recent_menu.clear()
        actions = []
        self.check_recent_files()
        for fname in self.recent_files:
            action = create_action(
                self,
                osp.basename(fname),
                icon=get_icon("libre-gui-file.svg"),
                triggered=lambda fname=fname: self.open_file(fname),
            )
            actions.append(action)
        add_actions(self.open_recent_menu, actions)

    def create_toolbars(self):
        """Create toolbars"""
        main_toolbar = self.addToolBar(_("Main toolbar"))
        add_actions(
            main_toolbar,
            (
                self.new_act,
                self.open_act,
                None,
                self.save_act,
                None,
                self.diropen_act,
                None,
                self.about_act,
            ),
        )
        for toolbar in self.central_widget.get_toolbars():
            self.addToolBar(toolbar)

    def switch_xml_mode(self, state):
        """Switch to XML advanced mode"""
        if self.maybe_save(_("Switching mode")):
            if Conf.main.xml_mode.get(False) != state:
                Conf.main.xml_mode.set(state)
                self.central_widget.editor.switch_mode(self.filename)

    def maybe_save(self, title):
        """Eventually save file before continuing"""
        if self._is_modified:
            answer = QW.QMessageBox.warning(
                self,
                title,
                _("Do you want to save XML file before continuing?"),
                QW.QMessageBox.Yes | QW.QMessageBox.No | QW.QMessageBox.Cancel,
            )
            if answer == QW.QMessageBox.Yes:
                return self.save_file()
            if answer == QW.QMessageBox.Cancel:
                return False
            return True
        return True

    def new_file(self):
        """New file"""
        if not self.maybe_save(_("New file")):
            return False
        self.filename = None
        self.central_widget.new_file()
        return True

    @property
    def basedir(self):
        """Return current file base dir"""
        fname = self.filename
        if fname is None:
            if self._last_basedir is None:
                return DATAPATH
        else:
            self._last_basedir = osp.dirname(fname)
        return self._last_basedir

    @qth.qt_try_except()
    def open_file(self, fname=None):
        """Open file"""
        if not self.maybe_save(_("Open file")):
            return False
        if fname is None:
            fname, _selected_filter = getopenfilename(
                self, _("Open"), self.basedir, "*.xml"
            )
            if not fname:
                return False
        self.central_widget.load_file(fname)
        self.filename = fname
        self.add_to_recent_files(fname)
        self.set_modified(False)
        return True

    def open_workdir(self):
        """Open current work directory"""
        if self.filename:
            os.startfile(osp.normpath(osp.dirname(self.filename)))

    def check_recent_files(self):
        """Check if recent files still exist"""
        self.recent_files = [
            filename for filename in self.recent_files if osp.isfile(filename)
        ]

    def add_to_recent_files(self, fname):
        """Add to recent files"""
        if fname in self.recent_files:
            self.recent_files.pop(self.recent_files.index(fname))
        self.recent_files.insert(0, fname)
        while len(self.recent_files) > self.MAX_RECENT_FILES:
            self.recent_files.pop(-1)
        Conf.main.recent_files.set(self.recent_files)

    def __save(self, fname):
        """Save current file"""
        self.filename = fname
        self.add_to_recent_files(fname)
        try:
            self.central_widget.save_file(fname)
        except OSError:
            return False
        self.set_modified(False)
        return True

    def save_file(self):
        """Save file"""
        if self.filename is None:
            return self.save_as_file()
        return self.__save(self.filename)

    def save_as_file(self):
        """Save as file"""
        fname = self.filename
        if fname is None:
            fname = osp.join(self.basedir, self.DEFAULT_NAME)
        fname, _selected_filter = getsavefilename(
            self, _("Save as"), fname, filters="*.xml"
        )
        if not fname:
            return False
        return self.__save(fname)

    def about(self):
        """About dialog box"""
        QW.QMessageBox.about(
            self,
            _("About") + APP_NAME,
            f"""<b>{APP_NAME}</b> v{__version__}<br>{APP_DESC}
            <p>{_('Software created by')} Pierre Raybaut
            <br>Copyright &copy; 2022 CODRA
            <p>guidata {GUIDATA_VERSION_STR}
            <br>Python {platform.python_version()},
            Qt {QC.__version__} {_('under')} {platform.system()}
            <p><br><i>{_('How to enable debug mode?')}</i>
            <br>{_('Set the PLANNINGDEBUG environment variable to 1 or 2')}""",
        )

    def show_log_viewer(self):
        """Show error logs"""
        exec_logviewer_dialog(self)

    def closeEvent(self, event):  # pylint: disable=C0103
        """Reimplement QMainWindow method"""
        if self.maybe_save(_("Quit")):
            self.__save_pos_and_size()
            try:
                self.console.close()
            except RuntimeError:
                pass
            event.accept()
        else:
            event.ignore()
