@echo off
cd /d "%~dp0"
echo.
echo  Alpha1 WhatsApp - fresh start (new schedule)
echo  ============================================
echo.
echo  Stopping old processes...
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*Update_2*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
if exist logs\last_slot.txt del logs\last_slot.txt
echo.
echo  Schedule preview:
.venv\Scripts\python.exe main.py --check-schedule
echo.
echo  Starting scheduler...
call run_scheduler_background.bat
echo.
echo  For auto-start on logon + every 15 min watchdog:
echo    Right-click install_windows_task.bat -^> Run as administrator
echo.
pause
