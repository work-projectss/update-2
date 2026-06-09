from __future__ import annotations

import re
from dataclasses import dataclass

from vicidial_report.parser import parse_campaign_totals


@dataclass
class AgentPerformanceSummary:
    headcount: int
    total_calls: int
    hours: int
    status_counts: dict[str, int]


def parse_agent_performance_report(html: str) -> AgentPerformanceSummary:
    """
    Parse Vicidial Agent Performance Detail (CALL STATS + PAUSE TOTALS).
    Uses column-index mapping so SALE / BSALE align correctly on alpha1 reports.
    """
    totals = parse_campaign_totals(html)
    status_counts: dict[str, int] = {}
    if totals.sale:
        status_counts["SALE"] = totals.sale
    if totals.bsale:
        status_counts["BSALE"] = totals.bsale

    return AgentPerformanceSummary(
        headcount=totals.headcount,
        total_calls=totals.calls,
        hours=int(round(totals.hrs)),
        status_counts=status_counts,
    )


def sum_statuses(status_counts: dict[str, int], codes: list[str]) -> int:
    total = 0
    seen: set[str] = set()
    for code in codes:
        key = code.upper()
        if key in seen:
            continue
        seen.add(key)
        total += status_counts.get(key, 0)
    return total


_USER_GROUP_SELECT = re.compile(
    r'<SELECT[^>]*NAME\s*=\s*["\']user_group\[\]["\'][^>]*>(.*?)</SELECT>',
    re.I | re.S,
)
_OPTION_VALUE = re.compile(
    r'<option\s+value\s*=\s*["\']([^"\']+)["\']',
    re.I,
)


def discover_user_groups(html: str) -> list[str]:
    """Read team names from the Vicidial report form (updates when teams change)."""
    match = _USER_GROUP_SELECT.search(html)
    if not match:
        return []
    groups: list[str] = []
    for value in _OPTION_VALUE.findall(match.group(1)):
        name = value.strip()
        if not name or name == "--ALL--" or name.startswith("--"):
            continue
        if name not in groups:
            groups.append(name)
    return groups
