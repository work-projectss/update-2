@echo off
cd /d "%~dp0"
wscript //nologo "%~dp0watchdog_hidden.vbs"
exit /b 0
