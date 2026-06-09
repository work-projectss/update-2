from __future__ import annotations

import re


_CAMPAIGN_BLOCK = re.compile(
    r'<b><a href="./realtime_report\.php\?group=([^"&]+)',
    re.I,
)
_AGENT_AVG_WAIT = re.compile(
    r"AGENT AVG WAIT:</B></TD><TD[^>]*><font[^>]*>\s*&nbsp;\s*([\d.]+)",
    re.I,
)


def parse_campaign_wait_times(html: str) -> dict[str, int]:
    """AGENT AVG WAIT (seconds) per campaign from AST_timeonVDADallSUMMARY."""
    waits: dict[str, int] = {}
    blocks = list(_CAMPAIGN_BLOCK.finditer(html))
    for index, match in enumerate(blocks):
        campaign_id = match.group(1).strip()
        start = match.start()
        end = blocks[index + 1].start() if index + 1 < len(blocks) else len(html)
        chunk = html[start:end]
        wait_match = _AGENT_AVG_WAIT.search(chunk)
        if wait_match:
            waits[campaign_id] = int(round(float(wait_match.group(1))))
        else:
            waits[campaign_id] = 0
    return waits
