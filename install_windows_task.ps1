# Background tasks: start scheduler at logon + watchdog every 1 min (locked screen OK).
# Right-click install_windows_task.bat -> Run as administrator

$ErrorActionPreference = "Stop"

$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)
if (-not $isAdmin) {
    Write-Host "Requesting Administrator..."
    Start-Process powershell.exe -Verb RunAs -ArgumentList @(
        "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$PSCommandPath`""
    )
    exit 0
}

$ProjectRoot = $PSScriptRoot
$WatchVbs = Join-Path $ProjectRoot "watchdog_hidden.vbs"
$RunBat = Join-Path $ProjectRoot "watchdog.bat"
$LogonTask = "Alpha1 Vicidial WhatsApp Scheduler"
$WatchTask = "Alpha1 Vicidial WhatsApp Watchdog"
$XmlFile = Join-Path $ProjectRoot "install_task.xml"

if (-not (Test-Path $RunBat)) {
    Write-Error "Missing $RunBat"
}

# S4U = runs in background while user is logged on (locked screen OK)
$xml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.3" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Keep Alpha1 WhatsApp scheduler running (locked screen OK)</Description>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>$env:USERDOMAIN\$env:USERNAME</UserId>
      <LogonType>S4U</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <StartWhenAvailable>true</StartWhenAvailable>
    <WakeToRun>true</WakeToRun>
    <ExecutionTimeLimit>PT5M</ExecutionTimeLimit>
    <Enabled>true</Enabled>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>wscript.exe</Command>
      <Arguments>//nologo "$WatchVbs"</Arguments>
      <WorkingDirectory>$ProjectRoot</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"@

$watchXml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.3" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Restart Alpha1 WhatsApp scheduler if stopped</Description>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>$(Get-Date -Format "yyyy-MM-dd")T00:00:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
      <Repetition>
        <Interval>PT5M</Interval>
        <Duration>P1D</Duration>
        <StopAtDurationEnd>false</StopAtDurationEnd>
      </Repetition>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>$env:USERDOMAIN\$env:USERNAME</UserId>
      <LogonType>S4U</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <StartWhenAvailable>true</StartWhenAvailable>
    <WakeToRun>true</WakeToRun>
    <ExecutionTimeLimit>PT5M</ExecutionTimeLimit>
    <Enabled>true</Enabled>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>wscript.exe</Command>
      <Arguments>//nologo "$WatchVbs"</Arguments>
      <WorkingDirectory>$ProjectRoot</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"@

$xml | Out-File -FilePath $XmlFile -Encoding Unicode -Force
$watchXmlPath = Join-Path $ProjectRoot "install_watchdog_task.xml"
$watchXml | Out-File -FilePath $watchXmlPath -Encoding Unicode -Force

schtasks /Delete /TN $LogonTask /F 2>$null | Out-Null
schtasks /Delete /TN $WatchTask /F 2>$null | Out-Null
schtasks /Delete /TN "Alpha1 Vicidial WhatsApp Report" /F 2>$null | Out-Null

schtasks /Create /TN $LogonTask /XML $XmlFile /F | Out-Null
schtasks /Create /TN $WatchTask /XML $watchXmlPath /F | Out-Null

Write-Host ""
Write-Host "=== Installed (locked screen OK) ==="
Write-Host "  $LogonTask  - at Windows logon"
Write-Host "  $WatchTask  - every 5 min silent (keep scheduler alive, no sends)"
Write-Host ""
Write-Host "Stay logged in. Lock screen (Win+L) is fine."
Write-Host "Log: $ProjectRoot\logs\scheduler.log"
Write-Host ""
schtasks /Query /TN $LogonTask /FO LIST | Select-String "Status|Task To Run"
schtasks /Query /TN $WatchTask /FO LIST | Select-String "Next Run|Status"
Write-Host ""
Read-Host "Press Enter to close"
