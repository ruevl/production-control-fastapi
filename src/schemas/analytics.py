from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SummaryStats(BaseModel):
    total_batches: int
    open_batches: int
    closed_batches: int
    total_products: int
    aggregated_products: int


class TodayStats(BaseModel):
    created_batches: int
    closed_batches: int
    aggregated_products: int


class ShiftStats(BaseModel):
    total_batches: int
    closed_batches: int
    total_products: int
    aggregated_products: int


class WorkCenterStats(BaseModel):
    id: int
    name: str
    total_batches: int
    closed_batches: int


class DashboardStats(BaseModel):
    summary: SummaryStats
    today: TodayStats
    by_shift: dict[str, ShiftStats]
    top_work_centers: list[WorkCenterStats]
    cached_at: datetime


class ProductionStats(BaseModel):
    total_products: int
    aggregated_products: int
    aggregation_percent: float


class BatchInfo(BaseModel):
    id: int
    batch_number: int
    nomenclature: str
    is_closed: bool


class TimelineStats(BaseModel):
    shift_start: Optional[datetime] = None
    shift_end: Optional[datetime] = None
    closed_at: Optional[datetime] = None


class TeamPerformance(BaseModel):
    team: str
    shift: str
    total_products: int
    aggregated_products: int


class BatchStatistics(BaseModel):
    batch_info: BatchInfo
    production_stats: ProductionStats
    timeline: TimelineStats
    team_performance: TeamPerformance


class BatchComparisonItem(BaseModel):
    batch_id: int
    batch_number: int
    total_products: int
    aggregated_products: int
    aggregation_percent: float


class AverageStats(BaseModel):
    total_products: float
    aggregated_products: float
    aggregation_percent: float


class BatchComparison(BaseModel):
    comparison: list[BatchComparisonItem]
    average: AverageStats
