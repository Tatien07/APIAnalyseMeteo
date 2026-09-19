from datetime import UTC, datetime
from decimal import Decimal

import httpx
import pytest

from energy_weather.collectors.weather.open_meteo import (
    OpenMeteoClient,
    OpenMeteoResponse,
    parse_weather_response,
)
from energy_weather.models.measurement import MeasurementKind

PAYLOAD = {
    "hourly": {
        "time": ["2026-09-02T12:00", "2026-09-02T13:00"],
        "temperature_2m": [21.5, 22.0],
        "relative_humidity_2m": [60, 58],
        "wind_speed_10m": [12.4, 13.1],
        "cloud_cover": [25, 20],
        "shortwave_radiation": [480, 510],
    },
    "hourly_units": {
        "temperature_2m": "°C",
        "relative_humidity_2m": "%",
        "wind_speed_10m": "km/h",
        "cloud_cover": "%",
        "shortwave_radiation": "W/m²",
    },
}


def test_parser_creates_one_measurement_per_time_and_variable() -> None:
    response = OpenMeteoResponse.model_validate(PAYLOAD)
    collected_at = datetime(2026, 9, 2, 11, 55, tzinfo=UTC)

    result = parse_weather_response(response, location="paris", collected_at=collected_at)

    assert len(result) == 10
    assert result[0].kind == MeasurementKind.TEMPERATURE
    assert result[0].value == Decimal("21.5")
    assert result[0].unit == "°C"
    assert result[0].observed_at == datetime(2026, 9, 2, 12, tzinfo=UTC)
    assert result[0].collected_at == collected_at


@pytest.mark.asyncio
async def test_client_sends_expected_query_parameters() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["timezone"] == "UTC"
        assert request.url.params["forecast_hours"] == "2"
        assert request.url.params["past_hours"] == "24"
        assert "temperature_2m" in request.url.params["hourly"]
        return httpx.Response(200, json=PAYLOAD)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = OpenMeteoClient("https://weather.test/v1/forecast", http_client)
        response = await client.fetch(
            latitude=48.8566,
            longitude=2.3522,
            forecast_hours=2,
            past_hours=24,
        )

    assert response.hourly.temperature_2m == [21.5, 22.0]


def test_parser_rejects_inconsistent_arrays() -> None:
    payload = {**PAYLOAD, "hourly": {**PAYLOAD["hourly"], "cloud_cover": [25]}}
    response = OpenMeteoResponse.model_validate(payload)

    with pytest.raises(ValueError, match="different lengths"):
        parse_weather_response(response, location="paris")
