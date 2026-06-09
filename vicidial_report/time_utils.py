import re
from typing import Optional


_TIME_RE = re.compile(r"^(\d+):(\d{2}):(\d{2})$")


def parse_duration_to_hours(value: str) -> float:
    """Convert H:MM:SS or M:SS style durations to decimal hours."""
    value = (value or "").strip()
    if not value or value in ("-", "0", "0:00:00", "0:00"):
        return 0.0

    if _TIME_RE.match(value):
        h, m, s = map(int, value.split(":"))
        return h + m / 60 + s / 3600

    parts = value.split(":")
    try:
        if len(parts) == 2:
            return int(parts[0]) / 60 + int(parts[1]) / 3600
        if len(parts) == 3:
            return int(parts[0]) + int(parts[1]) / 60 + int(parts[2]) / 3600
    except ValueError:
        pass
    return 0.0


def parse_duration_to_seconds(value: str) -> int:
    return int(round(parse_duration_to_hours(value) * 3600))


def format_hours(hours: float) -> str:
    if hours <= 0:
        return "0.00"
    return f"{hours:.2f}"


def format_pct(value: float) -> str:
    return f"{value:.1f}%"
