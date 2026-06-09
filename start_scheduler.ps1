$root = (Resolve-Path $PSScriptRoot).Path

function Test-SchedulerHealthy {
    $heartbeat = Join-Path $root "logs\scheduler.heartbeat"
    if (-not (Test-Path $heartbeat)) { return $false }
    try {
        $last = [datetime]::Parse((Get-Content $heartbeat -Raw).Trim())
        return ((Get-Date) - $last).TotalSeconds -lt 90
    }
    catch {
        return $false
    }
}

function Get-SchedulerProcs {
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -eq "pythonw.exe" -and
            $_.ExecutablePath -like "*$root*"
        }
}

if (Test-SchedulerHealthy) {
    exit 0
}

$procs = @(Get-SchedulerProcs)
if ($procs.Count -gt 1) {
    $procs | Select-Object -Skip 1 | ForEach-Object {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

$procs = @(Get-SchedulerProcs)
if ($procs.Count -ge 1 -and (Test-SchedulerHealthy)) {
    exit 0
}

$mutexName = "Alpha1WhatsAppScheduler_Update2"
$created = $false
$probe = New-Object System.Threading.Mutex($false, $mutexName, [ref]$created)
try {
    try {
        $owns = $probe.WaitOne(0)
    }
    catch [System.Threading.AbandonedMutexException] {
        $owns = $probe.WaitOne(0)
    }
    if (-not $owns) {
        exit 0
    }
}
finally {
    if ($probe) {
        try { $probe.ReleaseMutex() } catch { }
        $probe.Dispose()
    }
}

$logDir = Join-Path $root "logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }

$pythonw = Join-Path $root ".venv\Scripts\pythonw.exe"
$mainPy = Join-Path $root "main.py"
Start-Process -FilePath $pythonw -ArgumentList "`"$mainPy`" --schedule" `
    -WorkingDirectory $root -WindowStyle Hidden | Out-Null

Start-Sleep -Seconds 3
$procs = @(Get-SchedulerProcs)
if ($procs.Count -gt 1) {
    $procs | Select-Object -Skip 1 | ForEach-Object {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
}
