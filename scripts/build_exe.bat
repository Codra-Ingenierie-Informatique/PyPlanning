@echo off
REM This script adapted from PythonQwt project
REM ======================================================
REM Executable build script
REM ======================================================
REM Licensed under the terms of the MIT License
REM Copyright (c) 2020 Pierre Raybaut
REM (see PythonQwt LICENSE file for more details)
REM ======================================================
call %~dp0utils GetScriptPath SCRIPTPATH
call %FUNC% GetLibName LIBNAME
cd %SCRIPTPATH%\..\
call %FUNC% SetPythonPath
call %FUNC% UsePython
pyinstaller %LIBNAME%.spec --noconfirm
call %FUNC% EndOfScript