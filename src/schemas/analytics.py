from datetime import datetime
from typing import Any

from pydantic import BaseModel


class DashboardStats(BaseModel):
    summary: dict[str, Any]
    today: dict[str, Any]
    by_shift: dict[str, dict[str, Any]]
    top_work_centers: list[dict[str, Any]]
    cached_at: datetime


class BatchStatistics(BaseModel):
    batch_info: dict[str, Any]
    production_stats: dict[str, Any]
    timeline: dict[str, Any]
    team_performance: dict[str, Any]


class BatchComparison(BaseModel):
    comparison: list[dict[str, Any]]
    average: dict[str, float]
