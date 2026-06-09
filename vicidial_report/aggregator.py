from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from .config_loader import CampaignConfig, TeamConfig
from .parser import AgentStats, CampaignTotals, CampaignWait


@dataclass
class CampaignRow:
    name: str
    campaign_id: str
    main_code: str
    lead_volume: int = 0
    sales: int = 0
    b_sales: int = 0
    hrs: float = 0.0
    headcount: int = 0
    target: float = 0.0
    wait_sec: int = 0

    @property
    def total_sales(self) -> int:
        return self.sales + self.b_sales

    @property
    def avg_per_hour(self) -> float:
        return self.total_sales / self.hrs if self.hrs > 0 else 0.0

    @property
    def ave_per_agent(self) -> float:
        return self.total_sales / self.headcount if self.headcount > 0 else 0.0

    @property
    def pct_to_target(self) -> float:
        if self.target > 0:
            return (self.total_sales / self.target) * 100
        return 0.0


@dataclass
class TeamRow:
    name: str
    target: float = 0.0
    sales: int = 0
    b_sales: int = 0
    hrs: float = 0.0
    headcount: int = 0

    @property
    def total_sales(self) -> int:
        return self.sales + self.b_sales

    @property
    def avg_per_hour(self) -> float:
        return self.total_sales / self.hrs if self.hrs > 0 else 0.0

    @property
    def ave_per_agent(self) -> float:
        return self.total_sales / self.headcount if self.headcount > 0 else 0.0

    @property
    def pct_to_target(self) -> float:
        if self.target > 0:
            return (self.total_sales / self.target) * 100
        return 0.0


@dataclass
class FullReport:
    campaigns: List[CampaignRow] = field(default_factory=list)
    teams: List[TeamRow] = field(default_factory=list)
    period_label: str = ""


def apply_lunch_deduction(hrs: float, weekdays: int, lunch_minutes: int) -> float:
    """Deduct one lunch break per weekday from total NONPAUSE hours."""
    deduction = (lunch_minutes / 60.0) * weekdays
    return max(0.0, hrs - deduction)


def build_campaign_rows(
    campaign_configs: List[CampaignConfig],
    campaign_data: Dict[str, CampaignTotals],
    wait_data: Dict[str, CampaignWait],
    weekdays: int = 0,
    lunch_minutes: int = 0,
    auto_target_per_agent: float = 0.0,
) -> List[CampaignRow]:
    rows: List[CampaignRow] = []
    for cfg in campaign_configs:
        data = campaign_data.get(cfg.id, CampaignTotals())
        wait = wait_data.get(cfg.id)
        hrs = apply_lunch_deduction(data.hrs, weekdays, lunch_minutes)
        target = cfg.target
        if target <= 0 and auto_target_per_agent > 0 and data.headcount > 0:
            target = data.headcount * auto_target_per_agent
        rows.append(
            CampaignRow(
                name=cfg.name,
                campaign_id=cfg.id,
                main_code=cfg.main_code,
                lead_volume=data.calls,
                sales=data.sale,
                b_sales=data.bsale,
                hrs=hrs,
                headcount=data.headcount,
                target=target,
                wait_sec=wait.agent_avg_wait_sec if wait else 0,
            )
        )
    return rows


def build_team_rows(
    team_configs: List[TeamConfig],
    agents: List[AgentStats],
    lunch_deduction_per_agent: float,
) -> List[TeamRow]:
    rows: List[TeamRow] = []
    for cfg in team_configs:
        team_agents = [a for a in agents if a.team == cfg.vicidial_group]
        sales = sum(a.sale for a in team_agents)
        b_sales = sum(a.bsale for a in team_agents)
        hrs = sum(max(0.0, a.hrs) for a in team_agents)
        if not team_agents and lunch_deduction_per_agent:
            hrs = 0.0
        rows.append(
            TeamRow(
                name=cfg.name,
                target=cfg.target,
                sales=sales,
                b_sales=b_sales,
                hrs=hrs,
                headcount=len(team_agents),
            )
        )
    return rows
