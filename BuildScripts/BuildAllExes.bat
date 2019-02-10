@echo off

REM If VirtualEnv is not active, this script will enable it.
REM In that case we will disable it at the end.

if "%VIRTUAL_ENV%"=="" (
    call %~dp0\..\venv\Scripts\activate.bat
    set _ENV_CREATED = 1
) else (
    set _ENV_CREATED = 0
)

set PYTHONPATH=%~dp0\..\Source\;%PYTHONPATH%
cd %~dp0\..\Source\
set errorlevel=
python setup.py build

if "%_ENV_CREATED%"=="1" (
    set _ERRORLEVEL = %errorlevel%
    call %~dp0\..\..\..\venv\Scripts\deactivate.bat
    set %errorlevel% = %_ERRORLEVEL%
)

REM Forward the error level
exit /b %errorlevel%
