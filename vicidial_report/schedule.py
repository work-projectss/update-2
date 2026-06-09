from __future__ import annotations

from datetime import date, timedelta


def monday_of_week(d: date | None = None) -> date:
    d = d or date.today()
    return d - timedelta(days=d.weekday())


def friday_of_week(d: date | None = None) -> date:
    return monday_of_week(d) + timedelta(days=4)


def weekday_count(start: date, end: date) -> int:
    """Count Mon–Fri days in inclusive range."""
    count = 0
    current = start
    while current <= end:
        if current.weekday() < 5:
            count += 1
        current += timedelta(days=1)
    return max(count, 0)
