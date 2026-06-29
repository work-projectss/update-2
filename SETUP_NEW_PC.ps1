# One-time setup for a new Windows PC. No WhatsApp send unless you choose test send.
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
Set-Location $root

function Write-Step($n, $msg) {
    Write-Host ""
    Write-Host "[$n] $msg" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "  Alpha1 Vicidial WhatsApp — New PC setup" -ForegroundColor White
Write-Host "  ========================================" -ForegroundColor White
Write-Host "  Folder: $root"
Write-Host ""

# --- 1. Python ---
Write-Step "1/7" "Checking Python..."
$py = $null
foreach ($cmd in @("python", "py")) {
    try {
        $v = & $cmd -c "import sys; print(sys.version_info[0], sys.version_info[1])" 2>$null
        if ($v) {
            $parts = $v.Trim() -split '\s+'
            if ([int]$parts[0] -ge 3 -and [int]$parts[1] -ge 10) {
                $py = $cmd
                break
            }
        }
    } catch { }
}
if (-not $py) {
    Write-Host "FAIL: Python 3.10+ not found." -ForegroundColor Red
    Write-Host "Install from https://www.python.org/downloads/ and tick 'Add python.exe to PATH'."
    exit 1
}
Write-Host "OK: $py ($(& $py --version))"

# --- 2. Virtual environment ---
Write-Step "2/7" "Virtual environment (.venv)..."
$venvPy = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    & $py -m venv (Join-Path $root ".venv")
    if (-not (Test-Path $venvPy)) {
        Write-Host "FAIL: Could not create .venv" -ForegroundColor Red
        exit 1
    }
    Write-Host "Created .venv"
} else {
    Write-Host "Already exists"
}

$pip = Join-Path $root ".venv\Scripts\pip.exe"
& $pip install -q -r (Join-Path $root "requirements.txt")
Write-Host "Dependencies installed"

# --- 3. .env ---
Write-Step "3/7" "Credentials (.env)..."
$envFile = Join-Path $root ".env"
$envExample = Join-Path $root ".env.example"
if (-not (Test-Path $envFile)) {
    if (Test-Path $envExample) {
        Copy-Item $envExample $envFile
        Write-Host "Created .env from .env.example — EDIT IT before going live." -ForegroundColor Yellow
    } else {
        Write-Host "FAIL: No .env or .env.example" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "Found .env"
}

$envText = Get-Content $envFile -Raw
$needsEdit = $false
foreach ($needle in @("your_username", "your_password", "your_group_id", "your-evolution-server")) {
    if ($envText -match $needle) { $needsEdit = $true }
}
if ($needsEdit) {
    Write-Host "WARNING: .env still has placeholder values — edit before sending." -ForegroundColor Yellow
}

# --- 4. Folders ---
Write-Step "4/7" "Log folders..."
$logDir = Join-Path $root "logs"
$outDir = Join-Path $root "output"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir | Out-Null }
Write-Host "logs\ and output\ ready"

# --- 5. Connectivity (no send) ---
Write-Step "5/7" "Connectivity test (no WhatsApp send)..."
$check = Join-Path $root ".venv\Scripts\python.exe"
& $check (Join-Path $root "check_connections.py")
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Connectivity failed — fix .env / network, then run:" -ForegroundColor Yellow
    Write-Host "  .venv\Scripts\python.exe check_connections.py"
    $continue = Read-Host "Continue setup anyway? (y/N)"
    if ($continue -notmatch '^y') { exit 1 }
}

# --- 6. Schedule preview ---
Write-Step "6/7" "Today's schedule..."
& $check (Join-Path $root "main.py") --check-schedule

# --- 7. Background + startup ---
Write-Step "7/7" "Start scheduler + Startup shortcut..."
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like "*$root*main.py*" } |
    ForEach-Object {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }

wscript //nologo (Join-Path $root "start_scheduler_hidden.vbs")
Start-Sleep -Seconds 4

$startup = [Environment]::GetFolderPath("Startup")
$lnkPath = Join-Path $startup "Alpha1 WhatsApp Scheduler.lnk"
$shell = New-Object -ComObject WScript.Shell
$lnk = $shell.CreateShortcut($lnkPath)
$lnk.TargetPath = "wscript.exe"
$lnk.Arguments = '"' + (Join-Path $root "start_scheduler_hidden.vbs") + '"'
$lnk.WorkingDirectory = $root
$lnk.WindowStyle = 7
$lnk.Description = "Alpha1 Vicidial WhatsApp scheduler"
$lnk.Save()
Write-Host "Startup shortcut: $lnkPath"

$hb = Join-Path $root "logs\scheduler.heartbeat"
if (Test-Path $hb) {
    Write-Host "Heartbeat: $(($(Get-Content $hb -Raw).Trim()))"
} else {
    Write-Host "Heartbeat file not yet created — wait 1 minute." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Setup complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "IMPORTANT: Run the scheduler on ONE PC only (avoid duplicate WhatsApp messages)."
Write-Host ""
Write-Host "Optional (recommended): Right-click install_windows_task.bat -> Run as administrator"
Write-Host "  - Starts scheduler at logon (locked screen OK)"
Write-Host "  - Watchdog every 5 min if scheduler stops"
Write-Host ""
Write-Host "Stay logged in. Lock screen (Win+L) is fine. PC must be ON during business hours."
Write-Host "Log: $root\logs\scheduler.log"
Write-Host ""

$installTasks = Read-Host "Install Windows tasks now as Administrator? (y/N)"
if ($installTasks -match '^y') {
    Start-Process powershell.exe -Verb RunAs -ArgumentList @(
        "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
        "`"$(Join-Path $root 'install_windows_task.ps1')`""
    )
}

$testSend = Read-Host "Send one test report now? (y/N)"
if ($testSend -match '^y') {
    & $check (Join-Path $root "main.py") --once --force
}

Write-Host ""
Read-Host "Press Enter to close"
