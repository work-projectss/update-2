# Start the 30-min scheduler every time you log in (stays running while PC is on).
# Right-click install_logon_scheduler.bat -> Run as administrator

$ErrorActionPreference = "Stop"

$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)
if (-not $isAdmin) {
    Start-Process powershell.exe -Verb RunAs -ArgumentList @(
        "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$PSCommandPath`""
    )
    exit 0
}

$ProjectRoot = $PSScriptRoot
$Starter = Join-Path $ProjectRoot "run_scheduler_background.bat"
$TaskName = "Alpha1 Vicidial WhatsApp Scheduler"

$Action = New-ScheduledTaskAction -Execute $Starter -WorkingDirectory $ProjectRoot
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Force | Out-Null

Write-Host "Logon task installed: $TaskName"
Write-Host "Starts the 30-min scheduler when you sign in."
Read-Host "Press Enter to close"
