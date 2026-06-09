#!/usr/bin/env python3
"""Alpha1 Vicidial -> WhatsApp performance updates."""

from __future__ import annotations

import argparse
import ctypes
import logging
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from datetime import date, datetime, timedelta
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.config_loader import load_config  # noqa: E402
from src.image_report import generate_report_image  # noqa: E402
from src.report import format_whatsapp_message  # noqa: E402
from src.report import PerformanceReportBuilder  # noqa: E402
from src.schedule_rules import (  # noqa: E402
    active_window_label,
    get_caption,
    list_todays_fire_times,
    next_run_after_suspend,
    reload_rules,
    run_key,
    should_fire_now,
    should_run,
    uses_dual_groups,
)
from src.vicidial_client import VicidialClient  # noqa: E402
from src.whatsapp import WhatsAppSender  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("alpha1-update")

_MUTEX_NAME = "Alpha1WhatsAppScheduler_Update2"
_SEND_LOCK = threading.Lock()
_SEND_JOB_TIMEOUT_SEC = 600
_GRACE_MINUTES = 10


def _setup_file_logging(filename: str) -> None:
    log_dir = ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    path = str(log_dir / filename)
    root = logging.getLogger()
    for existing in root.handlers:
        if isinstance(existing, logging.FileHandler) and existing.baseFilename == path:
            return
    handler = logging.FileHandler(path, encoding="utf-8", delay=True)
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )
    root.addHandler(handler)


def _slot_marker_path() -> Path:
    return ROOT / "logs" / "last_slot.txt"


def _sent_slots_path() -> Path:
    return ROOT / "logs" / "sent_slots.txt"


def _load_sent_slots() -> set[str]:
    path = _sent_slots_path()
    if not path.is_file():
        return set()
    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


def _already_sent_this_run(now: datetime) -> bool:
    key = run_key(now)
    if key in _load_sent_slots():
        return True
    path = _slot_marker_path()
    if path.is_file():
        return path.read_text(encoding="utf-8").strip() == key
    return False


def _mark_run_sent(now: datetime) -> None:
    key = run_key(now)
    sent_path = _sent_slots_path()
    sent_path.parent.mkdir(exist_ok=True)
    sent = _load_sent_slots()
    if key not in sent:
        with sent_path.open("a", encoding="utf-8") as fh:
            fh.write(f"{key}\n")
    path = _slot_marker_path()
    path.write_text(key, encoding="utf-8")


def _write_heartbeat() -> None:
    path = ROOT / "logs" / "scheduler.heartbeat"
    path.parent.mkdir(exist_ok=True)
    path.write_text(datetime.now().isoformat(timespec="seconds"), encoding="utf-8")


def _send_hold_until(now: datetime) -> datetime | None:
    """Optional logs/no_send_until.txt (ISO local time) blocks all sends until that time."""
    path = ROOT / "logs" / "no_send_until.txt"
    if not path.is_file():
        return None
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return None
    try:
        hold_until = datetime.fromisoformat(raw)
    except ValueError:
        log.warning("Invalid no_send_until.txt: %r", raw)
        return None
    if now < hold_until:
        return hold_until
    return None


def _acquire_mutex() -> bool:
    handle = ctypes.windll.kernel32.CreateMutexW(None, True, _MUTEX_NAME)
    return ctypes.windll.kernel32.GetLastError() != 183


def run_update(
    *,
    report_date: date | None = None,
    send: bool = True,
    caption: str | None = None,
) -> str | None:
    config = load_config()
    client = VicidialClient(config)
    builder = PerformanceReportBuilder(config, client)

    teams = client.resolve_teams(report_date=report_date)
    log.info(
        "Building report for %s (%d teams, %d campaigns)...",
        report_date or date.today(),
        len(teams),
        len(config.campaigns),
    )
    report = builder.build(report_date=report_date)
    generated_at = datetime.now()
    message = format_whatsapp_message(report, generated_at=generated_at)

    image_path = None
    if config.whatsapp_send_as_image:
        stamp = generated_at.strftime("%Y%m%d_%H%M%S")
        image_path = ROOT / "output" / f"performance_{stamp}.png"
        generate_report_image(report, image_path, generated_at=generated_at)
        log.info("Report image: %s", image_path)

    if send:
        cap = get_caption(generated_at) if caption is None else caption
        sender = WhatsAppSender(config)
        targets = sender._chat_ids_for_caption(cap, at=generated_at)
        log.info("WhatsApp targets (%d): %s", len(targets), ", ".join(targets))
        if image_path:
            sender.send(cap, image_path=image_path, at=generated_at)
        else:
            sender.send(message)
    return message


def _resolve_fire_time(now: datetime, *, force: bool) -> datetime | None:
    """Exact slot time to send, with grace if a slot was missed."""
    if force:
        return now.replace(second=0, microsecond=0)
    tick = now.replace(second=0, microsecond=0)
    if should_fire_now(tick):
        return tick
    for minutes_ago in range(1, _GRACE_MINUTES + 1):
        probe = tick - timedelta(minutes=minutes_ago)
        if should_fire_now(probe) and not _already_sent_this_run(probe):
            log.info("Grace catch-up for missed slot %s", run_key(probe))
            return probe
    return None


