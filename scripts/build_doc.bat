@echo off
REM This script was copied from PythonQwt project
REM ======================================================
REM Documentation build script
REM ======================================================
REM Licensed under the terms of the MIT License
REM Copyright (c) 2020 Pierre Raybaut
REM (see PythonQwt LICENSE file for more details)
REM ======================================================
call %~dp0utils GetScriptPath SCRIPTPATH
call %FUNC% GetLibName LIBNAME
call %FUNC% GetModName MODNAME
call %FUNC% SetPythonPath
call %FUNC% UsePython
call %FUNC% GetVersion CDL_VERSION
cd %SCRIPTPATH%\..
%PYTHON% doc\update_requirements.py
set PATH=C:\Program Files\HTML Help Workshop;C:\Program Files (x86)\HTML Help Workshop;%PATH%
sphinx-build -b singlehtml doc build\doc
start build\doc\index.html
call %FUNC% EndOfScript