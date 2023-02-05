# -*- coding: utf-8 -*-

"""
planning.config
---------------

The `config` module handles `planning` configuration.
"""

import os

from guidata import configtools
from guidata.userconfig import UserConfig

_ = configtools.get_translation("planning")

configtools.add_image_module_path("planning", "data")

APP_NAME = _("PyPlanning")
APP_DESC = _(
    """Manage team schedules and quickly create simple project plannings.
"""
)

DEBUG = len(os.environ.get("PLANNINGDEBUG", "")) > 0

MAIN_FONT_FAMILY = "Yu Gothic UI"  # "Bahnschrift Light"

DEFAULTS = {
    "main": {
        "normal/font/family": [MAIN_FONT_FAMILY, "Verdana"],
        "normal/font/size": 11,
        "small/font/family": [MAIN_FONT_FAMILY, "Verdana"],
        "small/font/size": 10,
    },
}
DEFAULTS = {}
CONF = UserConfig(DEFAULTS)
CONF.set_application(APP_NAME, "1.0.0", load=not DEBUG)

DATAPATH = configtools.get_module_data_path("planning", relpath="data")
TESTPATH = configtools.get_module_data_path("planning", relpath="tests")
