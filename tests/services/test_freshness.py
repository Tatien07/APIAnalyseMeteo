from datetime import UTC, datetime, timedelta

from energy_weather.services.freshness import build_freshness_response, evaluate_freshness


def test_missing_data_is_reported() -> None:
    result = evaluate_freshness(
        None,
        now=datetime.now(UTC),
        threshold=timedelta(hours=3),
    )

    assert result.status == "missing"
    assert result.age_minutes is None


def test_recent_data_is_fresh() -> None:
    now = datetime.now(UTC)
    result = evaluate_freshness(
        now - timedelta(minutes=30),
        now=now,
        threshold=timedelta(hours=3),
    )

    assert result.status == "fresh"
    assert result.age_minutes == 30.0


def test_old_data_is_stale() -> None:
    now = datetime.now(UTC)
    result = evaluate_freshness(
        now - timedelta(hours=4),
        now=now,
        threshold=timedelta(hours=3),
    )

    assert result.status == "stale"
    assert result.age_minutes == 240.0


def test_global_status_is_degraded_when_one_source_is_stale() -> None:
    now = datetime.now(UTC)
    result = build_freshness_response(
        now - timedelta(minutes=30),
        now - timedelta(hours=4),
        now=now,
        threshold_minutes=180,
    )

    assert result.status == "degraded"
    assert result.weather.status == "fresh"
    assert result.energy.status == "stale"
