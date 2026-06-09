from __future__ import annotations

import os
from datetime import date
from urllib.parse import urljoin

import requests
import urllib3
from requests.auth import HTTPBasicAuth

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class VicidialFetcher:
    """Fetches VICIdial reports using the same parameters as the web UI link."""

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        verify_ssl: bool = False,
        query_time: str = "00:00:00",
        end_time: str = "23:59:59",
        shift: str = "--",
        show_percentages: bool = True,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.auth = HTTPBasicAuth(username, password)
        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.verify = verify_ssl
        self.query_time = query_time
        self.end_time = end_time
        self.shift = shift
        self.show_percentages = show_percentages

    def fetch_agent_performance(
        self,
        report_date: date,
        campaign_id: str = "--ALL--",
    ) -> str:
        url = urljoin(self.base_url + "/", "AST_agent_performance_detail.php")
        params = [
            ("DB", "0"),
            ("query_date", report_date.isoformat()),
            ("end_date", report_date.isoformat()),
            ("query_time", self.query_time),
            ("end_time", self.end_time),
            ("group[]", campaign_id),
            ("user_group[]", "--ALL--"),
            ("users[]", "--ALL--"),
            ("shift", self.shift),
            ("report_display_type", "TEXT"),
            ("SUBMIT", "SUBMIT"),
        ]
        if self.show_percentages:
            params.append(("show_percentages", "checked"))

        response = self.session.get(url, params=params, timeout=180)
        response.raise_for_status()
        return response.text

    def fetch_campaign_summary(self) -> str:
        url = urljoin(self.base_url + "/", "AST_timeonVDADallSUMMARY.php")
        params = {
            "group": "",
            "RR": "4",
            "DB": "0",
            "types": "SHOW ALL CAMPAIGNS",
        }
        response = self.session.get(url, params=params, timeout=60)
        response.raise_for_status()
        return response.text

    @classmethod
    def from_env(cls) -> "VicidialFetcher":
        base = os.getenv("VICIDIAL_BASE_URL", "https://alpha2.onvoip.co.za/vicidial")
        user = os.getenv("VICIDIAL_USER", "")
        password = os.getenv("VICIDIAL_PASSWORD", "")
        if not user or not password:
            raise ValueError("VICIDIAL_USER and VICIDIAL_PASSWORD must be set in .env")
        verify = os.getenv("VICIDIAL_VERIFY_SSL", "false").lower() in ("1", "true", "yes")
        show_pct = os.getenv("SHOW_PERCENTAGES", "true").lower() in ("1", "true", "yes")
        return cls(
            base,
            user,
            password,
            verify_ssl=verify,
            query_time=os.getenv("REPORT_START_TIME", "00:00:00"),
            end_time=os.getenv("REPORT_END_TIME", "23:59:59"),
            shift=os.getenv("REPORT_SHIFT", "--"),
            show_percentages=show_pct,
        )
