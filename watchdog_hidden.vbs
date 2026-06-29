' Silent watchdog — keeps scheduler alive (no CMD window). Runs via Task Scheduler every 5 min.
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = root
shell.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -File """ & root & "\start_scheduler.ps1""", 0, False
