@echo off
REM Does the network let two machines reach each other? Classifies the blocker.
REM Stdlib only, no model needed. Run this BEFORE bothering with the model.
REM   nettest.bat -serve         on the master machine (prints its IP, listens)
REM   nettest.bat <master-ip>    on every other machine (classifies the result)
setlocal
if "%~1"=="" ( echo Usage:  nettest.bat -serve    OR    nettest.bat ^<master-ip^> & exit /b 1 )
python "%~dp0probe.py" %*
exit /b %errorlevel%
