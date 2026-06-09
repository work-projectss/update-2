#!/usr/bin/env python3
"""Run one live report and send to WhatsApp."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

from vicidial_report.build import build_live_report
from vicidial_report.report import format_whatsapp_message
from vicidial_report.whatsapp import get_whatsapp_sender


def main() -> int:
    load_dotenv(Path(__file__).parent / ".env")

    parser = argparse.ArgumentParser(description="VICIdial live report to WhatsApp")
    parser.add_argument("--dry-run", action="store_true", help="Print only, do not send")
    parser.add_argument("--save", metavar="FILE", help="Save report to file")
    parser.add_argument("--date", metavar="YYYY-MM-DD", help="Report date (default: today)")
    args = parser.parse_args()

    report_date = date.fromisoformat(args.date) if args.date else date.today()

    try:
        print(f"Building report for {report_date}...")
        report = build_live_report(report_date)
        message = format_whatsapp_message(report)
        print(message)

        if args.save:
            Path(args.save).write_text(message, encoding="utf-8")

        if args.dry_run:
            return 0

        sender = get_whatsapp_sender()
        if not sender:
            print("Configure Green API in .env (WHATSAPP_PROVIDER=greenapi)", file=sys.stderr)
            return 1

        sender.send(message)
        print("\nSent to WhatsApp.")
        return 0

    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
