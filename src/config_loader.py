from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import time as dtime
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


@dataclass(frozen=True)
class CampaignConfig:
    campaign_id: str
    main_code: str
    lead_volume: int


@dataclass(frozen=True)
class TeamConfig:
    user_group: str
    display_name: str
    target: int


@dataclass(frozen=True)
class AppConfig:
    vicidial_base_url: str
    vicidial_summary_url: str
    vicidial_summary_params: dict[str, str]
    vicidial_shift: str
    vicidial_report_params: dict[str, str]
    vicidial_verify_ssl: bool
    campaigns: list[CampaignConfig]
    teams: list[TeamConfig]
    teams_auto_discover: bool
    sales_statuses: list[str]
    b_sales_statuses: list[str]
    hours_source: str
    interval_seconds: int
    start_time: dtime
    stop_time: dtime
    whatsapp_provider: str
    whatsapp_send_as_image: bool
    whatsapp_default_chat: str
    whatsapp_lunch_eod_chats: list[str]
    vicidial_user: str
    vicidial_password: str


def _normalize_chat_id(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    if "@" in value:
        return value
    return f"{value}@c.us"


def _parse_chat_list(value: str) -> list[str]:
    ids: list[str] = []
    for part in value.replace(";", ",").split(","):
        chat = _normalize_chat_id(part)
        if chat and chat not in ids:
            ids.append(chat)
    return ids


def _parse_time(s: str) -> dtime:
    h, m = s.strip().split(":")
    return dtime(int(h), int(m))


def _read_interval(schedule: dict) -> int:
    if "interval_seconds" in schedule:
        return max(1, int(schedule["interval_seconds"]))
    return max(1, int(schedule.get("interval_minutes", 30))) * 60


def load_config(config_path: Path | None = None) -> AppConfig:
    load_dotenv()
    root = Path(__file__).resolve().parent.parent
    path = config_path or (root / "config.yaml")
    with path.open(encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f)

    vicidial = raw["vicidial"]
    campaigns = [
        CampaignConfig(
            campaign_id=c["campaign_id"],
            main_code=c["main_code"],
            lead_volume=int(c["lead_volume"]),
        )
        for c in raw["campaigns"]
    ]
    teams = [
        TeamConfig(
            user_group=t["user_group"],
            display_name=t.get("display_name", t["user_group"]),
            target=int(t["target"]),
        )
        for t in raw.get("teams", [])
        if isinstance(t, dict) and "user_group" in t
    ]

    user = os.getenv("VICIDIAL_USER", "").strip()
    password = os.getenv("VICIDIAL_PASSWORD", "").strip()
    if not user or not password:
        raise ValueError(
            "Set VICIDIAL_USER and VICIDIAL_PASSWORD in .env"
        )

    auto_discover = bool(raw.get("teams_auto_discover", True))

    summary_params = vicidial.get("summary_params") or {
        "RR": "4",
        "DB": "0",
        "adastats": "",
        "types": "SHOW ALL CAMPAIGNS",
    }
    summary_params = {str(k): str(v) for k, v in summary_params.items()}

    report_params = vicidial.get("report_params") or {}
    report_params = {str(k): str(v) for k, v in report_params.items()}

    whatsapp_cfg = raw.get("whatsapp", {})
    provider = whatsapp_cfg.get("provider", "console")
    env_provider = os.getenv("WHATSAPP_PROVIDER", "").strip().lower()
    if env_provider:
        alias = {
            "greenapi": "green_api",
            "green_api": "green_api",
            "evolution": "evolution",
            "evolution_api": "evolution",
            "twilio": "twilio",
            "webhook": "webhook",
            "console": "console",
        }
        provider = alias.get(env_provider, env_provider)

    default_from_env = _parse_chat_list(
        os.getenv("WHATSAPP_TO", "") or os.getenv("GREENAPI_CHAT_ID", "")
    )
    lunch_eod_from_env = _parse_chat_list(os.getenv("WHATSAPP_TO_LUNCH_EOD", ""))
    default_from_yaml = _normalize_chat_id(str(whatsapp_cfg.get("default_group", "")))
    lunch_eod_from_yaml = [
        _normalize_chat_id(str(x))
        for x in whatsapp_cfg.get(
            "dual_groups", whatsapp_cfg.get("lunch_eod_groups", [])
        )
        if str(x).strip()
    ]
    whatsapp_default_chat = (
        default_from_env[0] if default_from_env else default_from_yaml
    )
    whatsapp_lunch_eod_chats = lunch_eod_from_env or lunch_eod_from_yaml

    return AppConfig(
        vicidial_base_url=vicidial["base_url"],
        vicidial_summary_url=vicidial.get(
            "summary_url",
            "http://alpha1.onvoip.co.za/vicidial/AST_timeonVDADallSUMMARY.php",
        ),
        vicidial_summary_params=summary_params,
        vicidial_shift=vicidial.get("shift", "--"),
        vicidial_report_params=report_params,
        vicidial_verify_ssl=bool(vicidial.get("verify_ssl", True)),
        campaigns=campaigns,
        teams=teams,
        teams_auto_discover=auto_discover,
        sales_statuses=[s.upper() for s in raw.get("sales_statuses", [])],
        b_sales_statuses=[s.upper() for s in raw.get("b_sales_statuses", [])],
        hours_source=raw.get("hours_source", "nonpause"),
        interval_seconds=_read_interval(raw.get("schedule", {})),
        start_time=_parse_time(
            raw.get("schedule", {}).get("weekdays", {}).get("start_time", "08:30")
        ),
        stop_time=_parse_time(
            raw.get("schedule", {}).get("weekdays", {}).get("stop_time", "19:10")
        ),
        whatsapp_provider=provider,
        whatsapp_send_as_image=bool(whatsapp_cfg.get("send_as_image", True)),
        whatsapp_default_chat=whatsapp_default_chat,
        whatsapp_lunch_eod_chats=whatsapp_lunch_eod_chats,
        vicidial_user=user,
        vicidial_password=password,
    )
