"""Business hours, weekend rules, and WhatsApp caption labels."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, time as dtime
from typing import Any

DUAL_CAPTIONS = frozenset({"TEA_TIME", "LUNCH_TIME", "2ND_TEA", "2ND_TIME"})


@dataclass(frozen=True)
class WeekdaySchedule:
    start: dtime
    good_morning_at: dtime
    good_morning_caption: str
    stop: dtime
    tea_at: dtime
    tea_caption: str
    tea_resume_at: dtime
    lunch_at: dtime
    lunch_caption: str
    lunch_resume_at: dtime
    second_tea_at: dtime
    second_tea_caption: str
    second_tea_resume_at: dtime
    eod_at: dtime
    interval_seconds: int


@dataclass(frozen=True)
class SaturdaySchedule:
    start: dtime
    stop: dtime
    tea_at: dtime
    tea_caption: str
    tea_resume_at: dtime
    interval_seconds: int


@dataclass(frozen=True)
class ScheduleRules:
    weekday: WeekdaySchedule
    saturday: SaturdaySchedule

    @classmethod
    def from_config(cls, raw: dict[str, Any]) -> ScheduleRules:
        interval = int(raw.get("interval_seconds", 1800))
        wd = raw.get("weekdays", {})
        sat = raw.get("saturday", {})

        return cls(
            weekday=WeekdaySchedule(
                start=_parse_time(wd.get("start_time", "08:30")),
                good_morning_at=_parse_time(
                    wd.get("good_morning_time", wd.get("start_time", "08:30"))
                ),
                good_morning_caption=str(
                    wd.get("good_morning_caption", "Good morning")
                ),
                stop=_parse_time(wd.get("stop_time", "19:10")),
                tea_at=_parse_time(wd.get("tea_time", "10:01")),
                tea_caption=str(wd.get("tea_caption", "Tea_Time")),
                tea_resume_at=_parse_time(wd.get("tea_resume_time", "10:30")),
                lunch_at=_parse_time(wd.get("lunch_time", "13:01")),
                lunch_caption=str(wd.get("lunch_caption", "Lunch_Time")),
                lunch_resume_at=_parse_time(wd.get("lunch_resume_time", "13:30")),
                second_tea_at=_parse_time(wd.get("second_tea_time", "16:01")),
                second_tea_caption=str(wd.get("second_tea_caption", "2nd_Time")),
                second_tea_resume_at=_parse_time(
                    wd.get("second_tea_resume_time", "16:30")
                ),
                eod_at=_parse_time(wd.get("eod_time", "19:10")),
                interval_seconds=int(wd.get("interval_seconds", interval)),
            ),
            saturday=SaturdaySchedule(
                start=_parse_time(sat.get("start_time", "09:30")),
                stop=_parse_time(sat.get("stop_time", "13:30")),
                tea_at=_parse_time(sat.get("tea_time", "11:01")),
                tea_caption=str(sat.get("tea_caption", "Tea_Time")),
                tea_resume_at=_parse_time(sat.get("tea_resume_time", "11:30")),
                interval_seconds=int(sat.get("interval_seconds", interval)),
            ),
        )


def _parse_time(value: str) -> dtime:
    parts = value.strip().split(":")
    h, m = int(parts[0]), int(parts[1])
    return dtime(h, m)


def _clock(now: datetime) -> dtime:
    return now.time().replace(second=0, microsecond=0)


def _time_to_minutes(t: dtime) -> int:
    return t.hour * 60 + t.minute


def _bold_whatsapp(label: str) -> str:
    clean = label.strip().strip("*")
    return f"*{clean}*"


def caption_label(caption: str) -> str:
    return caption.strip().strip("*").upper().replace(" ", "_")


def uses_dual_groups(caption: str) -> bool:
    """Tea_Time, Lunch_Time, 2nd_Time -> both WhatsApp groups."""
    return caption_label(caption) in DUAL_CAPTIONS


def uses_lunch_eod_groups(caption: str, now: datetime | None = None) -> bool:
    """Backward-compatible alias for whatsapp routing."""
    return uses_dual_groups(caption)


def _in_time_window(clock: dtime, start: dtime, stop: dtime) -> bool:
    return _time_to_minutes(start) <= _time_to_minutes(clock) <= _time_to_minutes(stop)


def should_run(now: datetime | None = None) -> bool:
    """Broad active window (Mon-Fri or Sat)."""
    now = now or datetime.now()
    clock = _clock(now)
    rules = _rules()
    wd = now.weekday()
    if wd <= 4:
        return _in_time_window(clock, rules.weekday.start, rules.weekday.stop)
    if wd == 5:
        return _in_time_window(clock, rules.saturday.start, rules.saturday.stop)
    return False


def _weekday_special_at(clock: dtime) -> str | None:
    w = _rules().weekday
    if clock == w.tea_at:
        return w.tea_caption
    if clock == w.lunch_at:
        return w.lunch_caption
    if clock == w.second_tea_at:
        return w.second_tea_caption
    return None


def _saturday_special_at(clock: dtime) -> str | None:
    s = _rules().saturday
    if clock == s.tea_at:
        return s.tea_caption
    return None


def _special_caption_at(now: datetime) -> str | None:
    clock = _clock(now)
    wd = now.weekday()
    if wd <= 4:
        return _weekday_special_at(clock)
    if wd == 5:
        return _saturday_special_at(clock)
    return None


def is_special_slot(now: datetime) -> bool:
    return _special_caption_at(now) is not None


def _skip_regular_before_lunch(clock: dtime, w: WeekdaySchedule) -> bool:
    """
  After :00, skip the :30 slot in the lunch hour when lunch is after :30
  (e.g. 13:00 regular -> 13:31 lunch -> 14:00 resume; no 13:30).
    """
    if clock.minute != 30 or clock.hour != w.lunch_at.hour:
        return False
    return w.lunch_at.minute > 30


def is_regular_slot(now: datetime) -> bool:
    """Every 30 minutes on :00 and :30 within the active window."""
    if now.minute not in (0, 30):
        return False
    clock = _clock(now)
    rules = _rules()
    wd = now.weekday()

    if wd <= 4:
        w = rules.weekday
        if not _in_time_window(clock, w.start, w.stop):
            return False
        if _skip_regular_before_lunch(clock, w):
            return False
        return True

    if wd == 5:
        return _in_time_window(clock, rules.saturday.start, rules.saturday.stop)

    return False


def should_fire_now(now: datetime | None = None) -> bool:
    """True at exact send times: regular :00/:30 grid + weekday specials."""
    now = now or datetime.now()
    if not should_run(now):
        return False
    return is_regular_slot(now) or is_special_slot(now)


def run_key(now: datetime) -> str:
    """Unique id for deduplication (per minute)."""
    return now.strftime("%Y-%m-%dT%H:%M")


def get_caption(now: datetime | None = None) -> str:
    """
    Other regular slots: no caption (image only).
    Special slots: bold Tea_Time, Lunch_Time, 2nd_Time (Mon-Fri + Sat Tea).
    """
    now = now or datetime.now()
    if not should_fire_now(now):
        return ""

    clock = _clock(now)
    if now.weekday() <= 4:
        w = _rules().weekday
        if clock == w.good_morning_at and w.good_morning_caption.strip():
            return _bold_whatsapp(w.good_morning_caption)

    special = _special_caption_at(now)
    if special:
        return _bold_whatsapp(special)

    return ""


def active_window_label(now: datetime | None = None) -> str:
    now = now or datetime.now()
    wd = now.weekday()
    rules = _rules()
    if wd <= 4:
        w = rules.weekday
        return (
            f"Mon-Fri {w.start.strftime('%H:%M')}-{w.stop.strftime('%H:%M')} "
            f"(regular image-only from {w.start.strftime('%H:%M')}, "
            f"Tea {w.tea_at.strftime('%H:%M')}, Lunch {w.lunch_at.strftime('%H:%M')}, "
            f"2nd_Time {w.second_tea_at.strftime('%H:%M')})"
        )
    if wd == 5:
        s = rules.saturday
        return (
            f"Sat {s.start.strftime('%H:%M')}-{s.stop.strftime('%H:%M')} "
            f"(Tea {s.tea_at.strftime('%H:%M')}, resume {s.tea_resume_at.strftime('%H:%M')})"
        )
    return "Sun — off until Mon 08:30"


def next_run_after_suspend(now: datetime | None = None) -> datetime:
    now = now or datetime.now()
    rules = _rules()
    days_ahead = (7 - now.weekday()) % 7 or 7
    target = now.date() + timedelta(days=days_ahead)
    return datetime.combine(target, rules.weekday.start)


def list_todays_fire_times(now: datetime | None = None) -> list[str]:
    """Debug helper: all HH:MM send times for today."""
    now = now or datetime.now()
    rules = _rules()
    wd = now.weekday()
    times: list[str] = []
    if wd <= 4:
        w = rules.weekday
        start_m, stop_m = _time_to_minutes(w.start), _time_to_minutes(w.stop)
    elif wd == 5:
        s = rules.saturday
        start_m, stop_m = _time_to_minutes(s.start), _time_to_minutes(s.stop)
    else:
        return times

    for m in range(start_m, stop_m + 1):
        h, mi = divmod(m, 60)
        probe = now.replace(hour=h, minute=mi, second=0, microsecond=0)
        if should_fire_now(probe):
            cap = get_caption(probe)
            tag = "dual" if uses_dual_groups(cap) else "single"
            cap_txt = cap or "none"
            times.append(f"{h:02d}:{mi:02d} ({tag}, {cap_txt})")
    return times


_use_time_caption_cache: bool | None = None
_rules_cache: ScheduleRules | None = None


def _use_time_caption() -> bool:
    global _use_time_caption_cache
    if _use_time_caption_cache is None:
        import yaml
        from pathlib import Path

        path = Path(__file__).resolve().parent.parent / "config.yaml"
        with path.open(encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        _use_time_caption_cache = bool(
            raw.get("whatsapp", {}).get("use_time_caption", False)
        )
    return _use_time_caption_cache


def _rules() -> ScheduleRules:
    global _rules_cache
    if _rules_cache is None:
        import yaml
        from pathlib import Path

        path = Path(__file__).resolve().parent.parent / "config.yaml"
        with path.open(encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        _rules_cache = ScheduleRules.from_config(raw.get("schedule", {}))
    return _rules_cache


def reload_rules() -> None:
    global _rules_cache, _use_time_caption_cache
    _rules_cache = None
    _use_time_caption_cache = None
