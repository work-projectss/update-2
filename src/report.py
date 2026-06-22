from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime

from src.config_loader import AppConfig
from src.parser import sum_statuses
from src.vicidial_client import VicidialClient

log = logging.getLogger("alpha1-update")


@dataclass
class RowMetrics:
    label: str
    sub_label: str
    main_code: str
    target: int
    sales: int
    b_sales: int
    hrs: int
    headcount: int
    avg_per_hour: float | None
    ave_per_agent: float | None
    pct_to_target: int | None
    wait_time: int | None = None


@dataclass
class GrandTotals:
    sales: int
    b_sales: int
    hrs: int
    headcount: int
    avg_per_hour: float | None
    ave_per_agent: float | None
    pct_to_target: int | None
    wait_time: int | None = None


@dataclass
class PerformanceReport:
    report_date: date
    campaign_rows: list[RowMetrics]
    team_rows: list[RowMetrics]
    campaign_grand: GrandTotals
    team_grand: GrandTotals
    campaign_target_total: int
    team_target_total: int


def _decimal_ratio(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 1)


def _pct_whole(total_sales: int, target: int) -> int | None:
    if target <= 0:
        return None
    return round(100 * total_sales / target)


def _combined_sales(sales: int, b_sales: int) -> int:
    """Sales + business sales for rate and % to target calculations."""
    return sales + b_sales


def _build_row(
    *,
    label: str,
    sub_label: str,
    main_code: str = "",
    target: int,
    sales: int,
    b_sales: int,
    hrs: int,
    headcount: int,
    wait_time: int | None = None,
) -> RowMetrics:
    combined = _combined_sales(sales, b_sales)
    return RowMetrics(
        label=label,
        sub_label=sub_label,
        main_code=main_code or label,
        target=target,
        sales=sales,
        b_sales=b_sales,
        hrs=hrs,
        headcount=headcount,
        avg_per_hour=_decimal_ratio(combined, hrs),
        ave_per_agent=_decimal_ratio(combined, headcount),
        pct_to_target=_pct_whole(combined, target),
        wait_time=wait_time,
    )


def _build_grand(
    *,
    sales: int,
    b_sales: int,
    hrs: int,
    headcount: int,
    target_total: int,
    wait_time: int | None = None,
) -> GrandTotals:
    combined = _combined_sales(sales, b_sales)
    return GrandTotals(
        sales=sales,
        b_sales=b_sales,
        hrs=hrs,
        headcount=headcount,
        avg_per_hour=_decimal_ratio(combined, hrs),
        ave_per_agent=_decimal_ratio(combined, headcount),
        pct_to_target=_pct_whole(combined, target_total),
        wait_time=wait_time,
    )


class PerformanceReportBuilder:
    def __init__(self, config: AppConfig, client: VicidialClient) -> None:
        self._config = config
        self._client = client

    def _sales_metrics(self, summary) -> tuple[int, int, int]:
        sales = sum_statuses(summary.status_counts, self._config.sales_statuses)
        b_sales = sum_statuses(summary.status_counts, self._config.b_sales_statuses)
        hrs = summary.hours
        return sales, b_sales, hrs

    def build(self, report_date: date | None = None) -> PerformanceReport:
        report_day = report_date or date.today()
        teams = self._client.resolve_teams(report_date=report_day)
        try:
            wait_times = self._client.fetch_campaign_wait_times()
        except Exception as exc:
            log.warning(
                "Could not fetch campaign wait times; continuing without wait data: %s",
                exc,
            )
            wait_times = {}

        team_rows: list[RowMetrics] = []
        total_headcount = 0

        for team in teams:
            summary = self._client.fetch_summary(
                report_date=report_day, user_group=team.user_group
            )
            sales, b_sales, hrs = self._sales_metrics(summary)
            hc = summary.headcount
            total_headcount += hc
            team_rows.append(
                _build_row(
                    label=team.display_name,
                    sub_label="",
                    main_code="",
                    target=team.target,
                    sales=sales,
                    b_sales=b_sales,
                    hrs=hrs,
                    headcount=hc,
                )
            )

        campaign_rows: list[RowMetrics] = []
        wait_values: list[int] = []
        for campaign in self._config.campaigns:
            summary = self._client.fetch_summary(
                report_date=report_day, campaign_id=campaign.campaign_id
            )
            sales, b_sales, hrs = self._sales_metrics(summary)
            wait = wait_times.get(campaign.campaign_id, 0)
            wait_values.append(wait)
            campaign_rows.append(
                _build_row(
                    label=campaign.main_code,
                    sub_label=campaign.campaign_id,
                    main_code=campaign.main_code,
                    target=campaign.lead_volume,
                    sales=sales,
                    b_sales=b_sales,
                    hrs=hrs,
                    headcount=total_headcount,
                    wait_time=wait,
                )
            )

        campaign_target_total = sum(r.target for r in campaign_rows)
        team_target_total = sum(r.target for r in team_rows)

        campaign_sales = sum(r.sales for r in campaign_rows)
        campaign_b_sales = sum(r.b_sales for r in campaign_rows)
        campaign_hrs = sum(r.hrs for r in campaign_rows)
        avg_wait = (
            round(sum(wait_values) / len(wait_values)) if wait_values else None
        )

        campaign_grand = _build_grand(
            sales=campaign_sales,
            b_sales=campaign_b_sales,
            hrs=campaign_hrs,
            headcount=total_headcount,
            target_total=campaign_target_total,
            wait_time=avg_wait,
        )
        team_grand = _build_grand(
            sales=campaign_sales,
            b_sales=campaign_b_sales,
            hrs=campaign_hrs,
            headcount=total_headcount,
            target_total=team_target_total,
        )

        return PerformanceReport(
            report_date=report_day,
            campaign_rows=campaign_rows,
            team_rows=team_rows,
            campaign_grand=campaign_grand,
            team_grand=team_grand,
            campaign_target_total=campaign_target_total,
            team_target_total=team_target_total,
        )


