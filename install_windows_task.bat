@echo off
cd /d "%~dp0"
echo.
echo  Install Windows background tasks (Administrator required)
echo  Works when PC is LOCKED - stay logged in, do not Sign out.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_windows_task.ps1"
