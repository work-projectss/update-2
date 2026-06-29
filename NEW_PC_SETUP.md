# Run on a new Windows PC (same as main machine)

## Before you start

1. **One active scheduler only** — if both PCs run at the same time with the same Green API groups, WhatsApp gets **duplicate messages** every slot.
2. Copy the whole **`Update_2`** folder to the new PC (zip/USB/network). Include **`.env`** (credentials).
3. On the **old PC**, stop the scheduler if you are **moving** (not backup):

```cmd
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*Update_2*main.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
```

---

## Quick setup (recommended)

### Step 1 — Install Python

- Download Python **3.10+** from https://www.python.org/downloads/
- During install, tick **“Add python.exe to PATH”**

### Step 2 — Copy project

Example target folder:

```
C:\Projects\Update_2
```

Must include: `main.py`, `src\`, `config\`, `config.yaml`, all `.bat` / `.vbs` / `.ps1` files, and **`.env`**.

You can skip copying `.venv`, `logs\`, and `output\` — the installer recreates them.

### Step 3 — Run the installer

Double-click:

```
SETUP_NEW_PC.bat
```

Or from Command Prompt:

```cmd
cd C:\Projects\Update_2
SETUP_NEW_PC.bat
```

The installer will:

| Step | What it does |
|------|----------------|
| 1 | Check Python 3.10+ |
| 2 | Create `.venv` and install `requirements.txt` |
| 3 | Ensure `.env` exists (copy from `.env.example` if missing) |
| 4 | Create `logs\` and `output\` |
| 5 | Test Vicidial + Green API (**no send**) |
| 6 | Show today’s schedule |
| 7 | Start hidden scheduler + add **Startup** shortcut |

At the end you can optionally:

- Install **Windows tasks** (logon + 5‑min watchdog) — needs Administrator
- Send **one test report**

### Step 4 — Windows tasks (optional but recommended)

Right-click **`install_windows_task.bat`** → **Run as administrator**

Installs:

- **Alpha1 Vicidial WhatsApp Scheduler** — at logon (S4U, locked screen OK)
- **Alpha1 Vicidial WhatsApp Watchdog** — every 5 minutes, silent restart if scheduler died

Both run hidden via `watchdog_hidden.vbs` / `start_scheduler_hidden.vbs` (no CMD popups).

---

## Verify it is running

```cmd
cd C:\Projects\Update_2
.venv\Scripts\python.exe main.py --check-schedule
type logs\scheduler.heartbeat
type logs\scheduler.log
```

- **Heartbeat** should update every minute (e.g. `2026-06-29T08:15:00`).
- **scheduler.log** should show `Scheduler started` and minute ticks.

Manual start anytime:

```cmd
ensure_scheduler.bat
```

---

## Daily requirements

- PC **powered on** during business hours
- User **logged in** (Sign out breaks background tasks)
- **Lock screen** is fine (Win+L)
- Network to `alpha1.onvoip.co.za` and Green API

---

## Schedule (Mon–Fri)

| Time | Caption | Groups |
|------|---------|--------|
| 08:30 | `*Good morning*` | Default only |
| :00 / :30 | (image only) | Default |
| 10:01 | `*Tea_Time*` | Both |
| 13:31 | `*Lunch_Time*` | Both |
| 16:01 | `*2nd_Tea*` | Both |
| 19:05 | `*EOD*` | Both |

**Saturday:** 09:30–13:30 every 30 min + **11:01 Tea_Time** (both). **Sunday:** off.

---

## Useful commands

```cmd
.venv\Scripts\python.exe check_connections.py
.venv\Scripts\python.exe main.py --check-schedule
.venv\Scripts\python.exe main.py --once --dry-run --force
.venv\Scripts\python.exe main.py --once --force
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| No sends | Check `logs\scheduler.log`; run `ensure_scheduler.bat` |
| Heartbeat stale | Scheduler stopped — run `SETUP_NEW_PC.bat` or `ensure_scheduler.bat` |
| Duplicate messages | Two PCs both running — stop scheduler on one |
| Connectivity FAIL | Edit `.env`; check Vicidial login and Green API `authorized` state |
| Tasks not running | Run `install_windows_task.bat` as admin; stay logged in |

---

## Files that keep it running

| File | Role |
|------|------|
| `start_scheduler_hidden.vbs` | Hidden launcher (Startup + logon task) |
| `watchdog_hidden.vbs` | Silent watchdog (5‑min task) |
| `start_scheduler.ps1` | Starts `pythonw main.py --schedule` if heartbeat &gt; 90s |
| `ensure_scheduler.bat` | Manual “start now” |
| `logs\scheduler.heartbeat` | Updated every minute when healthy |
