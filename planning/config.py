# -*- coding: utf-8 -*-

"""
planning.config
---------------

The `config` module handles `planning` configuration.
"""

import os
import os.path as osp
import sys

from guidata import configtools

from planning.utils import conf

CONF_VERSION = "1.0.0"

APP_NAME = "PyPlanning"
MOD_NAME = "planning"

_ = configtools.get_translation(MOD_NAME)

configtools.add_image_module_path(MOD_NAME, "data")

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


DATAPATH = configtools.get_module_data_path(MOD_NAME, relpath="data")
TESTPATH = configtools.get_module_data_path(MOD_NAME, relpath="tests")


# Copyright (c) DataLab Platform Developers, BSD 3-Clause license.
# https://datalab-platform.com
def is_frozen(module_name: str) -> bool:
    """Test if module has been frozen (py2exe/cx_Freeze/pyinstaller)

    Args:
        module_name (str): module name

    Returns:
        bool: True if module has been frozen (py2exe/cx_Freeze/pyinstaller)
    """
    datapath = configtools.get_module_path(module_name)
    parentdir = osp.normpath(osp.join(datapath, osp.pardir))
    return not osp.isfile(__file__) or osp.isfile(parentdir)  # library.zip


IS_FROZEN = is_frozen(MOD_NAME)


# Copyright (c) DataLab Platform Developers, BSD 3-Clause license.
# https://datalab-platform.com
def get_mod_source_dir() -> str | None:
    """Return module source directory

    Returns:
        str | None: module source directory, or None if not found
    """
    if IS_FROZEN:
        devdir = osp.abspath(osp.join(sys.prefix, os.pardir, os.pardir))
    else:
        devdir = osp.abspath(osp.join(osp.dirname(__file__), os.pardir))
    if osp.isfile(osp.join(devdir, MOD_NAME, "__init__.py")):
        return devdir
    # Unhandled case (this should not happen, but just in case):
    return None


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


class ConsoleSection(conf.Section, metaclass=conf.SectionMeta):
    """Classs defining the console configuration section structure.
    Each class attribute is an option (metaclass is automatically affecting
    option names in .INI file based on class attribute names)."""

    console_enabled = conf.Option()
    max_line_count = conf.Option()
    external_editor_path = conf.Option()
    external_editor_args = conf.Option()


# Usage (example): Conf.console.enable.get(True)
class Conf(conf.Configuration, metaclass=conf.ConfMeta):
    """Class defining CodraFT configuration structure.
    Each class attribute is a section (metaclass is automatically affecting
    section names in .INI file based on class attribute names)."""

    main = MainSection()
    tree = TreeSection()
    console = ConsoleSection()


def get_old_log_fname(fname):
    """Return old log fname from current log fname"""
    return osp.splitext(fname)[0] + ".1.log"


def initialize():
    """Initialize application configuration"""
    Conf.initialize(APP_NAME, CONF_VERSION, load=not DEBUG)
    Conf.main.traceback_log_path.get(f".{APP_NAME}_traceback.log")
    Conf.main.faulthandler_log_path.get(f".{APP_NAME}_faulthandler.log")
    Conf.console.console_enabled.get(True)
    Conf.console.external_editor_path.get("code")
    Conf.console.external_editor_args.get("-g {path}:{line_number}")


def reset():
    """Reset application configuration"""
    Conf.reset()
    initialize()


initialize()
