from datetime import datetime
from decimal import Decimal
from math import sqrt

from energy_weather.schemas.analytics import EnergyWeatherAnalysis, HourlyEnergyWeatherPoint


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
