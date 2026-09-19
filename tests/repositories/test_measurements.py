from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import pytest

from energy_weather.collectors.types import MeasurementInput
from energy_weather.models.measurement import MeasurementKind
from energy_weather.repositories.measurements import MeasurementRepository


@pytest.mark.asyncio
async def test_add_many_counts_returned_ids_instead_of_driver_rowcount() -> None:
    result = Mock()
    result.scalars.return_value.all.return_value = [101]
    session = AsyncMock()
    session.execute.return_value = result
    repository = MeasurementRepository(session)
    measurement = MeasurementInput(
        source="rte-eco2mix",
        location="france",
        kind=MeasurementKind.ELECTRICITY_CONSUMPTION,
        value=Decimal("48000"),
        unit="MW",
        observed_at=datetime(2026, 9, 8, 12, 15, tzinfo=UTC),
        collected_at=datetime(2026, 9, 8, 12, 20, tzinfo=UTC),
    )

    inserted = await repository.add_many([measurement])

    assert inserted == 1
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_add_many_skips_database_for_empty_batch() -> None:
    session = AsyncMock()

    inserted = await MeasurementRepository(session).add_many([])

    assert inserted == 0
    session.execute.assert_not_awaited()
