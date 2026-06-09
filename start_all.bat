@echo off
cd /d "%~dp0"
echo Installing / refreshing Windows Task (Administrator required)...
call install_windows_task.bat
echo.
echo Starting background scheduler (backup)...
call run_scheduler_background.bat
echo.
echo Done. Check logs\task.log and logs\scheduler.log
pause
