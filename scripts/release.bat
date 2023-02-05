@echo off

call %~dp0utils GetScriptPath SCRIPTPATH
call %FUNC% GetLibName LIBNAME
cd %SCRIPTPATH%\..\
call %FUNC% SetPythonPath
call %FUNC% UseWinPython
call %FUNC% GetVersion VERSION

echo ===========================================================================
echo Making %LIBNAME% v%VERSION% release with %WINPYDIRBASE%
echo ===========================================================================

@REM set destdir=releases\%LIBNAME%-v%VERSION%-release
@REM if exist %destdir% ( rmdir /s /q %destdir% )
@REM mkdir %destdir%
@REM move "dist\*.whl" %destdir%
@REM move "dist\*.gz" %destdir%
@REM move "dist\*.zip" %destdir%
@REM move %LIBNAME%-%VERSION%.exe %destdir%
@REM copy "CHANGELOG_fr.md" %destdir%
set destdir=releases\
move %LIBNAME%-%VERSION%.exe %destdir%
explorer %destdir%

call %FUNC% EndOfScript