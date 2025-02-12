#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# pylint: skip-file

"""
gantt.py - version and date, see below

This is a python class to create gantt chart using SVG


Author : Alexandre Norman - norman at xael.org

Contributors:

* Sébastien NOBILI - pipoprods at free.fr


Licence : GPL v3 or any later version


This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""

__author__ = "Alexandre Norman (norman at xael.org)"
__version__ = "0.7.0"
__last_modification__ = "2016.03.20"

import calendar
import codecs
import datetime
import enum
import logging
import re
import sys
import textwrap
import types
from typing import Optional

import svgwrite
from dateutil.relativedelta import relativedelta

# conversion from mm/cm to pixel is done by ourselve as firefox seems
# to have a bug for big numbers...
# 3.543307 is for conversion from mm to pt units !
mm = 3.543307
cm = 35.43307
px_to_mm = 0.264583
px_to_cm = 0.0264583


class COLORS(enum.Enum):
    YEARS = "#9b9b9b"
    VACATIONS = "#999999"
    MILESTONES = "#FF3030"
    PROJECTS = "#9c9ea0"
    TODAY = "#76e9ff"
    START_END_DATES = "#9b9b9b"

class TYPE(enum.Enum):
    RESOURCE = "resource"
    TASK = "task"


class _my_svgwrite_drawing_wrapper(svgwrite.Drawing):
    """
    Hack for beeing able to use a file descriptor as filename
    """

    def save(self, width="100%", height="100%"):
        """Write the XML string to **filename**."""
        test = False
        import io

        # Fix height and width
        self["height"] = height
        self["width"] = width

        if sys.version_info[0] == 2:
            test = (
                type(self.filename) == types.FileType
                or type(self.filename) == types.InstanceType
            )
        elif sys.version_info[0] == 3:
            test = type(self.filename) == io.TextIOWrapper

        if test:
            self.write(self.filename)
        else:
            fileobj = io.open(str(self.filename), mode="w", encoding="utf-8")
            self.write(fileobj)
            fileobj.close()


############################################################################


class LoggingHelper:
    """Logging helper"""

    def __init__(self):
        self._logger = None

    def initialize(self, level=logging.INFO, stream=sys.stdout):
        """Initialize"""
        if sys.stdout is None:
            # pythonw.exe
            return
        self._logger = logging.getLogger("Gantt")
        self._logger.setLevel(level)
        fh = logging.StreamHandler(stream=stream)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        fh.setFormatter(formatter)
        self._logger.addHandler(fh)
        self._logger = logging.getLogger("Gantt")

    def close(self):
        """Close"""
        if self._logger is not None:
            handlers = self._logger.handlers[:]
            for handler in handlers:
                handler.setStream(None)
                handler.close()
                self._logger.removeHandler(handler)

    def debug(self, message):
        """Debug"""
        if self._logger is not None:
            self._logger.debug(message)

    def warning(self, message):
        """Warning"""
        if self._logger is not None:
            self._logger.warning(message)

    def error(self, message):
        """Error"""
        if self._logger is not None:
            self._logger.error(message)

    def critical(self, message):
        """Critical"""
        if self._logger is not None:
            self._logger.critical(message)


LOG = LoggingHelper()


############################################################################

DRAW_WITH_DAILY_SCALE = "d"
DRAW_WITH_WEEKLY_SCALE = "w"
DRAW_WITH_MONTHLY_SCALE = "m"
DRAW_WITH_QUATERLY_SCALE = "q"

############################################################################

# Unworked days (0: Monday ... 6: Sunday)
NOT_WORKED_DAYS = [5, 6]


def define_not_worked_days(list_of_days):
    """
    Define specific days off

    Keyword arguments:
    list_of_days -- list of integer (0: Monday ... 6: Sunday) - default [5, 6]
    """
    global NOT_WORKED_DAYS
    NOT_WORKED_DAYS = list_of_days
    return


def _not_worked_days():
    """
    Returns list of days off (0: Monday ... 6: Sunday)
    """
    global NOT_WORKED_DAYS
    return NOT_WORKED_DAYS


############################################################################

FONT_ATTR = {
    "fill": "black",
    "stroke": "black",
    "stroke_width": 0,
    "font_family": "Verdana",
    "font_size": 15,
}


def define_font_attributes(
    fill="black", stroke="black", stroke_width=0, font_family="Verdana"
):
    """
    Define font attributes

    Keyword arguments:
    fill -- fill - default 'black'
    stroke -- stroke - default 'black'
    stroke_width -- stroke width - default 0
    font_family -- font family - default 'Verdana'
    """
    global FONT_ATTR

    FONT_ATTR = {
        "fill": fill,
        "stroke": stroke,
        "stroke_width": stroke_width,
        "font_family": font_family,
    }

    return


def _font_attributes():
    """
    Return dictionnary of font attributes
    Example :
    FONT_ATTR = {
      'fill': 'black',
      'stroke': 'black',
      'stroke_width': 0,
      'font_family': 'Verdana',
    }
    """
    global FONT_ATTR
    return FONT_ATTR


############################################################################


# list of vacations as datetime (non worked days)
VACATIONS = []


############################################################################


def add_vacations(start_date, end_date=None):
    """
    Add vacations to a resource begining at [start_date] to [end_date]
    (included). If [end_date] is not defined, vacation will be for [start_date]
    day only

    Keyword arguments:
    start_date -- datetime.date begining of vacation
    end_date -- datetime.date end of vacation of vacation
    """
    LOG.debug(
        "** add_vacations {0}".format({"start_date": start_date, "end_date": end_date})
    )

    global VACATIONS

    if end_date is None:
        if start_date not in VACATIONS:
            VACATIONS.append(start_date)
    else:
        while start_date <= end_date:
            if start_date not in VACATIONS:
                VACATIONS.append(start_date)

            start_date += datetime.timedelta(days=1)

    LOG.debug(
        "** add_vacations {0}".format(
            {"start_date": start_date, "end_date": end_date, "vac": VACATIONS}
        )
    )

    return


############################################################################


def _show_version(name, **kwargs):
    """
    Show version
    """
    import os

    print("{0} version {1}".format(os.path.basename(name), __version__))
    return True


############################################################################


def _flatten(l, ltypes=(list, tuple)):
    """
    Return a flatten list from a list like [1,2,[4,5,1]]
    """
    ltype = type(l)
    l = list(l)
    i = 0
    while i < len(l):
        while isinstance(l[i], ltypes):
            if not l[i]:
                l.pop(i)
                i -= 1
                break
            else:
                l[i : i + 1] = l[i]
        i += 1
    return ltype(l)


############################################################################
class GroupOfResources(object):
    """
    Class for grouping resources
    """

    def __init__(self, name, fullname=None):
        """
        Init a group of resource resource

        Keyword arguments:
        name -- name given to the resource (id)
        fullname -- long name given to the resource
        """
        LOG.debug("** GroupOfResources::__init__ {0}".format({"name": name}))
        self.name = name
        self.vacations = []
        if fullname is not None:
            self.fullname = fullname
        else:
            self.fullname = name

        self.resources = []

        self.tasks = []
        return

    def add_resource(self, resource):
        """
        Add a resource to the group of resources

        Keyword arguments:
        resource -- Resource object
        """
        if resource not in self.resources:
            self.resources.append(resource)
            resource.add_group(self)
        return

    def add_vacations(self, dfrom, dto=None):
        """
        Add vacations to a resource begining at [dfrom] to [dto] (included). If
        [dto] is not defined, vacation will be for [dfrom] day only

        Keyword arguments:
        dfrom -- datetime.date begining of vacation
        dto -- datetime.date end of vacation of vacation
        """
        LOG.debug(
            "** Resource::add_vacations {0}".format(
                {"name": self.name, "dfrom": dfrom, "dto": dto}
            )
        )
        if dto is None:
            self.vacations.append((dfrom, dfrom))
        else:
            self.vacations.append((dfrom, dto))
        return

    def nb_elements(self):
        """
        Returns the number of resources
        """
        LOG.debug("** GroupOfResources::nb_elements ({0})".format({"name": self.name}))
        return len(self.resources)

    def is_available(self, date):
        """
        Returns True if any resource is available at given date, False if not.
        Availibility is taken from the global VACATIONS and resource's ones.

        Keyword arguments:
        date -- datetime.date day to look for
        """
        # Global VACATIONS
        if date in VACATIONS:
            LOG.debug(
                "** GroupOfResources::is_available {0} : False (global vacation)".format(
                    {"name": self.name, "date": date}
                )
            )
            return False

        # Group vacations
        for h in self.vacations:
            dfrom, dto = h
            if date >= dfrom and date <= dto:
                LOG.debug(
                    "** GroupOfResources::is_available {0} : False (group vacation)".format(
                        {"name": self.name, "date": date}
                    )
                )
                return False

        # Test if at least one resource is avalaible
        for r in self.resources:
            if r.is_available(date):
                LOG.debug(
                    "** GroupOfResources::is_available {0} : True {1}".format(
                        {"name": self.name, "date": date}, r.name
                    )
                )
                return True

        LOG.debug(
            "** GroupOfResources::is_available {0} : False".format(
                {"name": self.name, "date": date}
            )
        )
        return False

    def add_task(self, task):
        """
        Tell the resource that we have assigned a task

        Keyword arguments:
        task -- Task object
        """
        if task not in self.tasks:
            self.tasks.append(task)
        return

    def search_for_task_conflicts(self, all_tasks=False):
        """
        Returns a dictionnary of all days (datetime.date) containing for each
        overcharged day the list of task for this day.

        It examines all resources member and group tasks.

        Keyword arguments:
        all_tasks -- if True return all tasks for all days, not just overcharged days
        """
        # Get for each resource
        affected_days = {}
        for r in self.resources:
            ad = r.search_for_task_conflicts(all_tasks=True)
            for d in ad:
                try:
                    affected_days[d].append(ad[d])
                except KeyError:
                    affected_days[d] = [ad[d]]

        # inspect project
        for t in self.tasks:
            cday = t.start_date()
            while cday <= t.end_date():
                if cday.weekday() not in _not_worked_days():
                    try:
                        affected_days[cday].append(t.fullname)
                    except KeyError:
                        affected_days[cday] = [t.fullname]

                cday += datetime.timedelta(days=1)

        # compile everything
        overcharged_days = {}
        ke = list(affected_days.keys())
        ke.sort()
        for d in ke:
            affected_days[d] = _flatten(affected_days[d])
            if all_tasks:
                overcharged_days[d] = affected_days[d]

            elif len(affected_days[d]) > self.nb_elements():
                overcharged_days[d] = affected_days[d]
                LOG.warning(
                    '** GroupOfResources "{2}" has more than {3} tasks on day {0} / {1}'.format(
                        d, affected_days[d], self.name, self.nb_elements()
                    )
                )

        return overcharged_days

    def is_vacant(self, from_date, to_date):
        """
        Check if any resource from the group is unallocated between for a given timeframe.
        Returns a list of available ressource name.

        Keyword arguments:
        from_date -- first day
        to_date --  last day
        """
        availables = []
        for r in self.resources:
            if len(r.is_vacant(from_date, to_date)) > 0:
                availables.append(r.name)

        return availables


############################################################################


class Resource(object):
    """
    Class for handling resources assigned to tasks
    """

    def __init__(self, name, fullname=None, color=None):
        """
        Init a resource

        Keyword arguments:
        name -- name given to the resource (id)
        fullname -- long name given to the resource
        color -- string, html color, default None
        """
        LOG.debug("** Resource::__init__ {0}".format({"name": name}))
        self.name = name
        if fullname is not None:
            self.fullname = fullname
        else:
            self.fullname = name
        self.color = color

        self.vacations = []
        self.member_of_groups = []

        self.tasks = []
        return

    def add_vacations(self, dfrom, dto=None):
        """
        Add vacations to a resource begining at [dfrom] to [dto] (included). If
        [dto] is not defined, vacation will be for [dfrom] day only

        Keyword arguments:
        dfrom -- datetime.date begining of vacation
        dto -- datetime.date end of vacation of vacation
        """
        LOG.debug(
            "** Resource::add_vacations {0}".format(
                {"name": self.name, "dfrom": dfrom, "dto": dto}
            )
        )
        if dto is None:
            self.vacations.append((dfrom, dfrom))
        else:
            self.vacations.append((dfrom, dto))
        return

    def nb_elements(self):
        """
        Returns the number of resources, 1 here
        """
        LOG.debug("** Resource::nb_elements ({0})".format({"name": self.name}))
        return 1

    def is_available(self, date):
        """
        Returns True if the resource is available at given date, False if not.
        Availibility is taken from the global VACATIONS and resource's ones.

        Keyword arguments:
        date -- datetime.date day to look for
        """
        # global VACATIONS
        if date in VACATIONS:
            LOG.debug(
                "** Resource::is_available {0} : False (global vacation)".format(
                    {"name": self.name, "date": date}
                )
            )
            return False

        # GroupOfResources vacation
        for g in self.member_of_groups:
            for h in g.vacations:
                dfrom, dto = h
                if date >= dfrom and date <= dto:
                    LOG.debug(
                        "** Resource::is_available {0} : False (Group {1})".format(
                            {"name": self.name, "date": date}, g.name
                        )
                    )
                    return False

        # Resource vacation
        for h in self.vacations:
            dfrom, dto = h
            if date >= dfrom and date <= dto:
                LOG.debug(
                    "** Resource::is_available {0} : False".format(
                        {"name": self.name, "date": date}
                    )
                )
                return False
        LOG.debug(
            "** Resource::is_available {0} : True".format(
                {"name": self.name, "date": date}
            )
        )
        return True

    def add_group(self, groupofresources):
        """
        Tell the resource it belongs to a GroupOfResources

        Keyword arguments:
        groupofresources -- GroupOfResources
        """
        if groupofresources not in self.member_of_groups:
            self.member_of_groups.append(groupofresources)
        return

    def add_task(self, task):
        """
        Tell the resource that we have assigned a task

        Keyword arguments:
        task -- Task object
        """
        if task not in self.tasks:
            self.tasks.append(task)
        return

    def search_for_task_conflicts(self, all_tasks=False):
        """
        Returns a dictionnary of all days (datetime.date) containing for each
        overcharged day the list of task for this day.

        Keyword arguments:
        all_tasks -- if True return all tasks for all days, not just overcharged days
        """
        affected_days = {}
        for t in self.tasks:
            cday = t.start_date()
            while cday <= t.end_date():
                if cday.weekday() not in _not_worked_days():
                    try:
                        affected_days[cday].append(t.fullname)
                    except KeyError:
                        affected_days[cday] = [t.fullname]

                cday += datetime.timedelta(days=1)

        # return all
        if all_tasks:
            return affected_days

        # compile only overcharge
        overcharged_days = {}
        ke = list(affected_days.keys())
        ke.sort()
        for d in ke:
            if len(affected_days[d]) > 1:
                overcharged_days[d] = affected_days[d]
                LOG.warning(
                    '** Resource "{2}" has more than one task on day {0} / {1}'.format(
                        d, affected_days[d], self.name
                    )
                )

        return overcharged_days

    def is_vacant(self, from_date, to_date):
        """
        Check if the resource is unallocated between for a given timeframe.
        Returns True if the resource is free, False otherwise

        Keyword arguments:
        from_date -- first day
        to_date --  last day
        """
        non_vacant_days = self.search_for_task_conflicts(all_tasks=True)
        cday = from_date
        while cday <= to_date:
            if cday.weekday() not in _not_worked_days():
                if not self.is_available(cday):
                    LOG.debug(
                        '** Ressource "{0}" is not available on day {1} (vacation)'.format(
                            self.name, cday
                        )
                    )
                    return []
                if cday in non_vacant_days:
                    LOG.debug(
                        '** Ressource "{0}" is not available on day {1} (other task : {2})'.format(
                            self.name, cday, non_vacant_days[cday]
                        )
                    )
                    return []

            cday += datetime.timedelta(days=1)
        return [self.name]


############################################################################


def _get_maxx(scale, start_date, end_date):
    if scale == DRAW_WITH_DAILY_SCALE:
        # how many dayss do we need to draw ?
        maxx = (end_date - start_date).days
    elif scale == DRAW_WITH_WEEKLY_SCALE:
        # how many weeks do we need to draw ?
        maxx = 0
        guess = start_date
        while guess.weekday() != 0:
            guess = guess + relativedelta(days=-1)
        while end_date.weekday() != 6:
            end_date = end_date + relativedelta(days=+1)
        while guess <= end_date:
            maxx += 1
            guess = guess + relativedelta(weeks=+1)
        maxx -= 1
    elif scale == DRAW_WITH_MONTHLY_SCALE:
        # how many months do we need to draw ?
        delta = relativedelta(end_date + datetime.timedelta(days=1), start_date)
        maxx = delta.months + delta.years * 12 - 1
        if delta.days > 0:
            maxx += 1
    elif scale == DRAW_WITH_QUATERLY_SCALE:
        # how many quarter do we need to draw ?
        message = "DRAW_WITH_QUATERLY_SCALE not implemented yet"
        LOG.critical(message)
        raise ValueError(message)
    return maxx


def _time_diff(
    scale, start_date, end_date, duration, milestone=False, tu_fraction=False
) -> int | float:
    """Return time difference, depending on scale.
    If duration is True, this computes the duration of the task, else it computes
    the instant of start of the task which is the time difference between start_date
    (the beginning of the project) and end_date (the beginning of the task)"""

    if scale == DRAW_WITH_DAILY_SCALE:

        return (end_date - start_date).days

    if scale == DRAW_WITH_WEEKLY_SCALE:

        orig_end_date = end_date
        longer_than_week = (orig_end_date - start_date).days > 7
        td = 0
        guess = start_date

        while guess.weekday() != 0:
            guess = guess + relativedelta(days=-1)

        if duration:
            while end_date.weekday() != 0:
                end_date = end_date + relativedelta(days=-1)
        else:
            while end_date.weekday() != 6:
                end_date = end_date + relativedelta(days=+1)

        while guess + relativedelta(days=+6) < end_date:
            td += 1
            guess += relativedelta(weeks=+1)

        if milestone:
            return td - 1

        if tu_fraction:
            if longer_than_week:
                return (
                    td
                    + round(orig_end_date.weekday() / 7.0, 2)
                    - (1 if duration else 0)
                )
            else:
                return round((orig_end_date - start_date).days / 7.0, 2)

        return td

    if scale == DRAW_WITH_MONTHLY_SCALE:

        if not duration:
            start_date = start_date.replace(day=1)
        rdelta = relativedelta(end_date, start_date)
        return rdelta.months + rdelta.years * 12

    raise ValueError(f"Could not compute a time difference.")


class Task(object):
    """
    Class for manipulating Tasks
    """

    def __init__(
        self,
        name,
        start=None,
        stop=None,
        duration=None,
        depends_on=None,
        resources=None,
        percent_done=0,
        color=None,
        fullname=None,
        display=True,
        state="",
        is_project=False,
        project=None
    ):
        """
        Initialize task object. Two of start, stop or duration may be given.
        This task can rely on other task and will be completed with resources.
        If percent done is given, a progress bar will be included on the task.
        If color is specified, it will be used for the task.

        Keyword arguments:
        name -- name of the task (id)
        fullname -- long name given to the resource
        start -- datetime.date, first day of the task, default None
        stop -- datetime.date, last day of the task, default None
        duration -- int, duration of the task, default None
        depends_on -- list of Task which are parents of this one, default None
        resources -- list of Resources assigned to the task, default None
        percent_done -- int, percent of achievment, default 0
        color -- string, html color, default None
        display -- boolean, display this task, default True
        state -- string, state of the task
        is_project -- boolean, disable check on beginning and end dates
        project -- name of the project associated to the task
        """
        LOG.debug(
            "** Task::__init__ {0}".format(
                {
                    "name": name,
                    "start": start,
                    "stop": stop,
                    "duration": duration,
                    "depends_on": depends_on,
                    "resources": resources,
                    "percent_done": percent_done,
                    "project": project
                }
            )
        )
        self.name = name
        if fullname is not None:
            self.fullname = fullname
        else:
            self.fullname = name

        self.start = start
        self.stop = stop
        self.duration = duration
        self.color = color
        self.display = display
        self.state = state
        self.project = project

        ends = (self.start, self.stop, self.duration)
        nonecount = 0
        for e in ends:
            if e is None:
                nonecount += 1

        # check limits (2 must be set on 4) or scheduling is defined by duration and dependencies
        if (not is_project) and (nonecount != 1) and (self.duration is None or depends_on is None):
            LOG.error(
                '** Task "{1}" must be defined by two of three limits ({0})'.format(
                    {"start": self.start, "stop": self.stop, "duration": self.duration},
                    self.fullname,
                )
            )
            # Bug ? may be defined later
            # raise ValueError('Task "{1}" must be defined by two of three limits ({0})'.format({'start':self.start, 'stop':self.stop, 'duration':self.duration}, fullname))

        if type(depends_on) is type([]):
            self.depends_on = depends_on
        elif depends_on is not None:
            self.depends_on = [depends_on]
        else:
            self.depends_on = None

        self.resources = resources
        self.percent_done = percent_done
        self.drawn_x_begin_coord = None
        self.drawn_x_end_coord = None
        self.drawn_y_coord = None
        self._cache_start_date = None
        self._cache_end_date = None

        # tell each resource we have
        # assigned a new task
        if resources is not None:
            for r in resources:
                r.add_task(self)


    def add_depends(self, depends_on):
        """
        Adds dependency to a task

        Keyword arguments:
        depends_on -- list of Task which are parents of this one
        """
        if isinstance(depends_on, list):
            if self.depends_on is None:
                self.depends_on = depends_on
            else:
                self.depends_on.extend(depends_on)
        else:
            if self.depends_on is None:
                self.depends_on = depends_on
            else:
                self.depends_on.append(depends_on)

        # Adapt task start date if before end of dependencies
        if len(self.depends_on) > 0:
            min_start_date = self.depends_on[0].end_date()
            for dep in self.depends_on:
                if dep.end_date() is not None and dep.end_date() < min_start_date:
                    min_start_date = dep.end_date()
            if min_start_date is not None and (
                self.start is None or self.start < min_start_date
            ):
                self.start = min_start_date

        return

    def start_date(self):
        """
        Returns the first day of the task, either the one which was given at
        task creation or the one calculated after checking dependencies
        """
        if self._cache_start_date is not None:
            return self._cache_start_date

        LOG.debug("** Task::start_date ({0})".format(self.name))
        if self.start is not None:
            # start date setted, calculate begining
            if self.depends_on is None:
                # depends on nothing... start date is start
                # LOG.debug('*** Do not depend of other task')
                start = self.start
                while self.non_working_day(start):
                    start = start + datetime.timedelta(days=1)

                if start > self.start:
                    LOG.warning(
                        '** Due to vacations, Task "{0}", will not start on date {1} but {2}'.format(
                            self.fullname, self.start, start
                        )
                    )

                self._cache_start_date = start
                return self._cache_start_date
            else:
                # depends on other task, start date could vary
                # LOG.debug('*** Do depend of other tasks')
                start = self.start
                while self.non_working_day(start):
                    start = start + datetime.timedelta(days=1)

                prev_task_end = start
                for t in self.depends_on:
                    if isinstance(t, Milestone):
                        if t.end_date() >= prev_task_end:
                            prev_task_end = t.end_date()
                    elif isinstance(t, Task):
                        if t.end_date() >= prev_task_end:
                            prev_task_end = t.end_date() + datetime.timedelta(days=1)

                while self.non_working_day(prev_task_end):
                    prev_task_end = prev_task_end + datetime.timedelta(days=1)

                if prev_task_end > self.start:
                    LOG.warning(
                        '** Due to dependencies, Task "{0}", will not start on date {1} but {2}'.format(
                            self.fullname, self.start, prev_task_end
                        )
                    )

                self._cache_start_date = prev_task_end
                return self._cache_start_date

        elif self.duration is None:  # start and stop fixed
            current_day = self.start
            # check depends
            if self.depends_on is not None:
                prev_task_end = self.depends_on[0].end_date()
                for t in self.depends_on:
                    if isinstance(t, Milestone):
                        if t.end_date() > prev_task_end:
                            prev_task_end = t.end_date() - datetime.timedelta(days=1)
                    elif isinstance(t, Task):
                        if t.end_date() > prev_task_end:
                            prev_task_end = t.end_date()
                    # if t.end_date() > prev_task_end:
                    #     #LOG.debug('*** latest one {0} which end on {1}'.format(t.name, t.end_date()))
                    #     prev_task_end = t.end_date()
                if prev_task_end > current_day:
                    depend_start_date = prev_task_end
                else:
                    start = self.start
                    while self.non_working_day(start):
                        start = start + datetime.timedelta(days=1)
                    depend_start_date = start

                    if depend_start_date > current_day:
                        LOG.error(
                            '** Due to dependencies, Task "{0}", could not be finished on time (should start as last on {1} but will start on {2})'.format(
                                self.fullname, current_day, depend_start_date
                            )
                        )
                    self._cache_start_date = depend_start_date
            else:
                # should be first day of start...
                self._cache_start_date = current_day

            return self._cache_start_date

        elif (
            self.duration is not None
            and self.depends_on is not None
            and self.stop is None
        ):  # duration and dependencies fixed
            prev_task_end = None
            for t in self.depends_on:
                if isinstance(t, Milestone):
                    if prev_task_end is None or t.end_date() > prev_task_end:
                        prev_task_end = t.end_date() - datetime.timedelta(days=1)
                elif isinstance(t, Task):
                    if prev_task_end is None or t.end_date() > prev_task_end:
                        prev_task_end = t.end_date()
                # if t.end_date() > prev_task_end:
                #     LOG.debug('*** latest one {0} which end on {1}'.format(t.name, t.end_date()))
                #     prev_task_end = t.end_date()
            if prev_task_end:
                start = prev_task_end + datetime.timedelta(days=1)

            while self.non_working_day(start):
                start = start + datetime.timedelta(days=1)

            # should be first day of start...
            self._cache_start_date = start

        elif self.start is None and self.stop is not None:  # stop and duration fixed
            # start date not setted, calculate from end_date + depends
            current_day = self.stop
            real_duration = 0
            duration = self.duration
            while duration > 0:
                if not self.non_working_day(current_day):
                    real_duration = real_duration + 1
                    duration -= 1
                else:
                    real_duration = real_duration + 1

                current_day = self.stop - datetime.timedelta(days=real_duration)
            current_day = self.stop - datetime.timedelta(days=real_duration - 1)

            # check depends
            if self.depends_on is not None:
                prev_task_end = self.depends_on[0].end_date()
                for t in self.depends_on:
                    if isinstance(t, Milestone):
                        if t.end_date() > prev_task_end:
                            prev_task_end = t.end_date()
                    elif isinstance(t, Task):
                        if t.end_date() > prev_task_end:
                            prev_task_end = t.end_date()
                    # if t.end_date() > prev_task_end:
                    #     LOG.debug('*** latest one {0} which end on {1}'.format(t.name, t.end_date()))
                    #     prev_task_end = t.end_date()

                if prev_task_end > current_day:
                    start = prev_task_end + datetime.timedelta(days=1)
                    # return prev_task_end
                else:
                    start = current_day

                while self.non_working_day(start):
                    start = start + datetime.timedelta(days=1)

                depend_start_date = start

                if depend_start_date > current_day:
                    LOG.error(
                        '** Due to dependencies, Task "{0}", could not be finished on time (should start as last on {1} but will start on {2})'.format(
                            self.fullname, current_day, depend_start_date
                        )
                    )
                    self._cache_start_date = depend_start_date
                else:
                    # should be first day of start...
                    self._cache_start_date = depend_start_date
            else:
                # should be first day of start...
                self._cache_start_date = current_day

        if self._cache_start_date != self.start:
            LOG.warning(
                '** starting date for task "{0}" is changed from {1} to {2}'.format(
                    self.fullname, self.start, self._cache_start_date
                )
            )
        return self._cache_start_date

    def non_working_day(self, day):
        """
        Returns True if day is either during week-ends or global VACATIONS, extended to
        resource vacations only if task was assigne to a single resource
        """
        result = day.weekday() in _not_worked_days() or day in VACATIONS
        if self.resources is not None and len(self.resources) == 1:
            result = result or not self.resources[0].is_available(day)
        return result

    def end_date(self):
        """
        Returns the last day of the task, either the one which was given at task
        creation or the one calculated after checking dependencies
        """
        if self._cache_end_date is not None:
            return self._cache_end_date

        LOG.debug("** Task::end_date ({0})".format(self.name))

        if (self.duration is None or self.start is None) and self.stop is not None:
            real_end = self.stop
            # Take care of vacations
            while self.non_working_day(real_end):
                real_end -= datetime.timedelta(days=1)

            if real_end <= self.start_date() and self.duration is not None:
                current_day = self.start_date()
                real_duration = 0
                duration = self.duration
                while duration > 1 or self.non_working_day(current_day):
                    if not self.non_working_day(current_day):
                        real_duration = real_duration + 1
                        duration -= 1
                    else:
                        real_duration = real_duration + 1

                    current_day = self.start_date() + datetime.timedelta(
                        days=real_duration
                    )

                self._cache_end_date = self.start_date() + datetime.timedelta(
                    days=real_duration
                )
                LOG.warning(
                    '** task "{0}" will not be finished on time : end_date is changed from {1} to {2}'.format(
                        self.fullname, self.stop, self._cache_end_date
                    )
                )
                return self._cache_end_date

            self._cache_end_date = real_end
            if real_end != self.stop:
                LOG.warning(
                    '** task "{0}" will not be finished on time : end_date is changed from {1} to {2}'.format(
                        self.fullname, self.stop, self._cache_end_date
                    )
                )

            return self._cache_end_date

        if self.stop is None and self.duration is not None:
            current_day = self.start_date()
            real_duration = 0
            duration = self.duration
            while duration > 1 or self.non_working_day(current_day):
                if not self.non_working_day(current_day):
                    real_duration = real_duration + 1
                    duration -= 1
                else:
                    real_duration = real_duration + 1

                current_day = self.start_date() + datetime.timedelta(days=real_duration)

            self._cache_end_date = self.start_date() + datetime.timedelta(
                days=real_duration
            )
            return self._cache_end_date

        raise (ValueError)
        return None

    def svg(
        self,
        prev_y=0,
        start=None,
        end=None,
        color=None,
        level=None,
        scale=DRAW_WITH_DAILY_SCALE,
        title_align_on_left=False,
        offset=0,
        show_start_end_dates=False,
        gantt_type=TYPE.TASK,
        macro_mode=False,
        opacity=0.8,
        tu_width=1.0,
        tu_fraction=False,
    ):
        """
        Return SVG for drawing this task.

        Keyword arguments:
        prev_y -- int, line to start to draw
        start -- datetime.date of first day to draw
        end -- datetime.date of last day to draw
        color -- string of color for drawing the project
        level -- int, indentation level of the project, not used here
        scale -- drawing scale (d: days, w: weeks, m: months, q: quaterly)
        title_align_on_left -- boolean, align task title on left
        offset -- X offset from image border to start of drawing zone
        macro_mode -- boolean, not used (only in Project.svg())
        opacity -- float, opacity of drawing zone between 0 and 1,
        tu_width -- float, width of time unit in centimeters,
        tu_fraction -- boolean, whether to fractionate task duration under time unit
        """

        LOG.debug(
            "** Task::svg ({0})".format(
                {
                    "name": self.name,
                    "prev_y": prev_y,
                    "start": start,
                    "end": end,
                    "color": color,
                    "level": level,
                }
            )
        )
        if scale == DRAW_WITH_QUATERLY_SCALE:
            message = "DRAW_WITH_QUATERLY_SCALE not implemented yet"
            LOG.critical(message)
            raise ValueError(message)

        if not self.display:
            LOG.debug("** Task::svg ({0}) display off".format({"name": self.name}))
            return (None, 0)

        add_modified_begin_mark = False
        add_modified_end_mark = False

        if start is None:
            start = self.start_date()

        if self.start is not None and self.start_date() != self.start:
            add_modified_begin_mark = True

        if end is None:
            end = self.end_date()

        if self.stop is not None and self.end_date() != self.stop:
            add_modified_end_mark = True

        # override project color if defined
        if self.color is not None:
            color = self.color

        add_begin_mark = False
        add_end_mark = False

        y = prev_y

        # print(self.name + ": ", end="")
        # cas 1 -s--S==E--e-
        if self.start_date() >= start and self.end_date() <= end:
            # print("cas 1 -s--S==E--e-")
            x = _time_diff(scale, start, self.start_date(), False) * tu_width
            d = (
                _time_diff(scale, self.start_date(), self.end_date(), True) + 1
            ) * tu_width
            self.drawn_x_begin_coord = x
            self.drawn_x_end_coord = x + d
        # cas 5 -s--e--S==E-
        elif self.start_date() > end:
            # print("cas 5 -s--e--S==E-")
            return (None, 0)
        # cas 6 -S==E-s--e-
        elif self.end_date() < start:
            # print("cas 6 -S==E-s--e-")
            return (None, 0)
        # cas 2 -S==s==E--e-
        elif self.start_date() < start and self.end_date() <= end:
            # print("cas 2 -S==s==E--e-")
            x = 0
            d = (_time_diff(scale, start, self.end_date(), True) + 1) * tu_width
            self.drawn_x_begin_coord = x
            self.drawn_x_end_coord = x + d
            add_begin_mark = True
        # cas 3 -s--S==e==E-
        elif self.start_date() >= start and self.end_date() > end:
            # print("cas 3 -s--S==e==E-")
            x = _time_diff(scale, start, self.start_date(), False) * tu_width
            d = (_time_diff(scale, self.start_date(), end, True) + 1) * tu_width
            self.drawn_x_begin_coord = x
            self.drawn_x_end_coord = x + d
            add_end_mark = True
        # cas 4 -S==s==e==E-
        elif self.start_date() < start and self.end_date() > end:
            # print("cas 4 -S==s==e==E-")
            x = 0
            d = (_time_diff(scale, start, end, True) + 1) * tu_width
            self.drawn_x_begin_coord = x
            self.drawn_x_end_coord = x + d
            add_end_mark = True
            add_begin_mark = True
        else:
            # print("else")
            return (None, 0)

        self.drawn_y_coord = y
        svg = svgwrite.container.Group(id=re.sub(r"[ ,'\/()]", "_", self.name))
        svg.add(
            svgwrite.shapes.Rect(
                insert=((x + offset) * cm, (y + 0.1) * cm),
                size=(d * cm, 0.8 * cm),
                fill=color,
                stroke=color,
                stroke_width=2,
                opacity=opacity,
            )
        )
        svg.add(
            svgwrite.shapes.Rect(
                insert=((x + offset) * cm, (y + 0.6) * cm),
                size=(d * cm, 0.3 * cm),
                fill="#909090",
                stroke=color,
                stroke_width=1,
                opacity=opacity / 4.0,
            )
        )

        if add_modified_begin_mark:
            svg.add(
                svgwrite.shapes.Rect(
                    insert=((x + offset) * cm, (y + 0.1) * cm),
                    size=((tu_width * 0.1) * cm, 0.4 * cm),
                    fill="#0000FF",
                    stroke=color,
                    stroke_width=1,
                    opacity=opacity / 1.5,
                )
            )

        if add_modified_end_mark:
            svg.add(
                svgwrite.shapes.Rect(
                    insert=((x + d - (tu_width * 0.1) + offset) * cm, (y + 0.1) * cm),
                    size=((tu_width * 0.1) * cm, 0.4 * cm),
                    fill="#0000FF",
                    stroke=color,
                    stroke_width=1,
                    opacity=opacity / 1.5,
                )
            )

        if add_begin_mark:
            svg.add(
                svgwrite.shapes.Rect(
                    insert=((x + offset) * cm, (y + 0.1) * cm),
                    size=((tu_width * 0.1) * cm, 0.8 * cm),
                    fill="#000000",
                    stroke=color,
                    stroke_width=1,
                    opacity=opacity / 2.0,
                )
            )
        if add_end_mark:
            svg.add(
                svgwrite.shapes.Rect(
                    insert=((x + d - (tu_width * 0.1) + offset) * cm, (y + 0.1) * cm),
                    size=((tu_width * 0.1) * cm, 0.8 * cm),
                    fill="#000000",
                    stroke=color,
                    stroke_width=1,
                    opacity=opacity / 2.0,
                )
            )

        if self.percent_done is not None and 100 >= self.percent_done >= 0:
            # Bar shade
            svg.add(
                svgwrite.shapes.Rect(
                    insert=((x + offset) * cm, (y + 0.6) * cm),
                    size=((d * self.percent_done / 100) * cm, 0.3 * cm),
                    fill="#F08000",
                    stroke=color,
                    stroke_width=1,
                    opacity=opacity / 3.0,
                )
            )

        if not title_align_on_left:
            tx = x + 0.2
        else:
            tx = 5

        svg.add(
            svgwrite.text.Text(
                self.fullname,
                insert=((tx + offset) * cm, (y + 0.5) * cm),
                fill=_font_attributes()["fill"],
                stroke=_font_attributes()["stroke"],
                stroke_width=_font_attributes()["stroke_width"],
                font_family=_font_attributes()["font_family"],
                font_size=15,
            )
        )

        if show_start_end_dates:
            svg.add(
                svgwrite.text.Text(
                    self.start_date().strftime("%d/%m/%y"),
                    insert=((x + offset - 0.2) * cm, (y + 0.9) * cm),
                    fill=COLORS.START_END_DATES.value,
                    stroke=COLORS.START_END_DATES.value,
                    stroke_width=_font_attributes()["stroke_width"],
                    font_family=_font_attributes()["font_family"],
                    font_size=12,
                    style="text-anchor:end",
                )
            )
            svg.add(
                svgwrite.text.Text(
                    self.end_date().strftime("%d/%m/%y"),
                    insert=((x + offset + d + 0.2) * cm, (y + 0.9) * cm),
                    fill=COLORS.START_END_DATES.value,
                    stroke=COLORS.START_END_DATES.value,
                    stroke_width=_font_attributes()["stroke_width"],
                    font_family=_font_attributes()["font_family"],
                    font_size=12,
                )
            )

        if gantt_type == TYPE.RESOURCE and self.project is not None:
            t = self.project
            svg.add(
                svgwrite.text.Text(
                    "{0}".format(t),
                    insert=((tx + offset) * cm, (y + 0.85) * cm),
                    fill="purple",
                    stroke=_font_attributes()["stroke"],
                    stroke_width=_font_attributes()["stroke_width"],
                    font_family=_font_attributes()["font_family"],
                    font_size=15 - 5,
                )
            )
        elif gantt_type == TYPE.TASK and self.resources is not None:
            t = " / ".join(["{0}".format(r.name) for r in self.resources])
            svg.add(
                svgwrite.text.Text(
                    "{0}".format(t),
                    insert=((tx + offset) * cm, (y + 0.85) * cm),
                    fill="purple",
                    stroke=_font_attributes()["stroke"],
                    stroke_width=_font_attributes()["stroke_width"],
                    font_family=_font_attributes()["font_family"],
                    font_size=15 - 5,
                )
            )

        return (svg, 1)

    def svg_dependencies(self, prj):
        """
        Draws svg dependencies between task and project according to coordinates
        cached when drawing tasks

        Keyword arguments:
        prj -- Project object to check against
        """
        LOG.debug(
            "** Task::svg_dependencies ({0})".format({"name": self.name, "prj": prj})
        )
        if self.depends_on is None:
            return None
        else:
            svg = svgwrite.container.Group()
            for t in self.depends_on:
                if isinstance(t, Milestone):
                    if not (
                        t.drawn_x_end_coord is None
                        or t.drawn_y_coord is None
                        or self.drawn_x_begin_coord is None
                    ) and prj.is_in_project(t):
                        if t.drawn_x_end_coord < self.drawn_x_begin_coord:
                            # horizontal line
                            svg.add(
                                svgwrite.shapes.Line(
                                    start=(
                                        (t.drawn_x_end_coord + 0.9) * cm,
                                        (t.drawn_y_coord + 0.5) * cm,
                                    ),
                                    end=(
                                        (self.drawn_x_begin_coord) * cm,
                                        (t.drawn_y_coord + 0.5) * cm,
                                    ),
                                    stroke="black",
                                    stroke_dasharray="5,3",
                                )
                            )

                            marker = svgwrite.container.Marker(
                                insert=(5, 5), size=(10, 10)
                            )
                            marker.add(
                                svgwrite.shapes.Circle(
                                    (5, 5),
                                    r=5,
                                    fill="#000000",
                                    opacity=0.5,
                                    stroke_width=0,
                                )
                            )
                            svg.add(marker)
                            # vertical line
                            eline = svgwrite.shapes.Line(
                                start=(
                                    (self.drawn_x_begin_coord) * cm,
                                    (t.drawn_y_coord + 0.5) * cm,
                                ),
                                end=(
                                    (self.drawn_x_begin_coord) * cm,
                                    (self.drawn_y_coord + 0.5) * cm,
                                ),
                                stroke="black",
                                stroke_dasharray="5,3",
                            )
                            eline["marker-end"] = marker.get_funciri()
                            svg.add(eline)

                        else:
                            # horizontal line
                            svg.add(
                                svgwrite.shapes.Line(
                                    start=(
                                        (t.drawn_x_end_coord + 0.9) * cm,
                                        (t.drawn_y_coord + 0.5) * cm,
                                    ),
                                    end=(
                                        (self.drawn_x_begin_coord + 1) * cm,
                                        (t.drawn_y_coord + 0.5) * cm,
                                    ),
                                    stroke="black",
                                    stroke_dasharray="5,3",
                                )
                            )
                            # vertical
                            svg.add(
                                svgwrite.shapes.Line(
                                    start=(
                                        (self.drawn_x_begin_coord + 1) * cm,
                                        (t.drawn_y_coord + 0.5) * cm,
                                    ),
                                    end=(
                                        (self.drawn_x_begin_coord + 1) * cm,
                                        (t.drawn_y_coord + 1.5) * cm,
                                    ),
                                    stroke="black",
                                    stroke_dasharray="5,3",
                                )
                            )
                            # horizontal line
                            svg.add(
                                svgwrite.shapes.Line(
                                    start=(
                                        (self.drawn_x_begin_coord) * cm,
                                        (t.drawn_y_coord + 1.5) * cm,
                                    ),
                                    end=(
                                        (self.drawn_x_begin_coord + 1) * cm,
                                        (t.drawn_y_coord + 1.5) * cm,
                                    ),
                                    stroke="black",
                                    stroke_dasharray="5,3",
                                )
                            )

                            marker = svgwrite.container.Marker(
                                insert=(5, 5), size=(10, 10)
                            )
                            marker.add(
                                svgwrite.shapes.Circle(
                                    (5, 5),
                                    r=5,
                                    fill="#000000",
                                    opacity=0.5,
                                    stroke_width=0,
                                )
                            )
                            svg.add(marker)
                            # vertical line
                            eline = svgwrite.shapes.Line(
                                start=(
                                    (self.drawn_x_begin_coord) * cm,
                                    (t.drawn_y_coord + 1.5) * cm,
                                ),
                                end=(
                                    (self.drawn_x_begin_coord) * cm,
                                    (self.drawn_y_coord + 0.5) * cm,
                                ),
                                stroke="black",
                                stroke_dasharray="5,3",
                            )
                            eline["marker-end"] = marker.get_funciri()
                            svg.add(eline)

                elif isinstance(t, Task):
                    if not (
                        t.drawn_x_end_coord is None
                        or t.drawn_y_coord is None
                        or self.drawn_x_begin_coord is None
                    ) and prj.is_in_project(t):
                        # horizontal line
                        svg.add(
                            svgwrite.shapes.Line(
                                start=(
                                    (t.drawn_x_end_coord - 0.2) * cm,
                                    (t.drawn_y_coord + 0.5) * cm,
                                ),
                                end=(
                                    (self.drawn_x_begin_coord) * cm,
                                    (t.drawn_y_coord + 0.5) * cm,
                                ),
                                stroke="black",
                                stroke_dasharray="5,3",
                            )
                        )

                        marker = svgwrite.container.Marker(insert=(5, 5), size=(10, 10))
                        marker.add(
                            svgwrite.shapes.Circle(
                                (5, 5), r=5, fill="#000000", opacity=0.5, stroke_width=0
                            )
                        )
                        svg.add(marker)
                        # vertical line
                        eline = svgwrite.shapes.Line(
                            start=(
                                (self.drawn_x_begin_coord) * cm,
                                (t.drawn_y_coord + 0.5) * cm,
                            ),
                            end=(
                                (self.drawn_x_begin_coord) * cm,
                                (self.drawn_y_coord + 0.5) * cm,
                            ),
                            stroke="black",
                            stroke_dasharray="5,3",
                        )
                        eline["marker-end"] = marker.get_funciri()
                        svg.add(eline)

        return svg

    def nb_elements(self):
        """
        Returns the number of task, 1 here
        """
        LOG.debug("** Task::nb_elements ({0})".format({"name": self.name}))
        return 1

    def _reset_coord(self):
        """
        Reset cached elements of task
        """
        LOG.debug("** Task::reset_coord ({0})".format({"name": self.name}))
        self.drawn_x_begin_coord = None
        self.drawn_x_end_coord = None
        self.drawn_y_coord = None
        self._cache_start_date = None
        self._cache_end_date = None
        return

    def is_in_project(self, task):
        """
        Return True if the given Task is itself... (lazy coding ;)

        Keyword arguments:
        task -- Task object
        """
        LOG.debug(
            "** Task::is_in_project ({0})".format({"name": self.name, "task": task})
        )
        if task is self:
            return True

        return False

    def get_resources(self):
        """
        Returns Resources used in the task
        """
        return self.resources

    def check_conflicts_between_task_and_resources_vacations(self):
        """
        Displays a warning for each conflict between tasks and vacation of
        resources affected to the task

        And returns a dictionnary for resource vacation conflicts
        """
        conflicts = []
        if self.get_resources() is None:
            return conflicts
        for r in self.get_resources():
            cday = self.start_date()
            while cday <= self.end_date():
                if cday.weekday() not in _not_worked_days() and not r.is_available(
                    cday
                ):
                    conflicts.append(
                        {"resource": r.name, "date": cday, "task": self.name}
                    )
                    LOG.warning(
                        '** Caution resource "{0}" is affected on task "{2}" during vacations on day {1}'.format(
                            r.name, cday, self.fullname
                        )
                    )
                cday += datetime.timedelta(days=1)
        return conflicts

    def csv(self, csv=None):
        """
        Create CSV output from tasks

        Keyword arguments:
        csv -- None, dymmy object
        """
        if self.resources is not None:
            resources = ", ".join([x.fullname for x in self.resources])
        else:
            resources = ""

        csv_text = '"{0}";"{1}";{2};{3};{4};"{5}";\r\n'.format(
            self.state.replace('"', '\\"'),
            self.fullname.replace('"', '\\"'),
            self.start_date(),
            self.end_date(),
            self.duration,
            resources.replace('"', '\\"'),
        )
        return csv_text


############################################################################


class Milestone(Task):
    """
    Class for manipulating Milestones
    """

    def __init__(
        self, name, start=None, depends_on=None, color=None, fullname=None, display=True
    ):
        """
        Initialize milestone object. Two of start, stop or duration may be given.
        This milestone can rely on other milestone and will be completed with resources.
        If percent done is given, a progress bar will be included on the milestone.
        If color is specified, it will be used for the milestone.

        Keyword arguments:
        name -- name of the milestone (id)
        fullname -- long name given to the resource
        start -- datetime.date, first day of the milestone, default None
        depends_on -- list of Milestone which are parents of this one, default None
        color -- string, html color, default None
        display -- boolean, display this milestone, default True
        """
        LOG.debug(
            "** Milestone::__init__ {0}".format(
                {"name": name, "start": start, "depends_on": depends_on}
            )
        )
        self.name = name
        if fullname is not None:
            self.fullname = fullname
        else:
            self.fullname = name

        self.start = start
        self.stop = start
        self.duration = 0
        if color is not None:
            self.color = color
        else:
            self.color = COLORS.MILESTONES.value

        self.resources = None

        self.display = display
        self.state = "Milestone"

        if type(depends_on) is type([]):
            self.depends_on = depends_on
        elif depends_on is not None:
            self.depends_on = [depends_on]
        else:
            self.depends_on = None

        self.drawn_x_begin_coord = None
        self.drawn_x_end_coord = None
        self.drawn_y_coord = None
        self._cache_start_date = None
        self._cache_end_date = None

        return

    def end_date(self):
        """
        Returns the last day of the milestone, either the one which was given at milestone
        creation or the one calculated after checking dependencies
        """
        LOG.debug("** Milestone::end_date ({0})".format(self.name))
        # return self.start_date() - datetime.timedelta(days=1)
        return self.start_date()

    def svg(
        self,
        prev_y=0,
        start=None,
        end=None,
        color=None,
        level=None,
        scale=DRAW_WITH_DAILY_SCALE,
        title_align_on_left=False,
        offset=0,
        show_start_end_dates=False,
        gantt_type=TYPE.TASK,
        macro_mode=False,
        tu_width=1.0,
        tu_fraction=False,
    ):
        """
        Return SVG for drawing this milestone.

        Keyword arguments:
        prev_y -- int, line to start to draw
        start -- datetime.date of first day to draw
        end -- datetime.date of last day to draw
        color -- string of color for drawing the project
        level -- int, indentation level of the project, not used here
        scale -- drawing scale (d: days, w: weeks, m: months, q: quaterly)
        title_align_on_left -- boolean, align milestone title on left
        offset -- X offset from image border to start of drawing zone
        tu_width -- float, width of a time unit in drawing zone, not used here
        tu_fraction -- boolean, whether to show task duration in fractions under time unit, not used here
        """
        LOG.debug(
            "** Milestone::svg ({0})".format(
                {
                    "name": self.name,
                    "prev_y": prev_y,
                    "start": start,
                    "end": end,
                    "color": color,
                    "level": level,
                }
            )
        )

        if not self.display:
            LOG.debug("** Milestone::svg ({0}) display off".format({"name": self.name}))
            return (None, 0)

        # add_modified_begin_mark = False
        # add_modified_end_mark = False

        if start is None:
            start = self.start_date()

        # if self.start_date() != self.start and self.start is not None:
        #    add_modified_begin_mark = True

        if end is None:
            end = self.end_date()

        # if self.end_date() != self.stop and self.stop is not None:
        #    add_modified_end_mark = True

        # override project color if defined
        if self.color is not None:
            color = self.color

        # add_begin_mark = False
        # add_end_mark = False

        y = prev_y

        if scale == DRAW_WITH_QUATERLY_SCALE:
            message = "DRAW_WITH_QUATERLY_SCALE not implemented yet"
            LOG.critical(message)
            raise ValueError(message)

        # cas 1 -s--X--e-
        if self.start_date() >= start and self.end_date() <= end:
            x = _time_diff(scale, start, self.start_date(), False) * tu_width
            self.drawn_x_begin_coord = x
            self.drawn_x_end_coord = x
        else:
            return (None, 0)

        self.drawn_y_coord = y

        # insert=((x+1)*mm, (y+1)*mm),
        # size=((d-2)*mm, 8*mm),

        svg = svgwrite.container.Group(id=re.sub(r"[ ,'\/()]", "_", self.name))
        # 3.543307 is for conversion from mm to pt units !
        svg.add(
            svgwrite.shapes.Polygon(
                points=[
                    ((x + 0.5 + offset) * cm, (y + 0.2) * cm),
                    ((x + 0.8 + offset) * cm, (y + 0.5) * cm),
                    ((x + 0.5 + offset) * cm, (y + 0.8) * cm),
                    ((x + 0.2 + offset) * cm, (y + 0.5) * cm),
                ],
                fill=color,
                stroke=color,
                stroke_width=2,
                opacity=0.85,
            )
        )

        if not title_align_on_left:
            tx = x + 1
        else:
            tx = 0.5

        svg.add(
            svgwrite.text.Text(
                self.fullname,
                insert=((tx) * cm, (y + 0.5) * cm),
                fill=_font_attributes()["fill"],
                stroke=_font_attributes()["stroke"],
                stroke_width=_font_attributes()["stroke_width"],
                font_family=_font_attributes()["font_family"],
                font_size=15,
            )
        )

        if show_start_end_dates:
            svg.add(
                svgwrite.text.Text(
                    self.start_date().strftime("%d/%m/%y"),
                    insert=((x + 1 + offset) * cm, (y + 0.9) * cm),
                    fill=COLORS.START_END_DATES.value,
                    stroke=COLORS.START_END_DATES.value,
                    stroke_width=_font_attributes()["stroke_width"],
                    font_family=_font_attributes()["font_family"],
                    font_size=12,
                )
            )

        return (svg, 1)

    def svg_dependencies(self, prj):
        """
        Draws svg dependencies between milestone and project according to coordinates
        cached when drawing milestones

        Keyword arguments:
        prj -- Project object to check against
        """
        LOG.debug(
            "** Milestone::svg_dependencies ({0})".format(
                {"name": self.name, "prj": prj}
            )
        )
        if self.depends_on is None:
            return None
        else:
            svg = svgwrite.container.Group()
            for t in self.depends_on:
                if isinstance(t, Milestone):
                    if not (
                        t.drawn_x_end_coord is None
                        or t.drawn_y_coord is None
                        or self.drawn_x_begin_coord is None
                    ) and prj.is_in_project(t):
                        # horizontal line
                        svg.add(
                            svgwrite.shapes.Line(
                                start=(
                                    (t.drawn_x_end_coord + 0.9) * cm,
                                    (t.drawn_y_coord + 0.5) * cm,
                                ),
                                end=(
                                    (self.drawn_x_begin_coord + 0.5) * cm,
                                    (t.drawn_y_coord + 0.5) * cm,
                                ),
                                stroke="black",
                                stroke_dasharray="5,3",
                            )
                        )

                        marker = svgwrite.container.Marker(insert=(5, 5), size=(10, 10))
                        marker.add(
                            svgwrite.shapes.Circle(
                                (5, 5), r=5, fill="#000000", opacity=0.5, stroke_width=0
                            )
                        )
                        svg.add(marker)
                        # vertical line
                        eline = svgwrite.shapes.Line(
                            start=(
                                (self.drawn_x_begin_coord + 0.5) * cm,
                                (t.drawn_y_coord + 0.5) * cm,
                            ),
                            end=(
                                (self.drawn_x_begin_coord + 0.5) * cm,
                                (self.drawn_y_coord) * cm,
                            ),
                            stroke="black",
                            stroke_dasharray="5,3",
                        )
                        eline["marker-end"] = marker.get_funciri()
                        svg.add(eline)

                elif isinstance(t, Task):
                    if not (
                        t.drawn_x_end_coord is None
                        or t.drawn_y_coord is None
                        or self.drawn_x_begin_coord is None
                    ) and prj.is_in_project(t):
                        # horizontal line
                        svg.add(
                            svgwrite.shapes.Line(
                                start=(
                                    (t.drawn_x_end_coord - 0.2) * cm,
                                    (t.drawn_y_coord + 0.5) * cm,
                                ),
                                end=(
                                    (self.drawn_x_begin_coord + 0.5) * cm,
                                    (t.drawn_y_coord + 0.5) * cm,
                                ),
                                stroke="black",
                                stroke_dasharray="5,3",
                            )
                        )

                        marker = svgwrite.container.Marker(insert=(5, 5), size=(10, 10))
                        marker.add(
                            svgwrite.shapes.Circle(
                                (5, 5), r=5, fill="#000000", opacity=0.5, stroke_width=0
                            )
                        )
                        svg.add(marker)
                        # vertical line
                        eline = svgwrite.shapes.Line(
                            start=(
                                (self.drawn_x_begin_coord + 0.5) * cm,
                                (t.drawn_y_coord + 0.5) * cm,
                            ),
                            end=(
                                (self.drawn_x_begin_coord + 0.5) * cm,
                                (self.drawn_y_coord + 0.0) * cm,
                            ),
                            stroke="black",
                            stroke_dasharray="5,3",
                        )
                        eline["marker-end"] = marker.get_funciri()
                        svg.add(eline)

        return svg

    def get_resources(self):
        """
        Returns Resources used in the milestone
        """
        return []

    def check_conflicts_between_task_and_resources_vacations(self):
        """
        Displays a warning for each conflict between milestones and vacation of
        resources affected to the milestone

        And returns a dictionnary for resource vacation conflicts
        """
        return []

    def csv(self, csv=None):
        """
        Create CSV output from milestones

        Keyword arguments:
        csv -- None, dymmy object
        """
        if self.resources is not None:
            resources = ", ".join([x.fullname for x in self.resources])
        else:
            resources = ""

        csv_text = '"{0}";"{1}";{2};{3};{4};"{5}";\r\n'.format(
            self.state.replace('"', '\\"'),
            self.fullname.replace('"', '\\"'),
            self.start_date(),
            self.end_date(),
            self.duration,
            resources.replace('"', '\\"'),
        )
        return csv_text


##</Milestone>##############################################################

############################################################################


class Project(object):
    """
    Class for handling projects
    """

    def __init__(
        self,
        name="",
        color: Optional[str] = None,
        description: str = "",
        show_description: bool = False,
    ):
        """
        Initialize project with a given name and color for all tasks

        Keyword arguments:
        name -- string, name of the project
        color -- color for all tasks of the project
        """
        self.tasks: list[Task | Project] = []
        self.name = name
        if color is None:
            self.color = COLORS.PROJECTS.value
        else:
            self.color = color

        self.cache_nb_elements = None
        self.description = description
        self.show_description = show_description
        self.macro_task = Task(self.name, color=self.color, is_project=True)

    def add_task(self, task):
        """
        Add a Task to the Project. Task can also be a subproject

        Keyword arguments:
        task -- Task or Project object
        """
        self.tasks.append(task)
        self.cache_nb_elements = None
        return

    def _svg_calendar(
        self,
        maxx,
        maxy,
        start_date,
        today=None,
        scale=DRAW_WITH_DAILY_SCALE,
        offset=0,
        t0mode=False,
        tu_width=1.0,
        tu_fraction=False,
    ):
        """
        Draw calendar in svg, begining at start_date for maxx days, containing
        maxy lines. If today is given, draw a blue line at date

        Keyword arguments:
        maxx -- number of days, weeks, months or quarters (depending on scale) to draw
        maxy -- number of lines to draw
        start_date -- datetime.date of the first day to draw
        today -- datetime.date of day as today reference
        scale -- drawing scale (d: days, w: weeks, m: months, q: quaterly)
        offset -- X offset from image border to start of drawing zone
        """
        dwg = svgwrite.container.Group()

        cal = {0: "Lu", 1: "Ma", 2: "Me", 3: "Je", 4: "Ve", 5: "Sa", 6: "Di"}

        maxx += 1

        vlines = dwg.add(svgwrite.container.Group(id="vlines", stroke="lightgray"))
        for x in range(maxx):
            bold_vline = False
            if scale == DRAW_WITH_DAILY_SCALE:
                jour = start_date + datetime.timedelta(days=x)
                is_it_today = today == jour if today else False
            elif scale == DRAW_WITH_WEEKLY_SCALE:
                jour = start_date + relativedelta(weeks=x)
                jour_dapres = start_date + relativedelta(weeks=x + 1)
                is_it_today = (
                    (
                        jour.isocalendar().week == today.isocalendar().week
                        and jour.isocalendar().year == today.isocalendar().year
                    )
                    if today
                    else False
                )
                bold_vline = jour_dapres.month != jour.month
            elif scale == DRAW_WITH_MONTHLY_SCALE:
                jour = start_date + relativedelta(months=x)
                jour_dapres = start_date + relativedelta(months=x + 1)
                is_it_today = (
                    (today >= jour and today < jour_dapres) if today else False
                )
            elif scale == DRAW_WITH_QUATERLY_SCALE:
                # how many quarter do we need to draw ?
                message = "DRAW_WITH_QUATERLY_SCALE not implemented yet"
                LOG.critical(message)
                raise ValueError(message)

            tu_start_x = ((x * tu_width) + offset) * cm
            tu_middle_x = (((x + 0.5) * tu_width) + offset) * cm
            tu_end_x = (((x + 1.0) * tu_width) + offset) * cm

            vlines.add(
                svgwrite.shapes.Line(
                    start=(tu_end_x, 2 * cm),
                    end=(tu_end_x, (maxy + 2) * cm),
                    stroke_width=8 if bold_vline else 1,
                )
            )

            if is_it_today:

                x = tu_middle_x
                if scale == DRAW_WITH_WEEKLY_SCALE:
                    x = round(
                        tu_start_x
                        + (today.weekday() * ((tu_end_x - tu_start_x) / 7.0)),
                        2,
                    )
                elif scale == DRAW_WITH_MONTHLY_SCALE:
                    _, mtdays = calendar.monthrange(today.year, today.month)
                    x = round(
                        tu_start_x + (today.day * ((tu_end_x - tu_start_x) / mtdays)), 2
                    )

                vlines.add(
                    svgwrite.shapes.Rect(
                        insert=(x, 1 * cm),
                        size=(0.2 * cm, (maxy + 1) * cm),
                        fill=COLORS.TODAY.value,
                        stroke="lightgray",
                        stroke_width=0,
                        opacity=0.8,
                    )
                )

            if scale == DRAW_WITH_DAILY_SCALE:
                # draw vacations
                if (
                    start_date + datetime.timedelta(days=x)
                ).weekday() in _not_worked_days() or (
                    start_date + datetime.timedelta(days=x)
                ) in VACATIONS:
                    vlines.add(
                        svgwrite.shapes.Rect(
                            insert=(tu_start_x, 2 * cm),
                            size=(
                                tu_end_x - tu_start_x,
                                maxy * cm,
                            ),
                            fill="gray",
                            stroke="lightgray",
                            stroke_width=1,
                            opacity=0.9,
                        )
                    )

                # Current day
                vlines.add(
                    svgwrite.text.Text(
                        "{1} {0:02}".format(jour.day, cal[jour.weekday()][0]),
                        insert=(tu_start_x, 1.9 * cm),
                        fill="black",
                        stroke="black",
                        stroke_width=0,
                        font_family=_font_attributes()["font_family"],
                        font_size=15 - 3,
                    )
                )
                # Year
                if jour.day == 1 and jour.month == 1:
                    if t0mode:
                        text = f"Année A{jour.year - start_date.year + 1}"
                    else:
                        text = "{0}".format(jour.year)
                    vlines.add(
                        svgwrite.text.Text(
                            text,
                            insert=(tu_start_x, 0.5 * cm),
                            fill=COLORS.YEARS.value,
                            stroke=COLORS.YEARS.value,
                            stroke_width=0,
                            font_family=_font_attributes()["font_family"],
                            font_size=15 + 5,
                            font_weight="bold",
                        )
                    )
                # Month name
                if jour.day == 1:
                    if t0mode:
                        delta = (jour.year - start_date.year) * 12 + (
                            jour.month - start_date.month
                        )
                        text = f"Mois M{delta+1}"
                    else:
                        text = "{0}".format(jour.strftime("%B"))
                    vlines.add(
                        svgwrite.text.Text(
                            text,
                            insert=(tu_start_x, cm),
                            fill="#800000",
                            stroke="#800000",
                            stroke_width=0,
                            font_family=_font_attributes()["font_family"],
                            font_size=15 + 3,
                            font_weight="bold",
                        )
                    )
                # Week number
                if jour.weekday() == 0:
                    if t0mode:
                        text = f"S{(jour-start_date).days//7+1}"
                    else:
                        text = "S{0:02}".format(jour.isocalendar()[1])
                    vlines.add(
                        svgwrite.text.Text(
                            text,
                            insert=(tu_start_x, 1.5 * cm),
                            fill="black",
                            stroke="black",
                            stroke_width=0,
                            font_family=_font_attributes()["font_family"],
                            font_size=15 + 1,
                            font_weight="bold",
                        )
                    )

            elif scale == DRAW_WITH_WEEKLY_SCALE:
                # Year
                if jour.isocalendar()[1] == 1 and jour.month == 1:
                    if t0mode:
                        text = f"Année A{jour.year - start_date.year + 1}"
                    else:
                        text = "{0}".format(jour.year)
                    vlines.add(
                        svgwrite.text.Text(
                            text,
                            insert=(tu_start_x, 0.5 * cm),
                            fill=COLORS.YEARS.value,
                            stroke=COLORS.YEARS.value,
                            stroke_width=0,
                            font_family=_font_attributes()["font_family"],
                            font_size=15 + 5,
                            font_weight="bold",
                        )
                    )
                # Month name
                if jour.day <= 7:
                    if t0mode:
                        delta = (jour.year - start_date.year) * 12 + (
                            jour.month - start_date.month
                        )
                        text = f"Mois M{delta+1}"
                    else:
                        text = "{0}".format(jour.strftime("%B"))
                    vlines.add(
                        svgwrite.text.Text(
                            text,
                            insert=(tu_start_x, cm),
                            fill="#800000",
                            stroke="#800000",
                            stroke_width=0,
                            font_family=_font_attributes()["font_family"],
                            font_size=15 + 3,
                            font_weight="bold",
                        )
                    )
                if t0mode:
                    text = f"S{(jour-start_date).days//7+1}"
                else:
                    text = "S{0:02}".format(jour.isocalendar()[1])
                vlines.add(
                    svgwrite.text.Text(
                        text,
                        insert=(tu_start_x, 1.5 * cm),
                        fill="black",
                        stroke="black",
                        stroke_width=0,
                        font_family=_font_attributes()["font_family"],
                        font_size=15 + 1,
                        font_weight="bold",
                    )
                )

            elif scale == DRAW_WITH_MONTHLY_SCALE:
                # Month number
                if t0mode:
                    delta = (jour.year - start_date.year) * 12 + (
                        jour.month - start_date.month
                    )
                    text = f"M{delta+1}"
                else:
                    text = "{0}".format(jour.strftime("%m"))
                vlines.add(
                    svgwrite.text.Text(
                        text,
                        insert=(tu_start_x, 1.9 * cm),
                        fill="black",
                        stroke="black",
                        stroke_width=0,
                        font_family=_font_attributes()["font_family"],
                        font_size=15 - 3,
                    )
                )
                # Year
                if jour.month == 1:
                    if t0mode:
                        text = f"Année A{jour.year - start_date.year + 1}"
                    else:
                        text = "{0}".format(jour.year)
                    vlines.add(
                        svgwrite.text.Text(
                            text,
                            insert=(tu_start_x + 2, 0.5 * cm),
                            fill=COLORS.YEARS.value,
                            stroke=COLORS.YEARS.value,
                            stroke_width=0,
                            font_family=_font_attributes()["font_family"],
                            font_size=15 + 5,
                            font_weight="bold",
                        )
                    )
                    vlines.add(
                        svgwrite.shapes.Line(
                            start=(tu_start_x, 0),
                            end=(tu_start_x, (maxy + 2) * cm),
                            stroke=COLORS.YEARS.value,
                            stroke_dasharray="2,2",
                            stroke_width=4,
                            opacity=0.8
                        )
                    )

            elif scale == DRAW_WITH_QUATERLY_SCALE:
                # how many quarter do we need to draw ?
                message = "DRAW_WITH_QUATERLY_SCALE not implemented yet"
                LOG.critical(message)
                raise ValueError(message)

        vlines.add(
            svgwrite.shapes.Line(
                start=((offset + ((maxx + 1) * tu_width)) * cm, 2 * cm),
                end=((offset + ((maxx + 1) * tu_width)) * cm, (maxy + 2) * cm),
            )
        )

        hlines = dwg.add(svgwrite.container.Group(id="hlines", stroke="lightgray"))

        dwg.add(
            svgwrite.shapes.Line(
                start=(offset * cm, (2) * cm),
                end=((offset + (maxx * tu_width)) * cm, (2) * cm),
                stroke="black",
            )
        )
        dwg.add(
            svgwrite.shapes.Line(
                start=(offset * cm, (maxy + 2) * cm),
                end=((offset + (maxx * tu_width)) * cm, (maxy + 2) * cm),
                stroke="black",
            )
        )

        for y in range(2, maxy + 3):
            hlines.add(
                svgwrite.shapes.Line(
                    start=(offset * cm, y * cm),
                    end=((offset + (maxx * tu_width)) * cm, y * cm),
                )
            )

        return dwg

    def make_svg_for_tasks(
        self,
        filename,
        today=None,
        start=None,
        end=None,
        scale=DRAW_WITH_DAILY_SCALE,
        title_align_on_left=False,
        offset=0,
        t0mode=False,
        macro_mode=False,
        tu_width=1.0,
        tu_fraction=False,
    ):
        """
        Draw gantt of tasks and output it to filename. If start or end are
        given, use them as reference, otherwise use project first and last day

        Keyword arguments:
        filename -- string, filename to save to OR file object
        today -- datetime.date of day marked as a reference
        start -- datetime.date of first day to draw
        end -- datetime.date of last day to draw
        scale -- drawing scale (d: days, w: weeks, m: months, q: quaterly)
        title_align_on_left -- boolean, align task title on left
        offset -- X offset from image border to start of drawing zone
        tu_width -- float, width of a time unit on drawing zone in centimeters
        tu_fraction -- boolean, whether to show task duration fraction under time unit
        """
        if len(self.tasks) == 0:
            LOG.warning("** Empty project : {0}".format(self.name))
            return

        self._reset_coord()

        start_date = self.start_date() if start is None else start
        end_date = self.end_date() if end is None else end

        if start_date > end_date:
            message = "start date {0} > end_date {1}".format(start_date, end_date)
            LOG.critical(message)
            raise ValueError(message)

        ldwg = svgwrite.container.Group()
        psvg, pheight = self.svg(
            prev_y=2,
            start=start_date,
            end=end_date,
            scale=scale,
            title_align_on_left=title_align_on_left,
            offset=offset,
            t0mode=t0mode,
            macro_mode=macro_mode,
            tu_width=tu_width,
            tu_fraction=tu_fraction,
        )
        if psvg is not None:
            ldwg.add(psvg)

        dep = self.svg_dependencies(self)
        if dep is not None:
            ldwg.add(dep)

        maxx = _get_maxx(scale, start_date, end_date)

        dwg = _my_svgwrite_drawing_wrapper(filename, debug=True)
        dwg.add(
            svgwrite.shapes.Rect(
                insert=((0) * cm, 0 * cm),
                size=((offset + (maxx + 1) * tu_width) * cm, (pheight + 3) * cm),
                fill="white",
                stroke_width=0,
            )
        )

        dwg.add(
            self._svg_calendar(
                maxx,
                pheight,
                start_date,
                today,
                scale,
                offset=offset,
                t0mode=t0mode,
                tu_width=tu_width,
                tu_fraction=tu_fraction,
            )
        )
        dwg.add(ldwg)
        dwg.save(
            width=((offset + (maxx + 1) * tu_width) * cm),
            height=(pheight + 3) * cm,
        )
        return

    def make_svg_for_resources(
        self,
        filename,
        today=None,
        start=None,
        end=None,
        resources=None,
        one_line_for_tasks=False,
        filter="",
        scale=DRAW_WITH_DAILY_SCALE,
        title_align_on_left=False,
        offset=0,
        t0mode=False,
        resource_on_left=False,
        show_title=True,
        show_conflicts=True,
        show_vacations=True,
        tu_width=1.0,
        tu_fraction=False,
    ):
        """
        Draw resources affectation and output it to filename. If start or end are
        given, use them as reference, otherwise use project first and last day

        And returns to a dictionnary of dictionnaries for vacation and task
        conflicts for resources

        Keyword arguments:
        filename -- string, filename to save to OR file object
        today -- datetime.date of day marked as a reference
        start -- datetime.date of first day to draw
        end -- datetime.date of last day to draw
        resources -- list of Resource to check, default all
        one_line_for_tasks -- use only one line to display all tasks ?
        filter -- display only those tags
        scale -- drawing scale (d: days, w: weeks, m: months, q: quaterly)
        title_align_on_left -- boolean, align task title on left
        offset -- X offset from image border to start of drawing zone
        tu_width -- float, width of a time unit on drawing zone in centimeters
        tu_fraction -- boolean, whether to show task duration fraction under time unit
        """

        if scale not in (DRAW_WITH_DAILY_SCALE, DRAW_WITH_WEEKLY_SCALE):
            show_conflicts = show_vacations = False

        if len(self.tasks) == 0:
            LOG.warning("** Empty project : {0}".format(self.name))
            return

        self._reset_coord()

        start_date = self.start_date() if start is None else start
        end_date = self.end_date() if end is None else end

        if start_date > end_date:
            message = "start date {0} > end_date {1}".format(start_date, end_date)
            LOG.critical(message)
            raise ValueError(message)

        if resources is None:
            resources = self.get_resources()

        maxx = _get_maxx(scale, start_date, end_date)
        maxy = len(resources) * 2

        if maxy == 0:
            # No resources
            return {}

        # detect conflicts between resources and holidays
        conflicts_vacations = []
        for t in self.get_tasks():
            conflicts_vacations.append(
                t.check_conflicts_between_task_and_resources_vacations()
            )

        conflicts_vacations = _flatten(conflicts_vacations)

        ldwg = svgwrite.container.Group()

        if not one_line_for_tasks:
            ldwg.add(
                svgwrite.shapes.Line(
                    start=((0) * cm, (2) * cm),
                    end=((maxx + 1 + offset) * cm, (2) * cm),
                    stroke="black",
                )
            )

        nline = 2 if show_title else 1
        conflicts_tasks = []
        conflict_display_line = 1
        for r in resources:
            # do stuff for each resource
            if filter != "" and r.name not in filter:
                continue

            nline_ress = nline + 1 if resource_on_left else nline
            ress = svgwrite.container.Group()
            if resource_on_left and r.color is not None:
                ress.add(
                    svgwrite.shapes.Rect(
                        insert=(0, (nline_ress + 0.1) * cm),
                        size=((offset - 0.3) * cm, 0.8 * cm),
                        fill=r.color,
                        stroke=r.color,
                        stroke_width=1,
                        opacity=0.95,
                    )
                )
            ress.add(
                svgwrite.text.Text(
                    "{0}".format(r.fullname),
                    insert=(0.3 * cm, (nline_ress + 0.7) * cm),
                    fill=_font_attributes()["fill"],
                    stroke=_font_attributes()["stroke"],
                    stroke_width=_font_attributes()["stroke_width"],
                    font_family=_font_attributes()["font_family"],
                    font_size=15 + 3,
                )
            )

            overcharged_days = r.search_for_task_conflicts()

            conflict_display_line = nline + 1 if resource_on_left else nline
            nline += 1

            vac = svgwrite.container.Group()
            conflicts = svgwrite.container.Group()
            cday = start_date
            width = 4 * (tu_width / 10.0) if show_conflicts else 9.5 * (tu_width / 10.0)
            while cday <= end_date:
                # Vacations
                diff = _time_diff(scale, start_date, cday, False, tu_fraction=False)
                opacity = 0.65
                if scale == DRAW_WITH_WEEKLY_SCALE:
                    opacity /= 4.0
                if (
                    cday.weekday() not in _not_worked_days()
                    and cday not in VACATIONS
                    and not r.is_available(cday)
                ):
                    vac.add(
                        svgwrite.shapes.Rect(
                            insert=(
                                (diff * tu_width + offset + 0.1) * cm,
                                (conflict_display_line + 0.1) * cm,
                            ),
                            size=(width * cm, 0.8 * cm),
                            fill=COLORS.VACATIONS.value,
                            stroke=COLORS.VACATIONS.value,
                            stroke_width=1,
                            opacity=opacity,
                        )
                    )

                # Overcharge
                if (
                    cday.weekday() not in _not_worked_days()
                    and cday not in VACATIONS
                    and cday in overcharged_days
                ):
                    conflicts.add(
                        svgwrite.shapes.Rect(
                            insert=(
                                (diff * tu_width + 0.1 + 0.4 + offset) * cm,
                                (conflict_display_line + 0.1) * cm,
                            ),
                            size=(width * cm, 0.8 * cm),
                            fill="#AA0000",
                            stroke="#AA0000",
                            stroke_width=1,
                            opacity=opacity,
                        )
                    )

                cday += datetime.timedelta(days=1)

            nb_tasks = 0  # includes all resource's tasks in chart period, although he's on leave
            # nb_tasks_with_presence = 0
            project_task: Task = None

            for t in self.get_tasks():
                if t.get_resources() is not None and r in t.get_resources():
                    if t.start_date() <= end_date and start_date <= t.end_date():
                        nb_tasks += 1

                        if one_line_for_tasks and project_task is None:
                            project_task = Task(t.project, color=t.color, is_project=True)
                            project_task.start = t.start_date()

                            x = _time_diff(scale, t.start_date(), t.end_date(), True)
                            # TODO: make it a common code
                            title_capital_chars = sum(1 for char in t.project if char.isupper())
                            title_lower_chars = len(t.project) - title_capital_chars
                            font_size=15
                            title_width = round((
                                title_capital_chars * font_size / 1.5 + title_lower_chars * font_size / 2
                            ) / cm)

                            if title_width + 2 > x:
                                project_task.stop = t.start_date() + relativedelta(days=title_width+2) #HACK: +2 is take some margin with weekends
                            else:
                                project_task.stop = t.end_date()

                        elif project_task is not None and t.project in project_task.name and t.end_date() > project_task.stop:
                            project_task.stop = t.end_date()
                            project_task._reset_coord()
                        elif project_task is not None and not (t.project in project_task.name):
                            if t.start_date() > project_task.end_date():
                                psvg, _ = project_task.svg(
                                    prev_y=nline,
                                    start=start_date,
                                    end=end_date,
                                    scale=scale,
                                    title_align_on_left=title_align_on_left,
                                    offset=offset,
                                    gantt_type=TYPE.RESOURCE,
                                    show_start_end_dates=False,
                                    tu_width=tu_width,
                                    tu_fraction=tu_fraction,
                                )
                                if psvg is not None:
                                    ldwg.add(psvg)
                                    # nline += 1

                                project_task = Task(t.project, color=t.color, is_project=True)
                                project_task.start = t.start_date()
                                project_task.stop = t.end_date()
                            else:
                                project_task.name = project_task.name + " / " + t.project
                                project_task.fullname = project_task.name
                                x = _time_diff(scale, project_task.start_date(), project_task.end_date(), True) * tu_width
                                # TODO: make it a common code
                                title_capital_chars = sum(1 for char in project_task.name if char.isupper())
                                title_lower_chars = len(project_task.name) - title_capital_chars
                                font_size=15
                                title_width = round((
                                    title_capital_chars * font_size / 1.5 + title_lower_chars * font_size / 2
                                ) / cm)

                                if title_width + 2 > x:
                                    project_task.stop = project_task.start_date() + relativedelta(days=title_width+2)
                                elif t.end_date() > project_task.stop:
                                    project_task.stop = t.end_date()
                                project_task._reset_coord()



                    if not one_line_for_tasks:
                        psvg, _ = t.svg(
                            prev_y=nline,
                            start=start_date,
                            end=end_date,
                            scale=scale,
                            title_align_on_left=title_align_on_left,
                            offset=offset,
                            gantt_type=TYPE.RESOURCE,
                            show_start_end_dates=False,
                            tu_width=tu_width,
                            tu_fraction=tu_fraction,
                        )
                        if psvg is not None:
                            ldwg.add(psvg)
                            # nb_tasks_with_presence += 1
                            if not one_line_for_tasks:
                                nline += 1

            if nb_tasks == 0:
                nline -= 1
            else:
                if one_line_for_tasks and project_task is not None:
                    psvg, _ = project_task.svg(
                        prev_y=nline,
                        start=start_date,
                        end=end_date,
                        scale=scale,
                        title_align_on_left=title_align_on_left,
                        offset=offset,
                        gantt_type=TYPE.RESOURCE,
                        show_start_end_dates=False,
                        tu_width=tu_width,
                        tu_fraction=tu_fraction,
                    )
                    if psvg is not None:
                        ldwg.add(psvg)

                # print(r.fullname, nb_tasks)
                if resource_on_left or show_title:
                    ldwg.add(ress)
                    if show_vacations:
                        ldwg.add(vac)
                    if show_conflicts:
                        ldwg.add(conflicts)
                if nline > 0 and resource_on_left or not show_title:
                    nline -= 1

                if not one_line_for_tasks:
                    # nline += 1
                    ldwg.add(
                        svgwrite.shapes.Line(
                            start=((0) * cm, (nline + 1) * cm),
                            end=(
                                (((maxx + 1) * tu_width) + 1 + offset) * cm,
                                (nline+1) * cm,
                            ),
                            stroke="black",
                        )
                    )

                # nline += 1
                if one_line_for_tasks:
                    nline += 1
                    ldwg.add(
                        svgwrite.shapes.Line(
                            start=((0) * cm, (nline) * cm),
                            end=(
                                (((maxx + 1) * tu_width) + 1 + offset) * cm,
                                (nline) * cm,
                            ),
                            stroke="black",
                        )
                    )

        dwg = _my_svgwrite_drawing_wrapper(filename, debug=True)
        dwg.add(
            svgwrite.shapes.Rect(
                insert=(0 * cm, 0 * cm),
                size=((((maxx + 1) * tu_width) + 1 + offset) * cm, (nline + 1) * cm),
                fill="white",
                stroke_width=0,
                opacity=1,
            )
        )
        dwg.add(
            svgwrite.shapes.Line(
                start=((0) * cm, (nline + 1) * cm),
                end=((((maxx + 1) * tu_width) + 1 + offset) * cm, (nline + 1) * cm),
                stroke="black",
                stroke_width=2,
            )
        )

        dwg.add(
            self._svg_calendar(
                maxx,
                nline - 1,
                start_date,
                today,
                scale,
                offset=offset,
                t0mode=t0mode,
                tu_width=tu_width,
                tu_fraction=tu_fraction,
            )
        )
        dwg.add(ldwg)
        dwg.save(
            width=(offset + ((maxx + 1) * tu_width)) * cm,
            height=(nline + 1) * cm,
        )
        return {
            "conflicts_vacations": conflicts_vacations,
            "conflicts_tasks": conflicts_tasks,
        }

    def start_date(self):
        """
        Returns first day of the project
        """
        if len(self.tasks) == 0:
            LOG.warning("** Empty project : {0}".format(self.name))
            return datetime.date(9999, 1, 1)

        first = self.tasks[0].start_date()
        for t in self.tasks:
            if t.start_date() < first:
                first = t.start_date()
        return first

    def end_date(self):
        """
        Returns last day of the project
        """
        if len(self.tasks) == 0:
            LOG.warning("** Empty project : {0}".format(self.name))
            return datetime.date(1970, 1, 1)

        last = self.tasks[0].end_date()
        for t in self.tasks:
            if t.end_date() > last:
                last = t.end_date()
        return last

    def desc_svg(
        self,
        avail_width: int,
        color: str,
        x: float,
        prev_y: int,
        margin: int = 5,
        font_size: int = 18,
    ) -> tuple[Optional[svgwrite.container.Group], float]:
        line_char_count = int(avail_width / (font_size / 2))

        text_lines = self.description.split("\n")
        text_lines = sum(
            (textwrap.wrap(line, width=line_char_count) for line in text_lines),
            [self.name],
        )

        line_count = len(text_lines)
        if not self.name:
            return None, 0.0

        # TODO: make it a common code
        title_capital_chars = sum(1 for char in self.name if char.isupper())
        title_lower_chars = len(self.name) - title_capital_chars
        title_width = (
            title_capital_chars * font_size / 1.5 + title_lower_chars * font_size / 2
        )
        max_line_char_count = max(len(line) for line in text_lines)
        width = int(max(title_width, max_line_char_count * font_size / 2) + 2 * margin)
        width = min(avail_width, width)
        height = line_count * font_size + 2 * margin

        # HACK: Removed the divided by 10 and added 1 cm
        # Need to check if it works when the tu_width is modified
        x_top_left = x * cm - width + 1 * cm
        y_top_left = (prev_y + 0.5) * cm
        desc_box = svgwrite.container.Group()

        desc_box.add(
            svgwrite.shapes.Line(
                start=(title_width + 1 * cm, y_top_left),
                end=(x_top_left, y_top_left),
                stroke="gray",
                stroke_dasharray="15,10",
                stroke_width=1,
            )
        )

        desc_box.add(
            svgwrite.shapes.Rect(
                (x_top_left, y_top_left),
                (width, height),
                fill="white",
                stroke=color,
                stroke_width=3,
                opacity=0.8,
            )
        )

        desc_box.add(
            svgwrite.text.Text(
                text_lines[0],
                insert=(
                    x_top_left + 2 * margin,
                    y_top_left + margin / 2 + font_size,
                ),
                font_size=font_size,
                font_family=_font_attributes()["font_family"],
                font_weight="bold",
            )
        )

        for i, line in enumerate(text_lines[1:], start=1):
            desc_box.add(
                svgwrite.text.Text(
                    line,
                    insert=(
                        x_top_left + 2 * margin,
                        y_top_left + margin / 2 + (i + 1) * font_size,
                    ),
                    font_size=font_size,
                    font_family=_font_attributes()["font_family"],
                    font_weight="normal",
                )
            )

        return desc_box, height

    def svg(
        self,
        prev_y=0,
        start=None,
        end=None,
        color=None,
        level=0,
        scale=DRAW_WITH_DAILY_SCALE,
        title_align_on_left=False,
        offset=0,
        t0mode=False,
        show_start_end_dates=None,
        gantt_type=TYPE.TASK,
        macro_mode=False,
        show_leaves=True,
        tu_width=1.0,
        tu_fraction=False,
    ) -> tuple[svgwrite.container.Group | None, int]:
        """
        Return (SVG code, number of lines drawn) for the project. Draws all
        tasks and add project name with a purple bar on the left side.

        Keyword arguments:
        prev_y -- int, line to start to draw
        start -- datetime.date of first day to draw
        end -- datetime.date of last day to draw
        color -- string of color for drawing the project
        level -- int, indentation level of the project
        scale -- drawing scale (d: days, w: weeks, m: months, q: quaterly)
        title_align_on_left -- boolean, align task title on left
        offset -- X offset from image border to start of drawing zone
        """
        if show_start_end_dates is None:
            show_start_end_dates = not t0mode
        if start is None:
            start = self.start_date()
        if end is None:
            end = self.end_date()
        if color is None or self.color is not None:
            color = self.color

        font_size = 18

        cy = prev_y + 1 * (self.name != "")

        prj = svgwrite.container.Group()

        is_macro_project = macro_mode and level > 0
        macro_drawn = False

        res_leaves = {}

        for t in self.tasks:

            t_res_leaves = []

            if is_macro_project and type(t) is Task:
                if macro_drawn:
                    continue
                else:
                    self.macro_task.start_date = self.start_date
                    self.macro_task.end_date = self.end_date
                    self.macro_task.color = self.color
                    t = self.macro_task
                    macro_drawn = True

            if show_leaves and t.get_resources():
                for r in t.get_resources():
                    for v in r.vacations:

                        v_start, v_end = (None, None)

                        if type(v) is tuple:  # Period
                            leave_key = f"{r.name}-{v[0].strftime('%d-%m-%Y')}-{v[1].strftime('%d-%m-%Y')}"
                            v_start = v[0]
                            v_end = v[1]
                        else:  # Single day
                            leave_key = f"{r.name}-{v.strftime('%d-%m-%Y')}"
                            v_start = v
                            v_end = v

                        if (
                            (v_start < t.start_date() and v_end < t.start_date())
                            or (v_start > t.end_date() and v_end > t.end_date())
                            or leave_key in res_leaves.keys()
                        ):
                            continue

                        res_leaves[leave_key] = Task(
                            " ",
                            start=v_start,
                            stop=v_end,
                            color=COLORS.VACATIONS.value,
                        )
                        t_res_leaves.append(leave_key)

            trepr, theight = t.svg(
                cy,
                start=start,
                end=end,
                level=level + 1,
                scale=scale,
                title_align_on_left=title_align_on_left,
                offset=offset,
                show_start_end_dates=show_start_end_dates,
                gantt_type=gantt_type,
                macro_mode=macro_mode,
                tu_width=tu_width,
                tu_fraction=tu_fraction,
            )

            if trepr is not None:
                for lk in t_res_leaves:
                    lrepr, _ = res_leaves[lk].svg(
                        cy,
                        start=start,
                        end=end,
                        level=level + 1,
                        scale=scale,
                        title_align_on_left=title_align_on_left,
                        offset=offset,
                        show_start_end_dates=False,
                        gantt_type=gantt_type,
                        macro_mode=macro_mode,
                        opacity=1,
                        tu_width=tu_width,
                        tu_fraction=tu_fraction,
                    )
                    if lrepr is not None:
                        prj.add(lrepr)
                prj.add(trepr)
                cy += theight

        fprj = svgwrite.container.Group()
        prj_bar = False

        if self.name != "":
            is_project_in_interval = (
                start <= self.start_date() <= end
                or start <= self.end_date() <= end
                or self.start_date() <= start <= end <= self.end_date()
            )
            if is_project_in_interval or level == 1:
                fprj.add(
                    svgwrite.text.Text(
                        "{0}".format(self.name),
                        insert=(
                            (0.6 * level + 0.3 + offset) * cm,
                            (prev_y + 0.7) * cm,
                        ),
                        fill=_font_attributes()["fill"],
                        stroke=_font_attributes()["stroke"],
                        stroke_width=_font_attributes()["stroke_width"],
                        font_family=_font_attributes()["font_family"],
                        font_size=font_size,
                    )
                )

                fprj.add(
                    svgwrite.shapes.Rect(
                        insert=(
                            (0.6 * level + 0.08 + offset) * cm,
                            (prev_y + 0.5) * cm,
                        ),
                        size=(0.2 * cm, ((cy - prev_y - 1) + 0.4) * cm),
                        fill=color,
                        stroke=color,
                        stroke_width=0,
                        opacity=0.8,
                    )
                )
                prj_bar = True

            else:
                cy -= 1

            if is_project_in_interval and level >= 1 and self.show_description:
                x = _time_diff(scale, start, end, False) * tu_width
                desc_box, px_desc_height = self.desc_svg(
                    400, color, x, prev_y, font_size=font_size
                )
                if desc_box is not None:
                    prj.add(desc_box)

                    cm_desc_height = px_desc_height * px_to_cm + 1

                    tasks_height = cy - prev_y
                    if tasks_height < cm_desc_height:
                        cy += int(cm_desc_height - tasks_height)

        # Do not display empty tasks
        if (cy - prev_y) == 0 or ((cy - prev_y) == 1 and prj_bar):
            return (None, 0)

        fprj.add(prj)
        return (fprj, cy - prev_y)

    def svg_dependencies(self, prj: "Project"):
        """
        Draws svg dependencies between tasks according to coordinates cached
        when drawing tasks

        Keyword arguments:
        prj -- Project object to check against
        """
        svg = svgwrite.container.Group()
        for t in self.tasks:
            trepr = t.svg_dependencies(prj)
            if trepr is not None:
                svg.add(trepr)
        return svg

    def nb_elements(self):
        """
        Returns the number of tasks included in the project or subproject
        """
        if self.cache_nb_elements is not None:
            return self.cache_nb_elements

        nb = 0
        for t in self.tasks:
            nb += t.nb_elements()

        self.cache_nb_elements = nb
        return nb

    def _reset_coord(self):
        """
        Reset cached elements of all tasks and project
        """
        self.cache_nb_elements = None
        for t in self.tasks:
            t._reset_coord()
        return

    def is_in_project(self, task):
        """
        Return True if the given Task is in the project, False if not

        Keyword arguments:
        task -- Task object
        """
        for t in self.tasks:
            if t.is_in_project(task):
                return True
        return False

    def get_resources(self):
        """
        Returns Resources used in the project
        """
        rlist = []
        for t in self.tasks:
            r = t.get_resources()
            if r is not None:
                rlist.append(r)

        flist = []
        for r in _flatten(rlist):
            if r not in flist:
                flist.append(r)
        return flist

    def get_tasks(self):
        """
        Returns flat list of Tasks used in the Project and subproject
        """
        tlist = []
        for t in self.tasks:
            # if it is a sub project, recurse
            if type(t) is type(self):
                st = t.get_tasks()
                tlist.append(st)
            else:  # get task
                tlist.append(t)

        flist = []
        for r in _flatten(tlist):
            if r not in flist:
                flist.append(r)
        return flist

    def csv(self, csv=None):
        """
        Create CSV output from projects

        Keyword arguments:
        csv -- string, filename to save to OR file object OR None
        """
        if len(self.tasks) == 0:
            LOG.warning("** Empty project : {0}".format(self.name))
            return

        if csv is not None:
            csv_text = bytes.decode(codecs.BOM_UTF8, "utf-8")
            csv_text += '"State";"Task Name";"Start date";"End date";"Duration";"Resources";\r\n'
        else:
            csv_text = ""

        for t in self.tasks:
            c = t.csv()
            if c is not None:
                if sys.version_info[0] == 2:
                    try:
                        c = unicode(c, "utf-8")
                    except TypeError:
                        pass
                    csv_text += c
                elif sys.version_info[0] == 3:
                    csv_text += c
                else:
                    csv_text += c

        if csv is not None:
            test = False
            import io

            if sys.version_info[0] == 2:
                test = type(csv) == types.FileType or type(csv) == types.InstanceType
            elif sys.version_info[0] == 3:
                test = type(csv) == io.TextIOWrapper

            if test:
                csv.write(csv_text)
            else:
                fileobj = io.open(csv, mode="w", encoding="utf-8")
                fileobj.write(csv_text)
                fileobj.close()

        return csv_text


# MAIN -------------------
if __name__ == "__main__":
    import doctest

    # non regression test
    doctest.testmod()

else:
    LOG.initialize(level=logging.CRITICAL)


# <EOF>######################################################################
