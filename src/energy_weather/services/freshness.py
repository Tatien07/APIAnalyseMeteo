from datetime import UTC, datetime, timedelta

from energy_weather.schemas.health import DataFreshnessResponse, DataSourceFreshness


def evaluate_freshness(
    latest_collected_at: datetime | None,
    *,
    now: datetime,
    threshold: timedelta,
) -> DataSourceFreshness:
    if latest_collected_at is None:
        return DataSourceFreshness(
            status="missing",
            latest_collected_at=None,
            age_minutes=None,
        )

    if latest_collected_at.tzinfo is None:
        latest_collected_at = latest_collected_at.replace(tzinfo=UTC)

    age = max(now - latest_collected_at, timedelta())
    return DataSourceFreshness(
        status="fresh" if age <= threshold else "stale",
        latest_collected_at=latest_collected_at,
        age_minutes=round(age.total_seconds() / 60, 1),
    )


def build_freshness_response(
    weather_collected_at: datetime | None,
    energy_collected_at: datetime | None,
    *,
    now: datetime,
    threshold_minutes: int,
) -> DataFreshnessResponse:
    threshold = timedelta(minutes=threshold_minutes)
    weather = evaluate_freshness(weather_collected_at, now=now, threshold=threshold)
    energy = evaluate_freshness(energy_collected_at, now=now, threshold=threshold)
    status = "healthy" if weather.status == energy.status == "fresh" else "degraded"
    return DataFreshnessResponse(
        status=status,
        threshold_minutes=threshold_minutes,
        weather=weather,
        energy=energy,
    )
