from datetime import datetime

from pydantic import BaseModel


class HourlyEnergyWeatherPoint(BaseModel):
    hour: datetime
    temperature_c: float
    consumption_mw: float


class EnergyWeatherAnalysis(BaseModel):
    hours_requested: int
    points_count: int
    temperature_consumption_correlation: float | None
    points: list[HourlyEnergyWeatherPoint]
