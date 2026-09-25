from datetime import UTC, datetime, timedelta
from decimal import Decimal

from energy_weather.models.measurement import MeasurementKind
from energy_weather.services.analytics import (
    build_energy_summary,
    build_energy_weather_analysis,
    pearson_correlation,
)


def test_pearson_correlation_detects_positive_relation() -> None:
    assert pearson_correlation([(1, 10), (2, 20), (3, 30)]) == 1.0


def test_pearson_correlation_returns_none_for_constant_series() -> None:
    assert pearson_correlation([(1, 10), (1, 20)]) is None


def test_build_analysis_serializes_hourly_rows() -> None:
    start = datetime(2026, 9, 8, 10, tzinfo=UTC)
    rows = [
        (start, Decimal("12.5"), Decimal("45000")),
        (start + timedelta(hours=1), Decimal("13.5"), Decimal("44000")),
    ]

    analysis = build_energy_weather_analysis(rows, hours_requested=24)

    assert analysis.hours_requested == 24
    assert analysis.points_count == 2
    assert analysis.points[0].temperature_c == 12.5
    assert analysis.temperature_consumption_correlation == -1.0


def test_build_energy_summary_calculates_generation_shares() -> None:
    averages = {
        MeasurementKind.ELECTRICITY_CONSUMPTION: Decimal("50000"),
        MeasurementKind.CARBON_INTENSITY: Decimal("30"),
        MeasurementKind.NUCLEAR_PRODUCTION: Decimal("60"),
        MeasurementKind.WIND_PRODUCTION: Decimal("10"),
        MeasurementKind.SOLAR_PRODUCTION: Decimal("5"),
        MeasurementKind.HYDRO_PRODUCTION: Decimal("10"),
        MeasurementKind.BIOENERGY_PRODUCTION: Decimal("5"),
        MeasurementKind.GAS_PRODUCTION: Decimal("10"),
    }

    summary = build_energy_summary(averages, hours_requested=24)

    assert summary.average_consumption_mw == 50000
    assert summary.average_carbon_intensity_gco2_kwh == 30
    assert summary.average_total_production_mw == 100
    assert summary.renewable_share_percent == 30
    assert summary.low_carbon_share_percent == 90
    assert summary.fossil_share_percent == 10
