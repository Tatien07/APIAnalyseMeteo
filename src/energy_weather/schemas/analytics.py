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


class EnergySummary(BaseModel):
    hours_requested: int
    average_consumption_mw: float | None
    average_carbon_intensity_gco2_kwh: float | None
    average_total_production_mw: float | None
    renewable_share_percent: float | None
    low_carbon_share_percent: float | None
    fossil_share_percent: float | None
