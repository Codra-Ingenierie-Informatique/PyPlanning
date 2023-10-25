@echo off
cd/D "C:\Apps\WPy64-31001-PyPlanning\scripts\"
call "env_for_icons.bat" %*
cd/D %~dp0
set PYTHONPATH=%cd%;C:\Dev\Libre\guidata
pylint .\planning\ --ignore=gantt.py,simplebrowser.py
pause