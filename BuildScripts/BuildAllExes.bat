@echo off

REM NOTE: You need to install python cx_freeze for this to work

set PYTHONPATH=%~dp0\..\Source\
cd %~dp0\..\Source\
python setup.py build
