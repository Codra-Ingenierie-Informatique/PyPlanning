# PyPlanning Releases #

## Version 2.2.0 ##

💥 New features:

* Keep graphs from the current planning open when merging multiple planning
* Improvement on the "Resources" graph showing task for each resource as a Gantt for better visualization
* "Macro resources" graph added allowing a one line per resources view automatically merging project names or task names

🛠️ Bug fixes:

* Fix merge multiples planning when old depend references where still present in the XML
* Fix task completion input when including a '%' character during editing

## Version 2.1.1 ##

💥 New features:

* First implementation of a "Merge planning" feature

🛠️ Bug fixes:

* [Issue #51](https://github.com/Codra-Ingenierie-Informatique/PyPlanning/issues/51) - No version check when opening a file

## Version 2.1.0 ##

💥 New features:

* [Issue #44](https://github.com/Codra-Ingenierie-Informatique/PyPlanning/issues/44) - Modulate time scale on charts (variable time unit width editable in XML)
* [Issue #46](https://github.com/Codra-Ingenierie-Informatique/PyPlanning/issues/46) - Edit closing dates via GUI
* [Issue #47](https://github.com/Codra-Ingenierie-Informatique/PyPlanning/issues/47) - Set leaves by duration in complement of date periods

🛠️ Bug fixes:


* [Issue #21](https://github.com/Codra-Ingenierie-Informatique/PyPlanning/issues/21) - DataItems of type DTypes.MULTIPLE_CHOICE and DTypes.CHOICE cannot handle duplicate values approprietly
* [Issue #29](https://github.com/Codra-Ingenierie-Informatique/PyPlanning/issues/29) - Ressource graph missing bottom line
* [Issue #35](https://github.com/Codra-Ingenierie-Informatique/PyPlanning/issues/35) - Dates between TreeView and Chart may be desynchronized
  * Homogenized calculated dates display in tree, in dedicated columns
  * Prevent set of task's start date before last end of its deps
* [Issue #38](https://github.com/Codra-Ingenierie-Informatique/PyPlanning/issues/38) - It shouldn't be possible to add a "leave" task under a global task
* [Issue #40](https://github.com/Codra-Ingenierie-Informatique/PyPlanning/issues/40) - Chart: show resources even if on leave during the period
  * Proposed fix:
    * For resource chart, count resource if his task is in the period, even if he's on leave.
    * For task chart, when processing task draw, create temp "tasks" on resources' leaves periods and print them above the task.
  * May draw resources' leaves on another level according to #43 enhancement
* [Issue #41](https://github.com/Codra-Ingenierie-Informatique/PyPlanning/issues/41) - Undefined dates causing ValueErrors
* [Issue #42](https://github.com/Codra-Ingenierie-Informatique/PyPlanning/issues/42) - Modifications are not saved when planning is opened in XML advanced mode
* [Issue #45](https://github.com/Codra-Ingenierie-Informatique/PyPlanning/issues/45) - Today mark isn't always exact
* [Issue #49](https://github.com/Codra-Ingenierie-Informatique/PyPlanning/issues/49) - Possible incorrect calculated start date when toggling duration mode of given dep-free task

## Version 2.0.1 ##

🛠️ Bug fixes:

* [Issue #36](https://github.com/Codra-Ingenierie-Informatique/PyPlanning/issues/36) - Duplicated task cannot depend on original task
* [Issue #31](https://github.com/Codra-Ingenierie-Informatique/PyPlanning/issues/31) - Action "duplicate task" does not work normally
* [Issue #24](https://github.com/Codra-Ingenierie-Informatique/PyPlanning/issues/24) - When PyPlanning is opened directly in XML mode, the toolbar is active and can cause errors
* [Issue #30](https://github.com/Codra-Ingenierie-Informatique/PyPlanning/issues/30) - When the application starts, the project actions are shown in the toolbar
* [Issue #27](https://github.com/Codra-Ingenierie-Informatique/PyPlanning/issues/27) - Months displayed in the SVG chart are always in english
* [Issue #25](https://github.com/Codra-Ingenierie-Informatique/PyPlanning/issues/25) - Action "Edit" triggers an error in an empty project when no item is currently selected (e.g. empty planning)
* [Issue #26](https://github.com/Codra-Ingenierie-Informatique/PyPlanning/issues/26) - Color editor does not allow to unselect a color to use the default one
* [Issue #29](https://github.com/Codra-Ingenierie-Informatique/PyPlanning/issues/29) - Ressource graph missing bottom line
* Improved description box sizing in the chart view

## Version 2.0.0 ##

💥 New features:

* [Issue #15](https://github.com/Codra-Ingenierie-Informatique/PyPlanning/issues/15) - Charts: show multiple projects status and description:
  * New Project Tree that allows users to create, delete, modify and organise projects
    * Project selections for charts has not changed
    * Project selection for tasks is now done via a combobox
    * Projects color can be modified
  * Charts:
    * Project description is now displayed on the right part of the chart
* [Issue #20](https://github.com/Codra-Ingenierie-Informatique/PyPlanning/issues/20) - Charts: new "Macro tasks" option for grouping tasks related to the same project
* Various enhancements (when creating a task, etc.)

🛠️ Bug fixes:

* Fix some translations
* Fix bugs related to tasks number when moving up or down
* Fix error when creating tasks (from an empty Task Tree, when selecting a resource
  or when clicking on a "leave" row)
* Fix chart not updating on project selection
* Fix SVG deletion when opening another planning, *saving as* or creating a new planning
* Fix various issues related to single choice and multiple choices editors

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
