# -*- coding: utf-8 -*-
#
# Licensed under the terms of the BSD 3-Clause or the CeCILL-B License
# (see codraft/__init__.py for details)

"""
PyPlanning Configuration utilities

Based on CodraFT's module codraft/utils/conf.py
"""

import os
import os.path as osp

from guidata.configtools import get_font
from guidata.userconfig import NoDefault, UserConfig, get_config_dir

CONF = UserConfig({})


class Configuration:
    """Configuration file"""

    @classmethod
    def initialize(cls, name, version, load):
        """Initialize configuration"""
        CONF.set_application(name, version, load=load)

    @classmethod
    def reset(cls):
        """Reset configuration"""
        global CONF  # pylint: disable=global-statement
        CONF.cleanup()  # Remove configuration file
        CONF = UserConfig({})


class Section:
    """Configuration section"""

    @classmethod
    def set_name(cls, section):
        """Set section name"""
        cls._name = section

    @classmethod
    def get_name(cls):
        """Return section name"""
        return cls._name


class Option:
    """Configuration option handler"""

    def __init__(self):
        self.section = None
        self.option = None

    def get(self, default=NoDefault):
        """Get configuration option value"""
        return CONF.get(self.section, self.option, default)

    def set(self, value):
        """Set configuration option value"""
        CONF.set(self.section, self.option, value)

    def reset(self):
        """Reset configuration option"""
        CONF.remove_option(self.section, self.option)


class ConfigPathOption(Option):
    """Configuration file path configuration option handler"""

    def get(self, default=NoDefault):
        """Get configuration file path from configuration"""
        if default is NoDefault:
            default = ""
        fname = super().get(default)
        if osp.basename(fname) != fname:
            raise ValueError("Invalid configuration file name {fname}")
        return osp.join(get_config_dir(), osp.basename(fname))


class WorkingDirOption(Option):
    """Working directory configuration option handler"""

    def get(self, default=NoDefault):
        """Get working directory from configuration"""
        if default is NoDefault:
            default = ""
        path = super().get(default)
        if osp.isdir(path):
            return path
        return ""

    def set(self, value):
        """Set working directory in configuration"""
        if not osp.isdir(value):
            value = osp.dirname(value)
            if not osp.isdir(value):
                raise FileNotFoundError(f"Invalid working directory name {value}")
        os.chdir(value)
        super().set(value)


class RecentFilesOption(Option):
    """Recent files configuration option handler"""

    @staticmethod
    def __filter_filenames(filenames):
        """Remove invalid filenames from recent files"""
        return [fname for fname in filenames if osp.exists(fname)]

    def get(self, default=NoDefault):
        """Get recent files from configuration"""
        if default is NoDefault:
            default = []
        return self.__filter_filenames(super().get(default))

    def set(self, value):
        """Set recent files in configuration"""
        super().set(self.__filter_filenames(value))


class FontOption(Option):
    """Font configuration option handler"""

    def get(self, default=NoDefault):
        """Get font from configuration"""
        return get_font(CONF, self.section, self.option)

    def set(self, value: dict):
        """Set font in configuration"""
        for key, val in value:
            CONF.set(self.section, self.option + "/font/" + key, val)


class SectionMeta(type):
    """Configuration metaclass"""

    def __new__(cls, name, bases, dct):
        optlist = []
        for attrname, obj in list(dct.items()):
            if isinstance(obj, Option):
                obj.option = attrname
                optlist.append(obj)
        dct["_options"] = optlist
        return type.__new__(cls, name, bases, dct)


class ConfMeta(type):
    """Configuration metaclass"""

    def __new__(cls, name, bases, dct):
        for attrname, obj in list(dct.items()):
            if isinstance(obj, Section):
                obj.set_name(attrname)
                for option in obj._options:
                    option.section = attrname
        return type.__new__(cls, name, bases, dct)
