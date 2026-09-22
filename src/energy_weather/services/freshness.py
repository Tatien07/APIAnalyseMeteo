from datetime import UTC, datetime, timedelta

from energy_weather.schemas.health import DataSourceFreshness


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
