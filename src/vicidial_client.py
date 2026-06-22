from __future__ import annotations

import re
import logging
import time
from datetime import date

import requests
import urllib3

from src.config_loader import AppConfig, TeamConfig
from src.parser import (
    AgentPerformanceSummary,
    discover_user_groups,
    parse_agent_performance_report,
)
from src.summary_wait import parse_campaign_wait_times

log = logging.getLogger("alpha1-update")
_TEAM_PREFIX = re.compile(r"^Team", re.I)


class VicidialClient:
    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._session = requests.Session()
        self._session.auth = (config.vicidial_user, config.vicidial_password)
        self._session.headers.update(
            {"User-Agent": "Alpha1-WhatsApp-Update/1.0"}
        )
        self._session.verify = config.vicidial_verify_ssl
        if not config.vicidial_verify_ssl:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def _get(self, url: str, *, params: list[tuple[str, str]] | dict[str, str]) -> requests.Response:
        last_error: Exception | None = None
        for attempt in range(1, 5):
            try:
                response = self._session.get(url, params=params, timeout=120)
                response.raise_for_status()
                return response
            except requests.RequestException as exc:
                last_error = exc
                if attempt == 4:
                    break
                delay = attempt * 2
                log.warning(
                    "Vicidial request failed (attempt %d/4); retrying in %ss: %s",
                    attempt,
                    delay,
                    exc,
                )
                time.sleep(delay)
        assert last_error is not None
        raise last_error

    def _report_date_str(self, report_date: date | None) -> str:
        return (report_date or date.today()).isoformat()

    def _report_params(
        self,
        *,
        query_date: str,
        campaigns: list[str] | None,
        user_groups: list[str] | None,
    ) -> list[tuple[str, str]]:
        extra = self._config.vicidial_report_params
        params: list[tuple[str, str]] = [
            ("query_date", query_date),
            ("end_date", query_date),
            ("shift", self._config.vicidial_shift),
            ("SUBMIT", "SUBMIT"),
        ]
        for key, value in extra.items():
            if key in ("users",):
                params.append(("users[]", value))
            else:
                params.append((key, value))

        if campaigns:
            for c in campaigns:
                params.append(("group[]", c))
        else:
            params.append(("group[]", "--ALL--"))

        if user_groups:
            for g in user_groups:
                params.append(("user_group[]", g))
        else:
            params.append(("user_group[]", "--ALL--"))

        return params

    def fetch_report(
        self,
        *,
        report_date: date | None = None,
        campaigns: list[str] | None = None,
        user_groups: list[str] | None = None,
    ) -> str:
        d = self._report_date_str(report_date)
        params = self._report_params(
            query_date=d, campaigns=campaigns, user_groups=user_groups
        )
        response = self._get(self._config.vicidial_base_url, params=params)
        if "Invalid Username/Password" in response.text:
            raise PermissionError("Vicidial rejected credentials")
        if "not allowed to view this report" in response.text:
            raise PermissionError("User cannot view Agent Performance Detail")
        return response.text

    def fetch_summary(
        self,
        *,
        report_date: date | None = None,
        campaign_id: str | None = None,
        user_group: str | None = None,
    ) -> AgentPerformanceSummary:
        campaigns = [campaign_id] if campaign_id else None
        user_groups = [user_group] if user_group else None
        html = self.fetch_report(
            report_date=report_date,
            campaigns=campaigns,
            user_groups=user_groups,
        )
        return parse_agent_performance_report(html)

    def _filter_discovered_groups(self, groups: list[str]) -> list[str]:
        """Keep call-center teams only (Team* / Trainees*), not ADMIN or agent logins."""
        filtered: list[str] = []
        for name in groups:
            if name in ("ADMIN", "AGENTS", "INVNT", "--ALL--"):
                continue
            if _TEAM_PREFIX.match(name) or name.startswith("Trainees"):
                filtered.append(name)
        return filtered

    def resolve_teams(
        self, report_date: date | None = None
    ) -> list[TeamConfig]:
        configured = {t.user_group: t for t in self._config.teams}
        if not self._config.teams_auto_discover:
            return list(self._config.teams)

        html = self.fetch_report(report_date=report_date)
        discovered = self._filter_discovered_groups(discover_user_groups(html))
        merged: list[TeamConfig] = []
        seen: set[str] = set()

        for user_group in discovered:
            seen.add(user_group)
            if user_group in configured:
                merged.append(configured[user_group])
            else:
                merged.append(
                    TeamConfig(
                        user_group=user_group,
                        display_name=user_group,
                        target=0,
                    )
                )

        for team in self._config.teams:
            if team.user_group not in seen:
                merged.append(team)

        return sorted(merged, key=lambda t: t.display_name.lower())

    def fetch_campaign_wait_times(self) -> dict[str, int]:
        response = self._get(
            self._config.vicidial_summary_url,
            params=self._config.vicidial_summary_params,
        )
        return parse_campaign_wait_times(response.text)
