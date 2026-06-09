from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .time_utils import parse_duration_to_hours


@dataclass
class AgentStats:
    name: str
    user_id: str
    team: str
    calls: int = 0
    sale: int = 0
    bsale: int = 0
    hrs: float = 0.0

    @property
    def total_sales(self) -> int:
        return self.sale + self.bsale


@dataclass
class CampaignTotals:
    calls: int = 0
    sale: int = 0
    bsale: int = 0
    hrs: float = 0.0
    headcount: int = 0


@dataclass
class CampaignWait:
    campaign_id: str
    agent_avg_wait_sec: int
    avg_agents: float = 0.0


def _clean_cell(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _strip_html(text: str) -> str:
    return _clean_cell(re.sub(r"<[^>]+>", "", text))


def _extract_user_id(cell: str) -> str:
    match = re.search(r"user=([A-Za-z0-9]+)", cell)
    if match:
        return match.group(1)
    return _strip_html(cell)


def _parse_pipe_table(section_html: str) -> tuple[List[str], List[List[str]]]:
    headers: List[str] = []
    rows: List[List[str]] = []

    for line in section_html.splitlines():
        line = line.strip()
        if not line.startswith("|") or line.startswith("+-") or line.startswith("+="):
            continue
        cells = [_clean_cell(c) for c in line.strip("|").split("|")]
        if not cells:
            continue
        if not headers and any("USER NAME" in c.upper() for c in cells):
            headers = cells
            continue
        if "TOTALS" in line.upper() and "AGENTS:" in line.upper():
            rows.append(cells)
            continue
        if headers and len(cells) >= 2 and "TOTALS" not in line.upper():
            rows.append(cells)

    return headers, rows


def _index_map(headers: List[str]) -> Dict[str, int]:
    mapping: Dict[str, int] = {}
    for i, h in enumerate(headers):
        key = _strip_html(h).upper()
        key = re.sub(r"\s+", " ", key)
        if key.endswith(" %"):
            continue
        if key not in mapping:
            mapping[key] = i
    return mapping


def _parse_int(value: str) -> int:
    value = _strip_html(value).replace(",", "")
    if not value or "%" in value:
        return 0
    try:
        return int(float(value))
    except ValueError:
        return 0


def _agents_from_totals_row(cells: List[str]) -> int:
    joined = " ".join(cells)
    match = re.search(r"AGENTS:\s*(\d+)", joined, re.IGNORECASE)
    return int(match.group(1)) if match else 0


def _is_totals_row(cells: List[str]) -> bool:
    return bool(cells) and "AGENTS:" in cells[0].upper()


def _totals_cell(cells: List[str], col_index: int) -> str:
    """TOTALS rows omit the first 3 label columns; values shift left by 3."""
    if col_index < 0:
        return ""
    idx = col_index - 3 if _is_totals_row(cells) else col_index
    if 0 <= idx < len(cells):
        return cells[idx]
    return ""


def parse_campaign_totals(html: str) -> CampaignTotals:
    """Extract TOTALS row from CALL STATS and PAUSE CODE sections."""
    parts = re.split(
        r"CALL STATS BREAKDOWN:|PAUSE CODE BREAKDOWN:",
        html,
        flags=re.IGNORECASE,
    )
    totals = CampaignTotals()

    if len(parts) >= 2:
        headers, rows = _parse_pipe_table(parts[1])
        totals_row = next((r for r in rows if _agents_from_totals_row(r)), None)
        if headers and totals_row:
            col = _index_map(headers)
            totals.headcount = _agents_from_totals_row(totals_row)
            if "CALLS" in col:
                totals.calls = _parse_int(_totals_cell(totals_row, col["CALLS"]))
            if "SALE" in col:
                totals.sale = _parse_int(_totals_cell(totals_row, col["SALE"]))
            for key in ("BSALE", "B-SALE", "BUSINESS SALES"):
                if key in col:
                    totals.bsale = _parse_int(_totals_cell(totals_row, col[key]))
                    break

    if len(parts) >= 3:
        headers, rows = _parse_pipe_table(parts[2])
        totals_row = next((r for r in rows if _agents_from_totals_row(r)), None)
        if headers and totals_row:
            col = _index_map(headers)
            if "NONPAUSE" in col:
                totals.hrs = parse_duration_to_hours(
                    _totals_cell(totals_row, col["NONPAUSE"])
                )
            if not totals.headcount:
                totals.headcount = _agents_from_totals_row(totals_row)

    return totals


def parse_agents(html: str, lunch_deduction_hrs: float = 0.0) -> List[AgentStats]:
    parts = re.split(
        r"CALL STATS BREAKDOWN:|PAUSE CODE BREAKDOWN:",
        html,
        flags=re.IGNORECASE,
    )
    agents: Dict[str, AgentStats] = {}

    if len(parts) >= 2:
        headers, rows = _parse_pipe_table(parts[1])
        if headers:
            col = _index_map(headers)
            name_i = col.get("USER NAME", 0)
            id_i = col.get("ID", 1)
            team_i = col.get("CURRENT USER GROUP", 2)
            calls_i = col.get("CALLS", -1)
            sale_i = col.get("SALE", -1)
            bsale_i = col.get("BSALE", col.get("B-SALE", -1))

            for row in rows:
                if _agents_from_totals_row(row):
                    continue
                if len(row) <= max(name_i, id_i, team_i):
                    continue
                uid = _extract_user_id(row[id_i] if id_i < len(row) else "")
                if not uid:
                    continue
                agents[uid] = AgentStats(
                    name=row[name_i],
                    user_id=uid,
                    team=row[team_i] if team_i < len(row) else "",
                    calls=_parse_int(row[calls_i]) if calls_i >= 0 else 0,
                    sale=_parse_int(row[sale_i]) if sale_i >= 0 else 0,
                    bsale=_parse_int(row[bsale_i]) if bsale_i >= 0 else 0,
                )

    if len(parts) >= 3:
        headers, rows = _parse_pipe_table(parts[2])
        if headers:
            col = _index_map(headers)
            id_i = col.get("ID", 1)
            np_i = col.get("NONPAUSE", 5)
            for row in rows:
                if _agents_from_totals_row(row):
                    continue
                uid = _strip_html(row[id_i] if id_i < len(row) else "")
                if uid in agents:
                    np_val = row[np_i] if np_i < len(row) else "0:00:00"
                    raw = parse_duration_to_hours(np_val)
                    agents[uid].hrs = max(0.0, raw - lunch_deduction_hrs)

    return list(agents.values())


def parse_campaign_summary(html: str) -> Dict[str, CampaignWait]:
    results: Dict[str, CampaignWait] = {}
    campaign_blocks = re.split(
        r'<BR><b><a href="\./realtime_report\.php\?group=([^"&]+)',
        html,
        flags=re.IGNORECASE,
    )

    for i in range(1, len(campaign_blocks), 2):
        campaign_id = campaign_blocks[i]
        block = campaign_blocks[i + 1] if i + 1 < len(campaign_blocks) else ""
        wait_match = re.search(
            r"AGENT AVG WAIT:</B></TD><TD[^>]*><font[^>]*>\s*&nbsp;\s*(\d+)\s*&nbsp;",
            block,
            re.IGNORECASE,
        )
        agents_match = re.search(
            r"AVG AGENTS:</B></TD><TD[^>]*><font[^>]*>\s*&nbsp;\s*([\d.]+)\s*&nbsp;",
            block,
            re.IGNORECASE,
        )
        if wait_match:
            results[campaign_id] = CampaignWait(
                campaign_id=campaign_id,
                agent_avg_wait_sec=int(wait_match.group(1)),
                avg_agents=float(agents_match.group(1)) if agents_match else 0.0,
            )
    return results
