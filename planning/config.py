# -*- coding: utf-8 -*-

"""
planning.config
---------------

The `config` module handles `planning` configuration.
"""

import os
import os.path as osp

from guidata import configtools

from planning.utils import conf

_ = configtools.get_translation("planning")

configtools.add_image_module_path("planning", "data")

CONF_VERSION = "1.0.0"
APP_NAME = _("PyPlanning")
APP_DESC = _(
    """Manage team schedules and quickly create simple project plannings.
"""
)

DEBUG_VAR_STR = "PLANNINGDEBUG"
try:
    DEBUG = int(os.environ.get(DEBUG_VAR_STR, ""))
except ValueError:
    DEBUG = 1 if len(os.environ.get(DEBUG_VAR_STR, "")) > 0 else 0

MAIN_FONT_FAMILY = "Yu Gothic UI"  # "Bahnschrift Light"
DATETIME_FORMAT = "%d/%m/%Y - %H:%M:%S"


DATAPATH = configtools.get_module_data_path("planning", relpath="data")
TESTPATH = configtools.get_module_data_path("planning", relpath="tests")


class MainSection(conf.Section, metaclass=conf.SectionMeta):
    """Class defining the main configuration section structure.
    Each class attribute is an option (metaclass is automatically affecting
    option names in .INI file based on class attribute names)."""

    traceback_log_path = conf.ConfigPathOption()
    traceback_log_available = conf.Option()
    faulthandler_enabled = conf.Option()
    faulthandler_log_path = conf.ConfigPathOption()
    faulthandler_log_available = conf.Option()
    window_maximized = conf.Option()
    window_position = conf.Option()
    window_size = conf.Option()
    base_dir = conf.WorkingDirOption()
    recent_files = conf.RecentFilesOption()
    xml_mode = conf.Option()


class TreeSection(conf.Section, metaclass=conf.SectionMeta):
    """Class defining the tree widget configuration section structure.
    Each class attribute is an option (metaclass is automatically affecting
    option names in .INI file based on class attribute names)."""

    normal = conf.FontOption()
    small = conf.FontOption()


# Usage (example): Conf.console.enable.get(True)
class Conf(conf.Configuration, metaclass=conf.ConfMeta):
    """Class defining CodraFT configuration structure.
    Each class attribute is a section (metaclass is automatically affecting
    section names in .INI file based on class attribute names)."""

    main = MainSection()
    tree = TreeSection()


def get_old_log_fname(fname):
    """Return old log fname from current log fname"""
    return osp.splitext(fname)[0] + ".1.log"


def initialize():
    """Initialize application configuration"""
    Conf.initialize(APP_NAME, CONF_VERSION, load=not DEBUG)
    Conf.main.traceback_log_path.set(f".{APP_NAME}_traceback.log")
    Conf.main.faulthandler_log_path.set(f".{APP_NAME}_faulthandler.log")


def reset():
    """Reset application configuration"""
    Conf.reset()
    initialize()


initialize()
