@echo off
cd /d "%~dp0"
echo.
echo  Alpha1 WhatsApp - background setup (works when PC is locked)
echo  =============================================================
echo.
echo  Requirements: stay LOGGED IN (lock screen is OK, do not Sign out).
echo  PC must stay ON during business hours.
echo.

echo  [1/3] Stopping old instances...
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*Update_2*main.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"

echo  [2/3] Starting hidden scheduler now...
call ensure_scheduler.bat
timeout /t 2 /nobreak >nul

echo  [3/3] Adding Startup shortcut (runs after every login)...
powershell -NoProfile -Command ^
  "$root = '%CD%'; $startup = [Environment]::GetFolderPath('Startup');" ^
  "$lnk = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $startup 'Alpha1 WhatsApp Scheduler.lnk'));" ^
  "$lnk.TargetPath = 'wscript.exe';" ^
  "$lnk.Arguments = '\"\"' + $root + '\start_scheduler_hidden.vbs\"\"';" ^
  "$lnk.WorkingDirectory = $root; $lnk.WindowStyle = 7; $lnk.Description = 'Alpha1 Vicidial WhatsApp scheduler';" ^
  "$lnk.Save(); Write-Host 'Startup shortcut created.'"

echo.
echo  OPTIONAL (recommended): Right-click install_windows_task.bat -^> Run as administrator
echo  That adds a watchdog every 1 min if the scheduler ever stops.
echo.
echo  Log file: logs\scheduler.log
echo.
pause
