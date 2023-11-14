# PyPlanning Releases #

## Version 1.5.8 ##

🛠️ Bug fixes:

* ...

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