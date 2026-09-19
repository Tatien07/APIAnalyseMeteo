from datetime import UTC, datetime, timedelta
from decimal import Decimal

from energy_weather.services.analytics import (
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
