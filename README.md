# Alpha1 Vicidial → WhatsApp performance updates

Pulls **Agent Performance Detail** and **Wait(sec)** from alpha1 Vicidial, builds a PNG matching your spreadsheet layout, and sends it to WhatsApp every 30 minutes via Green API.

## Setup (Command Prompt)

```cmd
cd c:\Projects\Update_2
python -m venv .venv
.venv\Scripts\pip.exe install -r requirements.txt
copy .env.example .env
```

Edit `.env`:

- `VICIDIAL_USER` / `VICIDIAL_PASSWORD` — report login
- `GREEN_API_INSTANCE_ID` / `GREEN_API_TOKEN` / `WHATSAPP_TO` — Green API (group id ends with `@g.us`)

Edit `config.yaml` for campaigns, team targets, and schedule.

## Schedule (automatic sends)

| Day | Active | Interval | Special captions |
|-----|--------|----------|----------------|
| **Mon–Fri** | 08:30 – 19:02 | 30 min | **\*LUNCH_TIME\*** at 13:30, normal from 14:00, **\*EOD\*** at 19:02 |
| **Saturday** | 09:30 – 13:02 | 30 min | `Tea_Time` at 11:00, normal from 11:30, **\*EOD\*** at 13:02 |
| **Sunday** | Off | — | Suspended until Monday 08:30 |

**Dual WhatsApp groups** (`lunch_eod_groups` in `config.yaml`): Mon–Fri **LUNCH_TIME** + **EOD**; Saturday **Tea_Time** + **EOD**. All other slots use `WHATSAPP_TO` only.

Check the current slot:

```cmd
.venv\Scripts\python.exe main.py --check-schedule
```

## Run

| Goal | Command |
|------|---------|
| Preview (no WhatsApp) | `.venv\Scripts\python.exe main.py --once --dry-run --force` |
| Send once (if in window) | `.venv\Scripts\python.exe main.py --once` |
| Test outside hours | add `--force` |
| Every 30 min (window open) | `.venv\Scripts\python.exe main.py --schedule` |

Or double-click `run_dry_run.bat`, `run_update.bat`, or `run_scheduler.bat`.

## Run when your PC is off

The script cannot run if the computer is **powered off**. For “always on” behaviour:

1. Use a PC or server that stays on during business hours, **or**
2. Install the Windows task (runs every 30 min; Python skips outside hours):

```powershell
cd c:\Projects\Update_2
.\install_windows_task.ps1
```

Set `WHATSAPP_TO` in `.env` to your group id before going live.

PNG files are saved under `output\`.

## Data source

- Performance: `http://alpha1.onvoip.co.za/vicidial/AST_agent_performance_detail.php`
- Wait(sec): `http://alpha1.onvoip.co.za/vicidial/AST_timeonVDADallSUMMARY.php`

Metrics: **SALE**, **BSALE**, hours from **NONPAUSE** totals, headcount from **AGENTS** (teams summed for campaign rows).

## Security

Do not commit `.env`. Rotate passwords if they were shared in chat.
