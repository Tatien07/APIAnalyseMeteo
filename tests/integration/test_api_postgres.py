from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx
import pytest
from sqlalchemy import text

from energy_weather.collectors.types import MeasurementInput
from energy_weather.db.session import SessionFactory
from energy_weather.models.measurement import MeasurementKind
from energy_weather.repositories.measurements import MeasurementRepository

pytestmark = pytest.mark.integration


async def test_alembic_created_measurements_table(api_client: httpx.AsyncClient) -> None:
    async with SessionFactory() as session:
        table_name = await session.scalar(text("SELECT to_regclass('public.measurements')"))

    assert table_name == "measurements"
    response = await api_client.get("/api/v1/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "up"}


async def test_measurement_is_idempotent_and_visible_from_api(
    api_client: httpx.AsyncClient,
) -> None:
    observed_at = datetime.now(UTC) - timedelta(minutes=30)
    measurement = MeasurementInput(
        source="integration-test",
        location="paris",
        kind=MeasurementKind.TEMPERATURE,
        value=Decimal("12.5"),
        unit="°C",
        observed_at=observed_at,
        collected_at=datetime.now(UTC),
    )

    async with SessionFactory() as session:
        repository = MeasurementRepository(session)
        first_insert = await repository.add_many([measurement])
        duplicate_insert = await repository.add_many([measurement])

    assert first_insert == 1
    assert duplicate_insert == 0

    response = await api_client.get(
        "/api/v1/measurements",
        params={"location": "paris", "kind": "temperature"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert float(payload[0]["value"]) == 12.5
    assert payload[0]["source"] == "integration-test"


async def test_analytics_reads_hourly_values_from_postgres(
    api_client: httpx.AsyncClient,
) -> None:
    now = datetime.now(UTC).replace(minute=15, second=0, microsecond=0)
    measurements: list[MeasurementInput] = []
    for offset, temperature, consumption in [
        (2, "10", "40000"),
        (1, "15", "45000"),
    ]:
        observed_at = now - timedelta(hours=offset)
        collected_at = datetime.now(UTC)
        measurements.extend(
            [
                MeasurementInput(
                    source="integration-weather",
                    location="paris",
                    kind=MeasurementKind.TEMPERATURE,
                    value=Decimal(temperature),
                    unit="°C",
                    observed_at=observed_at,
                    collected_at=collected_at,
                ),
                MeasurementInput(
                    source="integration-energy",
                    location="france",
                    kind=MeasurementKind.ELECTRICITY_CONSUMPTION,
                    value=Decimal(consumption),
                    unit="MW",
                    observed_at=observed_at,
                    collected_at=collected_at,
                ),
            ]
        )

    async with SessionFactory() as session:
        inserted = await MeasurementRepository(session).add_many(measurements)

    assert inserted == 4
    response = await api_client.get("/api/v1/analytics/weather-energy", params={"hours": 6})
    assert response.status_code == 200
    payload = response.json()
    assert payload["points_count"] == 2
    assert payload["temperature_consumption_correlation"] == 1.0

    lyon_response = await api_client.get(
        "/api/v1/analytics/weather-energy",
        params={"hours": 6, "weather_location": "lyon"},
    )
    assert lyon_response.status_code == 200
    assert lyon_response.json()["points_count"] == 0

    summary_response = await api_client.get(
        "/api/v1/analytics/energy-summary",
        params={"hours": 6},
    )
    assert summary_response.status_code == 200
    assert summary_response.json()["average_consumption_mw"] == 42500.0


async def test_data_freshness_reports_recent_collections(
    api_client: httpx.AsyncClient,
) -> None:
    now = datetime.now(UTC)
    measurements = [
        MeasurementInput(
            source="integration-weather",
            location="paris",
            kind=MeasurementKind.TEMPERATURE,
            value=Decimal("18"),
            unit="°C",
            observed_at=now,
            collected_at=now,
        ),
        MeasurementInput(
            source="integration-energy",
            location="france",
            kind=MeasurementKind.ELECTRICITY_CONSUMPTION,
            value=Decimal("42000"),
            unit="MW",
            observed_at=now,
            collected_at=now,
        ),
    ]
    async with SessionFactory() as session:
        await MeasurementRepository(session).add_many(measurements)

    response = await api_client.get("/api/v1/data-freshness")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["weather"]["status"] == "fresh"
    assert payload["energy"]["status"] == "fresh"
