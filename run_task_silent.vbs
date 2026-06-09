' For Task Scheduler — fully hidden, no CMD window. No sends.
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = root
shell.Run "wscript.exe //nologo """ & root & "\start_scheduler_hidden.vbs""", 0, False
