@echo off
cd /d "%~dp0"
echo.
echo === Windows Task status ===
schtasks /Query /TN "Alpha1 Vicidial WhatsApp Report" /FO LIST /V | findstr /I "Next Run Status Last Run Task To Run Run As Logon"
echo.
if exist logs\task.log (
    echo === Last 15 log lines ===
    powershell -NoProfile -Command "Get-Content logs\task.log -Tail 15"
) else (
    echo No logs\task.log yet — task has not run since install.
)
echo.
pause
