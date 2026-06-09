from __future__ import annotations

import os
from datetime import date, datetime

from .aggregator import FullReport, build_campaign_rows, build_team_rows
from .config_loader import load_campaigns, load_teams
from .fetcher import VicidialFetcher
from .parser import parse_agents, parse_campaign_summary, parse_campaign_totals


def build_live_report(report_date: date | None = None) -> FullReport:
    """Pull today's VICIdial data and build campaign + team tables."""
    report_date = report_date or date.today()
    fetcher = VicidialFetcher.from_env()
    campaigns_cfg = load_campaigns()
    teams_cfg = load_teams()

    wait_data = parse_campaign_summary(fetcher.fetch_campaign_summary())

    campaign_data = {}
    for cfg in campaigns_cfg:
        html = fetcher.fetch_agent_performance(report_date, cfg.id)
        campaign_data[cfg.id] = parse_campaign_totals(html)

    all_html = fetcher.fetch_agent_performance(report_date, "--ALL--")
    agents = parse_agents(all_html, lunch_deduction_hrs=0.0)
    auto_target = float(os.getenv("AUTO_SALES_PER_AGENT_TARGET", "3"))

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    period_label = f"{report_date.isoformat()} (updated {now})"

    return FullReport(
        period_label=period_label,
        campaigns=build_campaign_rows(
            campaigns_cfg,
            campaign_data,
            wait_data,
            auto_target_per_agent=auto_target,
        ),
        teams=build_team_rows(teams_cfg, agents, 0.0),
    )
