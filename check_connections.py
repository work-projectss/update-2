"""Connectivity check — no WhatsApp send."""
from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

import requests

from src.config_loader import load_config
from src.vicidial_client import VicidialClient


def check_vicidial() -> tuple[bool, str]:
    config = load_config()
    client = VicidialClient(config)
    try:
        html = client.fetch_report(report_date=date.today())
        if "Invalid Username/Password" in html:
            return False, "Invalid credentials"
        if len(html) < 500:
            return False, f"Unexpected short response ({len(html)} bytes)"
        teams = client.resolve_teams()
        waits = client.fetch_campaign_wait_times()
        return True, f"OK — {len(teams)} teams, {len(waits)} wait entries"
    except Exception as exc:
        return False, str(exc)


def check_green_api() -> tuple[bool, str]:
    instance = os.environ.get("GREEN_API_INSTANCE_ID", "").strip()
    token = os.environ.get("GREEN_API_TOKEN", "").strip()
    if not instance or not token:
        return False, "Missing GREEN_API_INSTANCE_ID or GREEN_API_TOKEN in .env"
    url = f"https://api.green-api.com/waInstance{instance}/getStateInstance/{token}"
    try:
        r = requests.get(url, timeout=30)
        data = r.json()
        state = data.get("stateInstance", data)
        if r.status_code == 200 and state == "authorized":
            return True, f"OK — stateInstance={state}"
        return False, f"HTTP {r.status_code} — {data}"
    except Exception as exc:
        return False, str(exc)


def main() -> None:
    print("=== Connectivity (no send) ===")
    ok_v, msg_v = check_vicidial()
    print(f"Vicidial: {'PASS' if ok_v else 'FAIL'} — {msg_v}")
    ok_g, msg_g = check_green_api()
    print(f"Green API: {'PASS' if ok_g else 'FAIL'} — {msg_g}")
    sys.exit(0 if ok_v and ok_g else 1)


if __name__ == "__main__":
    main()