def _run_if_scheduled(*, send: bool, force: bool) -> int:
    now = datetime.now()
    reload_rules()

    fire_at = _resolve_fire_time(now, force=force)
    if not force and fire_at is None:
        if not should_run(now):
            wd = now.weekday()
            if wd == 6:
                nxt = next_run_after_suspend(now)
                log.info(
                    "Sunday — suspended. Next run Monday %s.",
                    nxt.strftime("%Y-%m-%d %H:%M"),
                )
            else:
                log.info(
                    "Outside active window (%s). Skipping.",
                    active_window_label(now),
                )
        return 0

    fire_at = fire_at or now.replace(second=0, microsecond=0)

    if send and not force and _already_sent_this_run(fire_at):
        log.info("Run %s already sent — skipping duplicate.", run_key(fire_at))
        return 0

    hold_until = _send_hold_until(fire_at) if send and not force else None
    if hold_until is not None:
        log.info(
            "Send held until %s — skipping slot %s.",
            hold_until.strftime("%H:%M"),
            run_key(fire_at),
        )
        return 0

    caption = get_caption(fire_at)
    dual = uses_dual_groups(caption)
    log.info(
        "Sending update (caption: %s, groups: %s)",
        caption if caption else "(none)",
        "both" if dual else "default",
    )

    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            run_update(report_date=None, send=send, caption=caption)
            if send:
                _mark_run_sent(fire_at)
            return 0
        except Exception as exc:
            last_error = exc
            log.exception("Update failed (attempt %d/3)", attempt)
            if attempt < 3:
                time.sleep(30)

    log.error("All retries failed: %s", last_error)
    return 1


def _run_send_job(*, send: bool) -> None:
    """Run one scheduled send with a hard timeout so the lock cannot stick forever."""
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            fut = pool.submit(_run_if_scheduled, send=send, force=False)
            fut.result(timeout=_SEND_JOB_TIMEOUT_SEC)
    except FuturesTimeout:
        log.error(
            "Send job timed out after %ds — slot can retry via grace.",
            _SEND_JOB_TIMEOUT_SEC,
        )
    except Exception:
        log.exception("Send job failed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Run one update")
    parser.add_argument("--dry-run", action="store_true", help="No WhatsApp send")
    parser.add_argument("--force", action="store_true", help="Ignore schedule window")
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Keep running; fire at each scheduled minute",
    )
    parser.add_argument(
        "--check-schedule",
        action="store_true",
        help="Show today's send times and current slot",
    )
    parser.add_argument("--date", type=str, default=None, help="Report date YYYY-MM-DD")
    args = parser.parse_args()

    report_date = date.fromisoformat(args.date) if args.date else None
    send = not args.dry_run

    if args.check_schedule:
        reload_rules()
        now = datetime.now()
        print("Now:", now.strftime("%A %Y-%m-%d %H:%M"))
        print("Window:", active_window_label(now))
        print("Active now:", should_run(now))
        print("Would fire now:", should_fire_now(now))
        print("Caption now:", get_caption(now) or "(none — image only)")
        print()
        print("Today's send times:")
        for line in list_todays_fire_times(now):
            print(" ", line)
        if now.weekday() == 6:
            print("Next run:", next_run_after_suspend(now).strftime("%A %Y-%m-%d %H:%M"))
        return

    if args.schedule:
        _setup_file_logging("scheduler.log")
        if not _acquire_mutex():
            log.warning("Scheduler already running — exiting.")
            sys.exit(0)

        scheduler = BlockingScheduler()

        def _tick() -> None:
            _write_heartbeat()

            def _work() -> None:
                if not _SEND_LOCK.acquire(blocking=False):
                    log.info("Send already in progress — tick skipped.")
                    return
                try:
                    _run_send_job(send=send)
                    _run_send_job(send=send)
                finally:
                    _SEND_LOCK.release()

            threading.Thread(target=_work, daemon=True, name="alpha1-send").start()

        scheduler.add_job(
            _tick,
            CronTrigger(minute="*"),
            id="alpha1_schedule_tick",
            max_instances=3,
            coalesce=True,
            misfire_grace_time=120,
        )

        log.info("Scheduler started. %s", active_window_label())
        log.info(
            "Mon-Fri 08:30 Good morning (single), then 30 min image-only + "
            "10:01 Tea_Time, 13:31 Lunch_Time, 16:01 2nd_Tea, 19:10 EOD (both groups). "
            "Sat 09:30-13:30 every 30 min + 11:01 Tea_Time (both groups)."
        )
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            log.info("Scheduler stopped")
        return

    if args.once:
        _setup_file_logging("task.log")
        if report_date:
            run_update(report_date=report_date, send=send, caption=get_caption())
        else:
            code = _run_if_scheduled(send=send, force=args.force)
            if args.dry_run:
                latest = sorted((ROOT / "output").glob("performance_*.png"))
                if latest:
                    print(f"\nLatest image: {latest[-1]}")
            sys.exit(code)
        return

    message = run_update(report_date=report_date, send=send, caption=get_caption())
    if args.dry_run or not send:
        print(message)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        _setup_file_logging("task.log")
        logging.getLogger("alpha1-update").exception("Fatal error")
        sys.exit(1)
