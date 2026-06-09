' Runs the report job hidden and waits until finished (for Task Scheduler).
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = root

logPath = root & "\logs\task.log"
If Not fso.FolderExists(root & "\logs") Then fso.CreateFolder(root & "\logs")

Set logFile = fso.OpenTextFile(logPath, 8, True)
logFile.WriteLine "[" & Now & "] Task started (VBS)"
logFile.Close

pythonExe = root & "\.venv\Scripts\python.exe"
mainPy = root & "\main.py"
cmd = """" & pythonExe & """ """ & mainPy & """ --once"
exitCode = shell.Run(cmd, 0, True)

Set logFile = fso.OpenTextFile(logPath, 8, True)
logFile.WriteLine "[" & Now & "] Exit code " & exitCode
logFile.Close

WScript.Quit exitCode
