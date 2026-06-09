from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


@dataclass
class CampaignConfig:
    id: str
    name: str
    main_code: str
    target: float = 0.0


@dataclass
class TeamConfig:
    name: str
    vicidial_group: str
    target: float = 0.0


def load_campaigns(path: Path | None = None) -> list[CampaignConfig]:
    path = path or ROOT / "config" / "campaigns.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return [CampaignConfig(**item) for item in data]


def load_teams(path: Path | None = None) -> list[TeamConfig]:
    path = path or ROOT / "config" / "teams.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return [TeamConfig(**item) for item in data]
