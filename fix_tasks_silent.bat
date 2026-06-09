@echo off
REM Updates scheduled tasks to run fully hidden (no CMD popup). No sends.
schtasks /Change /TN "Alpha1 Vicidial WhatsApp Watchdog" /TR "wscript.exe //nologo c:\Projects\Update_2\watchdog_hidden.vbs"
schtasks /Change /TN "Alpha1 Vicidial WhatsApp Watchdog" /RI 5
schtasks /Change /TN "Alpha1 Vicidial WhatsApp Report" /TR "wscript.exe //nologo c:\Projects\Update_2\watchdog_hidden.vbs"
schtasks /Change /TN "Alpha1 Vicidial WhatsApp Report" /RI 30
echo Done. Tasks now run silent via wscript every 5 min (watchdog) / 30 min (report).
