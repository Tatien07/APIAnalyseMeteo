from datetime import UTC, datetime
from decimal import Decimal

import httpx
import pytest

from energy_weather.collectors.energy.eco2mix import (
    Eco2MixClient,
    Eco2MixResponse,
    parse_eco2mix_response,
)
from energy_weather.models.measurement import MeasurementKind

PAYLOAD = {
    "total_count": 1,
    "results": [
        {
            "date_heure": "2026-09-08T12:15:00+00:00",
            "consommation": 48500,
            "taux_co2": 28,
            "nucleaire": 39000,
            "eolien": 4500,
            "solaire": 7200,
            "hydraulique": 5600,
            "gaz": 800,
            "charbon": 0,
            "fioul": None,
            "bioenergies": 1100,
        }
    ],
}


def test_parser_normalizes_energy_measurements() -> None:
    response = Eco2MixResponse.model_validate(PAYLOAD)
    collected_at = datetime(2026, 9, 8, 12, 20, tzinfo=UTC)

    result = parse_eco2mix_response(response, collected_at=collected_at)

    assert len(result) == 9
    assert result[0].kind == MeasurementKind.ELECTRICITY_CONSUMPTION
    assert result[0].value == Decimal("48500.0")
    assert result[0].unit == "MW"
    assert result[0].location == "france"
    assert result[0].observed_at == datetime(2026, 9, 8, 12, 15, tzinfo=UTC)
    assert result[1].kind == MeasurementKind.CARBON_INTENSITY
    assert result[1].unit == "gCO2/kWh"


@pytest.mark.asyncio
async def test_client_requests_latest_non_null_records() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["limit"] == "12"
        assert request.url.params["order_by"] == "date_heure desc"
        assert request.url.params["where"] == "consommation is not null"
        assert "taux_co2" in request.url.params["select"]
        return httpx.Response(200, json=PAYLOAD)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = Eco2MixClient("https://energy.test/records", http_client)
        response = await client.fetch_latest(limit=12)

    assert response.results[0].consommation == 48500


def test_parser_converts_offset_to_utc() -> None:
    payload = {
        "total_count": 1,
        "results": [
            {
                "date_heure": "2026-09-08T14:15:00+02:00",
                "consommation": 48000,
            }
        ],
    }
    response = Eco2MixResponse.model_validate(payload)

    result = parse_eco2mix_response(response)

    assert result[0].observed_at == datetime(2026, 9, 8, 12, 15, tzinfo=UTC)