def _fmt_decimal(value: float | None) -> str:
    if value is None:
        return "#DIV/0!"
    return f"{value:.1f}".replace(".", ",")


def _fmt_int(value: int | None) -> str:
    return "-" if value is None else str(value)


def _format_table(
    title: str,
    rows: list[RowMetrics],
    grand: GrandTotals,
    target_total: int,
    *,
    show_sub: bool,
    target_header: str,
    include_total: bool = True,
) -> str:
    lines = [title, ""]
    if show_sub:
        lines.append(
            f"{'Campaign':<22} {'Vicidial ID':<10} {'Main Code':<18} "
            f"{target_header:>6} {'Sales':>6} {'B Sal':>6} {'Hrs':>6} {'HC':>4} "
            f"{'Avg/h':>6} {'/Ag':>5} {'%Tgt':>6} {'Wait':>5}"
        )
    else:
        lines.append(
            f"{'Team':<16} {target_header:>6} {'Sales':>6} {'B Sal':>6} "
            f"{'Hrs':>6} {'HC':>4} {'Avg/h':>6} {'/Ag':>5} {'%Tgt':>6}"
        )
    width = 78 if show_sub else 60
    lines.append("-" * width)

    for row in rows:
        pct = f"{row.pct_to_target}%" if row.pct_to_target is not None else "-"
        if show_sub:
            lines.append(
                f"{row.label:<22} {row.sub_label:<10} {row.main_code:<18} "
                f"{row.target:>6} {row.sales:>6} {row.b_sales:>6} {row.hrs:>6} "
                f"{row.headcount:>4} {_fmt_decimal(row.avg_per_hour):>6} "
                f"{_fmt_decimal(row.ave_per_agent):>5} {pct:>6} "
                f"{_fmt_int(row.wait_time):>5}"
            )
        else:
            lines.append(
                f"{row.label:<16} {row.target:>6} {row.sales:>6} "
                f"{row.b_sales:>6} {row.hrs:>6} {row.headcount:>4} "
                f"{_fmt_decimal(row.avg_per_hour):>6} "
                f"{_fmt_decimal(row.ave_per_agent):>5} {pct:>6}"
            )

    if include_total:
        pct_str = (
            f"{grand.pct_to_target}%"
            if grand.pct_to_target is not None
            else "-"
        )
        lines.append("-" * width)
        if show_sub:
            lines.append(
                f"{'TOTAL':<22} {'':<10} {'':<18} {target_total:>6} "
                f"{grand.sales:>6} {grand.b_sales:>6} {grand.hrs:>6} "
                f"{grand.headcount:>4} {_fmt_decimal(grand.avg_per_hour):>6} "
                f"{_fmt_decimal(grand.ave_per_agent):>5} {pct_str:>6} "
                f"{_fmt_int(grand.wait_time):>5}"
            )
        else:
            lines.append(
                f"{'TOTAL':<16} {target_total:>6} {grand.sales:>6} "
                f"{grand.b_sales:>6} {grand.hrs:>6} {grand.headcount:>4} "
                f"{_fmt_decimal(grand.avg_per_hour):>6} "
                f"{_fmt_decimal(grand.ave_per_agent):>5} {pct_str:>6}"
            )
    return "\n".join(lines)


def format_whatsapp_message(
    report: PerformanceReport,
    *,
    generated_at: datetime | None = None,
) -> str:
    ts = (generated_at or datetime.now()).strftime("%Y-%m-%d %H:%M")
    day = report.report_date.isoformat()
    return "\n".join(
        [
            "*Performance Update*",
            f"_{ts}_",
            f"Report date: *{day}*",
            "",
            _format_table(
                "*By campaign*",
                report.campaign_rows,
                report.campaign_grand,
                report.campaign_target_total,
                show_sub=True,
                target_header="Leads",
                include_total=True,
            ),
            "",
            _format_table(
                "*By team*",
                report.team_rows,
                report.team_grand,
                report.team_target_total,
                show_sub=False,
                target_header="Target",
            ),
        ]
    )
