from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ReadinessResponse(BaseModel):
    status: Literal["ready"] = "ready"
    database: Literal["up"] = "up"


class DataSourceFreshness(BaseModel):
    status: Literal["fresh", "stale", "missing"]
    latest_collected_at: datetime | None
    age_minutes: float | None


class DataFreshnessResponse(BaseModel):
    status: Literal["healthy", "degraded"]
    threshold_minutes: int
    weather: DataSourceFreshness
    energy: DataSourceFreshness
