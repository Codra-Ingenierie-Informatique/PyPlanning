![PyPlanning](https://raw.githubusercontent.com/Codra-Ingenierie-Informatique/PyPlanning/master/planning/data/planning.png)

[![pypi version](https://img.shields.io/pypi/v/PyPlanning.svg)](https://pypi.org/project/PyPlanning/)
[![PyPI status](https://img.shields.io/pypi/status/PyPlanning.svg)](https://github.com/Codra-Ingenierie-Informatique/PyPlanning/)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/PyPlanning.svg)](https://pypi.python.org/pypi/PyPlanning/)
[![download count](https://img.shields.io/conda/dn/conda-forge/PyPlanning.svg)](https://www.anaconda.com/download/)

ℹ️ Created in 2022 by [Pierre Raybaut](https://github.com/PierreRaybaut) and maintained by the [PyPlanning](https://github.com/Codra-Ingenierie-Informatique/PyPlanning) project team.

PyPlanning is a small planning tool initially developed for internal use at [CODRA](https://codra.net/). The main goal of this project is to provide a simple and easy-to-use planning tool for small teams or small projects, i.e. in cases where using a full-featured project management software is overkill.

# Examples

## Team schedule (daily view)

![Team schedule](https://raw.githubusercontent.com/Codra-Ingenierie-Informatique/PyPlanning/master/doc/images/shots/team_schedule-daily.png)

## Team schedule (tasks view)

![Team schedule / Tasks](https://raw.githubusercontent.com/Codra-Ingenierie-Informatique/PyPlanning/master/doc/images/shots/team_schedule-tasks.png)

## Simple project planning

![Simple project planning](https://raw.githubusercontent.com/Codra-Ingenierie-Informatique/PyPlanning/master/doc/images/shots/project_planning.png)

# Future plans

## High-priority tasks

Fix the following issues:

- FIXME: Treewidget/charts: removing project lead to "" project instead of no value
- TODO: Performance: process only gantt objects affected by changes
- TODO: Performance: update only visible chart? (this is it!)
- TODO: Performance: run chart update in a thread?
- TODO: New feature: custom chart names (instead of automatic indexed names)

## Medium-priority tasks

Implement the following features:

- TODO: Task: add "duplicate" action
- TODO: Task tree widget: add sub-context-menu "Bind to": resources
- TODO: Chart tree widget: add multiple checkboxes to select projects
- TODO: Chart tree widget: add QComboBox for editing the "project" field

## Low-priority tasks

Implement the following features:

- TODO: Add "percent_done" support for tasks
- TODO: Performance: add an option to update on demand?
- TODO: Replace python-gantt (planning/gantt.py) by an alternative with less restrictive
  license terms (no GPL!)

# License

PyPlanning is licensed under the terms of the GPL v3 license. This is prescribed by
the library upon which PyPlanning depends on for generating SVG Gantt plannings
(see GPL-based library code ([python-gantt](https://pypi.org/project/python-gantt/)).
The code of this library has been drastically patched and adapted to PyPlanning needs.
