# PyPlanning Releases #

## Version 1.6.0 ##

💥 Changes:

* [Issue #3](https://github.com/Codra-Ingenierie-Informatique/PyPlanning/issues/3) - Performance: update only visible chart
* [Issue #5](https://github.com/Codra-Ingenierie-Informatique/PyPlanning/issues/5) - Add support for custom chart names
* [Issue #7](https://github.com/Codra-Ingenierie-Informatique/PyPlanning/issues/7) - Add "Duplicate" action
* [Issue #18](https://github.com/Codra-Ingenierie-Informatique/PyPlanning/issues/18) - Add support for "%" (percent done) feature for tasks
* [Issue #19](https://github.com/Codra-Ingenierie-Informatique/PyPlanning/issues/19) - Add support for "Depends on" feature for tasks:
  * Added task number in the tree view
  * New "Depends on" column in the tree view with multiple checkboxes selection
  * When adding a new task, the "depends on" column is automatically filled with the
    previous task as a dependency, if any
* Charts / Project management:
  * Added support for multiple projects in the same chart
  * Projects are selected using multiple checkboxes in the chart tree view

🛠️ Bug fixes:

* [Issue #2](https://github.com/Codra-Ingenierie-Informatique/PyPlanning/issues/2) - GUI: task color combo box is not shown in the tree widget
* [Issue #13](https://github.com/Codra-Ingenierie-Informatique/PyPlanning/issues/13) - Performance: add an option to update on demand?
* [Issue #16](https://github.com/Codra-Ingenierie-Informatique/PyPlanning/issues/16) - Color issue when creating a new task
* [Issue #17](https://github.com/Codra-Ingenierie-Informatique/PyPlanning/issues/17) - Another `color` issue with tasks

## Version 1.5.12 ##

🛠️ Bug fixes:

* Fixed an annoying bug where the application would select an unexpected line
  in the tree view when the user would modify a task's start date, end date or
  duration:
  * This was due to the fact that the application was repopulating the tree
    view after each modification, which would lead to the selection of one of
    the first lines in the tree view
  * This is now fixed because the application is now refreshing the existing
    tree view instead of repopulating it

💥 Changes:

* Task tree: resource collapse/expand state is now saved in project file,
  so that the application can restore it when the project is reopened

## Version 1.5.11 ##

🛠️ Bug fixes:

* Fixed a bug related to adding a task to a resource (order issue):
  * Selecting a resource and adding a task to it would lead to an unexpected
    behavior (the task would sometimes appear to be added to another resource)
  * This was due to the fact that the application was not properly handling
    the case where the user would select a resource in the tree view, except
    for the first resource
  * This is now fixed

## Version 1.5.10 ##

🛠️ Bug fixes:

* Logging issues:
  * Added `LoggingHelper` class to handle properly logging in various contexts
    (e.g. when running with `pythonw.exe` on Windows, or when debugging)
  * This fixes the critical bug where the application would not show any chart
    when running with `pythonw.exe` on Windows

## Version 1.5.9 ##

🛠️ Bug fixes:

* Logging only when `PLANNINGDEBUG` environment variable is set to `1`, `2` or `3`
  (this is considered a bug fix because it was the intended behavior)

## Version 1.5.8 ##

🛠️ Bug fixes:

* When switching from XML mode to Tree mode, check if the Tree view can be updated (i.e. if the XML is valid). If not, do not switch to Tree mode and show a warning message instead.
* Fixed crash when application was trying to log a message in standard output (stdout) while running with pythonw.exe (instead of python.exe) on Windows: now redirecting logging to internal Qt console instead of stdout
* Log viewer: improved readability of log messages

## Version 1.5.7 ##

💥 Changes:

* New default colors for project tasks (light cyan)
* New default colors for vacations (silver)


## Version 1.5.6 ##

🛠️ Bug fixes:

* Reintroduced application logs (were accidentally removed in 1.5.3 following a refactoring)
* XML mode: fixed a bug where the application would crash if the user tried to remove a start date from a task

💥 Changes:

* New default colors for tasks and resources


## Version 1.5.5 ##

🛠️ Bug fixes:

* Log all warnings to internal console only if DEBUG is enabled

💥 Changes:

* Added [Python package](https://pypi.org/project/PyPlanning/)
* Added [documentation](https://pyplanning.readthedocs.io/)

## Version 1.5.4 ##

🛠️ Bug fixes:

* Fixed hard crashes due to multithreaded internal console

## Version 1.5.3 ##

🛠️ Bug fixes:

* Gantt/Monthly scale: fixed start date of tasks
* Better handling of column margins

💥 Changes:

* User configuration files moved to .PyPlanning folder
* Added a third level of debug, disabling the internal console (see about dialog)

♻ PyPlanning internal changes:

* Added launcher script (dev)
* Updated requirements
* `PlanningData`: fixed design flaw (removed singleton)
* Fixed various code quality issues