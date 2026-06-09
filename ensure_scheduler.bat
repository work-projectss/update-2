@echo off
cd /d "%~dp0"
wscript //nologo "%~dp0start_scheduler_hidden.vbs"
exit /b 0
