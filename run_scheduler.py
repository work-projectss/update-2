#!/usr/bin/env python3
"""
Send the live report to WhatsApp every N minutes (default 30).

Keep this running in the background, or use Windows Task Scheduler
to run run_report.py every 30 minutes instead.
"""

from __future__ import annotations

import os
import sys
import time
import traceback
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv

from vicidial_report.build import build_live_report
from vicidial_report.report import format_whatsapp_message
from vicidial_report.whatsapp import get_whatsapp_sender

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")


def _in_business_hours() -> bool:
    if os.getenv("BUSINESS_HOURS_ONLY", "false").lower() not in ("1", "true", "yes"):
        return True
    now = datetime.now().time()
    start = os.getenv("BUSINESS_START", "08:30")
    end = os.getenv("BUSINESS_END", "19:02")
    sh, sm = map(int, start.split(":")[:2])
    eh, em = map(int, end.split(":")[:2])
    from datetime import time as dt_time

    return dt_time(sh, sm) <= now <= dt_time(eh, em)


def _weekday_allowed() -> bool:
    if os.getenv("WEEKDAYS_ONLY", "true").lower() not in ("1", "true", "yes"):
        return True
    return date.today().weekday() < 5


def run_once(sender) -> bool:
    report = build_live_report()
    message = format_whatsapp_message(report)
    sender.send(message)
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Report sent ({len(message)} chars)")
    return True


def main() -> int:
    interval = int(os.getenv("UPDATE_INTERVAL_MINUTES", "30"))
    sender = get_whatsapp_sender()
    if not sender:
        print("Set WHATSAPP_PROVIDER=greenapi and GREENAPI_* in .env", file=sys.stderr)
        return 1

    print(f"Scheduler started: every {interval} minutes. Ctrl+C to stop.")
    while True:
        try:
            if _weekday_allowed() and _in_business_hours():
                run_once(sender)
            else:
                print(f"[{datetime.now():%H:%M:%S}] Skipped (outside hours/weekday)")
        except Exception:
            traceback.print_exc()

        time.sleep(interval * 60)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nStopped.")
        sys.exit(0)
