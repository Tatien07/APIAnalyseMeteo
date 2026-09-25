from datetime import datetime
from decimal import Decimal
from math import sqrt

from energy_weather.models.measurement import MeasurementKind
from energy_weather.schemas.analytics import (
    EnergySummary,
    EnergyWeatherAnalysis,
    HourlyEnergyWeatherPoint,
)

RENEWABLE_KINDS = {
    MeasurementKind.WIND_PRODUCTION,
    MeasurementKind.SOLAR_PRODUCTION,
    MeasurementKind.HYDRO_PRODUCTION,
    MeasurementKind.BIOENERGY_PRODUCTION,
}
FOSSIL_KINDS = {
    MeasurementKind.GAS_PRODUCTION,
    MeasurementKind.COAL_PRODUCTION,
    MeasurementKind.OIL_PRODUCTION,
}
PRODUCTION_KINDS = RENEWABLE_KINDS | FOSSIL_KINDS | {MeasurementKind.NUCLEAR_PRODUCTION}


def pearson_correlation(pairs: list[tuple[float, float]]) -> float | None:
    if len(pairs) < 2:
        return None

    x_mean = sum(x for x, _ in pairs) / len(pairs)
    y_mean = sum(y for _, y in pairs) / len(pairs)
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in pairs)
    x_variance = sum((x - x_mean) ** 2 for x, _ in pairs)
    y_variance = sum((y - y_mean) ** 2 for _, y in pairs)
    denominator = sqrt(x_variance * y_variance)
    if denominator == 0:
        return None
    return numerator / denominator


def build_energy_weather_analysis(
    rows: list[tuple[datetime, Decimal, Decimal]],
    *,
    hours_requested: int,
) -> EnergyWeatherAnalysis:
    points = [
        HourlyEnergyWeatherPoint(
            hour=hour,
            temperature_c=float(temperature),
            consumption_mw=float(consumption),
        )
        for hour, temperature, consumption in rows
    ]
    correlation = pearson_correlation(
        [(point.temperature_c, point.consumption_mw) for point in points]
    )
    return EnergyWeatherAnalysis(
        hours_requested=hours_requested,
        points_count=len(points),
        temperature_consumption_correlation=correlation,
        points=points,
    )


def build_energy_summary(
    averages: dict[MeasurementKind, Decimal],
    *,
    hours_requested: int,
) -> EnergySummary:
    production = {
        kind: max(float(averages.get(kind, Decimal())), 0.0) for kind in PRODUCTION_KINDS
    }
    total = sum(production.values())
    renewable = sum(production[kind] for kind in RENEWABLE_KINDS)
    fossil = sum(production[kind] for kind in FOSSIL_KINDS)
    low_carbon = renewable + production[MeasurementKind.NUCLEAR_PRODUCTION]

    def share(value: float) -> float | None:
        return round(value / total * 100, 2) if total > 0 else None

    consumption = averages.get(MeasurementKind.ELECTRICITY_CONSUMPTION)
    carbon = averages.get(MeasurementKind.CARBON_INTENSITY)
    return EnergySummary(
        hours_requested=hours_requested,
        average_consumption_mw=float(consumption) if consumption is not None else None,
        average_carbon_intensity_gco2_kwh=float(carbon) if carbon is not None else None,
        average_total_production_mw=round(total, 2) if total > 0 else None,
        renewable_share_percent=share(renewable),
        low_carbon_share_percent=share(low_carbon),
        fossil_share_percent=share(fossil),
    )
