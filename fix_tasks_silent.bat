@echo off
cd /d "%~dp0"
REM Updates scheduled tasks to run fully hidden (no CMD popup). No sends.
set "VBS=%~dp0watchdog_hidden.vbs"
schtasks /Change /TN "Alpha1 Vicidial WhatsApp Watchdog" /TR "wscript.exe //nologo \"%VBS%\""
schtasks /Change /TN "Alpha1 Vicidial WhatsApp Watchdog" /RI 5
schtasks /Change /TN "Alpha1 Vicidial WhatsApp Report" /TR "wscript.exe //nologo \"%VBS%\"" 2>nul
schtasks /Change /TN "Alpha1 Vicidial WhatsApp Report" /RI 30 2>nul
echo Done. Watchdog runs silent via wscript every 5 min.
