from __future__ import annotations

from datetime import datetime

from .aggregator import CampaignRow, FullReport, TeamRow


def _fmt_num(value: float, decimals: int = 1) -> str:
    if value == 0:
        return "0"
    if decimals == 0:
        return str(int(round(value)))
    return f"{value:.{decimals}f}"


def _fmt_pct(value: float) -> str:
    if value <= 0:
        return "0%"
    return f"{value:.0f}%"


def _campaign_table(campaigns: list[CampaignRow]) -> list[str]:
    lines = [
        "*CAMPAIGN PERFORMANCE*",
        "```",
        f"{'Campaign':<22} {'ID':<8} {'Leads':>5} {'Sale':>4} {'B-Sl':>4} "
        f"{'Hrs':>4} {'HC':>3} {'Avg/h':>5} {'Agnt':>4} {'%Tgt':>5} {'Wait':>4}",
        "-" * 78,
    ]
    for c in campaigns:
        avg_h = _fmt_num(c.avg_per_hour, 2) if c.hrs > 0 else "0"
        lines.append(
            f"{c.name[:22]:<22} {c.campaign_id:<8} {c.lead_volume:>5} {c.sales:>4} "
            f"{c.b_sales:>4} {_fmt_num(c.hrs, 0):>4} {c.headcount:>3} "
            f"{avg_h:>5} {_fmt_num(c.ave_per_agent, 1):>4} "
            f"{_fmt_pct(c.pct_to_target):>5} {c.wait_sec:>4}"
        )

    t_leads = sum(c.lead_volume for c in campaigns)
    t_sales = sum(c.sales for c in campaigns)
    t_b = sum(c.b_sales for c in campaigns)
    t_hrs = sum(c.hrs for c in campaigns)
    t_hc = sum(c.headcount for c in campaigns)
    t_all = t_sales + t_b
    t_avg_h = t_all / t_hrs if t_hrs > 0 else 0.0
    t_target = sum(c.target for c in campaigns)
    t_pct = (t_all / t_target * 100) if t_target > 0 else 0.0
    waits = [c.wait_sec for c in campaigns if c.wait_sec > 0]
    t_wait = int(round(sum(waits) / len(waits))) if waits else 0

    lines.append("-" * 78)
    lines.append(
        f"{'TOTAL':<22} {'':<8} {t_leads:>5} {t_sales:>4} {t_b:>4} "
        f"{_fmt_num(t_hrs, 0):>4} {t_hc:>3} {_fmt_num(t_avg_h, 2):>5} "
        f"{'':>4} {_fmt_pct(t_pct):>5} {t_wait:>4}"
    )
    lines.append("```")
    return lines


def _team_table(teams: list[TeamRow]) -> list[str]:
    lines = [
        "",
        "*TEAM PERFORMANCE*",
        "```",
        f"{'Team':<18} {'Tgt':>4} {'Sale':>4} {'B-Sl':>4} {'Hrs':>4} "
        f"{'HC':>3} {'Avg/h':>5} {'Agnt':>4} {'%Tgt':>5}",
        "-" * 58,
    ]
    for t in teams:
        avg_h = _fmt_num(t.avg_per_hour, 2) if t.hrs > 0 else "0"
        lines.append(
            f"{t.name[:18]:<18} {int(t.target):>4} {t.sales:>4} {t.b_sales:>4} "
            f"{_fmt_num(t.hrs, 0):>4} {t.headcount:>3} "
            f"{avg_h:>5} {_fmt_num(t.ave_per_agent, 1):>4} "
            f"{_fmt_pct(t.pct_to_target):>5}"
        )

    t_target = sum(t.target for t in teams)
    t_sales = sum(t.sales for t in teams)
    t_b = sum(t.b_sales for t in teams)
    t_hrs = sum(t.hrs for t in teams)
    t_hc = sum(t.headcount for t in teams)
    t_all = t_sales + t_b
    t_avg_h = t_all / t_hrs if t_hrs > 0 else 0.0
    t_pct = (t_all / t_target * 100) if t_target > 0 else 0.0

    lines.append("-" * 58)
    lines.append(
        f"{'Total':<18} {int(t_target):>4} {t_sales:>4} {t_b:>4} "
        f"{_fmt_num(t_hrs, 0):>4} {t_hc:>3} {_fmt_num(t_avg_h, 2):>5} "
        f"{'':>4} {_fmt_pct(t_pct):>5}"
    )
    lines.append("```")
    return lines


def format_whatsapp_message(report: FullReport) -> str:
    stamp = datetime.now().strftime("%H:%M")
    lines = [
        "*Live Performance Update*",
        f"_{report.period_label}_",
        f"_Today 00:00-23:59 | Sent {stamp}_",
        "_Sales = SALE + B-Sales | Hrs = NONPAUSE | Wait = AGENT AVG WAIT_",
    ]
    lines.extend(_campaign_table(report.campaigns))
    lines.extend(_team_table(report.teams))
    return "\n".join(lines)
