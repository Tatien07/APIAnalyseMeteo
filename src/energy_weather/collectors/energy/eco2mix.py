from datetime import UTC, datetime
from decimal import Decimal

import httpx
from pydantic import BaseModel

from energy_weather.collectors.types import MeasurementInput
from energy_weather.models.measurement import MeasurementKind

SELECTED_FIELDS = (
    "date_heure",
    "consommation",
    "taux_co2",
    "nucleaire",
    "eolien",
    "solaire",
    "hydraulique",
    "gaz",
    "charbon",
    "fioul",
    "bioenergies",
)


class Eco2MixRecord(BaseModel):
    date_heure: datetime
    consommation: float | None = None
    taux_co2: float | None = None
    nucleaire: float | None = None
    eolien: float | None = None
    solaire: float | None = None
    hydraulique: float | None = None
    gaz: float | None = None
    charbon: float | None = None
    fioul: float | None = None
    bioenergies: float | None = None


class Eco2MixResponse(BaseModel):
    total_count: int
    results: list[Eco2MixRecord]


class Eco2MixClient:
    def __init__(self, base_url: str, client: httpx.AsyncClient | None = None) -> None:
        self.base_url = base_url
        self._client = client

    async def fetch_latest(self, *, limit: int) -> Eco2MixResponse:
        params = {
            "select": ",".join(SELECTED_FIELDS),
            "where": "consommation is not null",
            "order_by": "date_heure desc",
            "limit": limit,
            "timezone": "UTC",
        }
        if self._client is not None:
            response = await self._client.get(self.base_url, params=params)
        else:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(self.base_url, params=params)
        response.raise_for_status()
        return Eco2MixResponse.model_validate(response.json())


def parse_eco2mix_response(
    response: Eco2MixResponse,
    *,
    collected_at: datetime | None = None,
) -> list[MeasurementInput]:
    collected_at = collected_at or datetime.now(UTC)
    field_mapping = (
        ("consommation", MeasurementKind.ELECTRICITY_CONSUMPTION, "MW"),
        ("taux_co2", MeasurementKind.CARBON_INTENSITY, "gCO2/kWh"),
        ("nucleaire", MeasurementKind.NUCLEAR_PRODUCTION, "MW"),
        ("eolien", MeasurementKind.WIND_PRODUCTION, "MW"),
        ("solaire", MeasurementKind.SOLAR_PRODUCTION, "MW"),
        ("hydraulique", MeasurementKind.HYDRO_PRODUCTION, "MW"),
        ("gaz", MeasurementKind.GAS_PRODUCTION, "MW"),
        ("charbon", MeasurementKind.COAL_PRODUCTION, "MW"),
        ("fioul", MeasurementKind.OIL_PRODUCTION, "MW"),
        ("bioenergies", MeasurementKind.BIOENERGY_PRODUCTION, "MW"),
    )

    measurements: list[MeasurementInput] = []
    for record in response.results:
        observed_at = record.date_heure
        if observed_at.tzinfo is None:
            observed_at = observed_at.replace(tzinfo=UTC)
        else:
            observed_at = observed_at.astimezone(UTC)

        for field_name, kind, unit in field_mapping:
            value = getattr(record, field_name)
            if value is not None:
                measurements.append(
                    MeasurementInput(
                        source="rte-eco2mix",
                        location="france",
                        kind=kind,
                        value=Decimal(str(value)),
                        unit=unit,
                        observed_at=observed_at,
                        collected_at=collected_at,
                    )
                )
    return measurements
