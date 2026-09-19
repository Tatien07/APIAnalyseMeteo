from datetime import UTC, datetime
from decimal import Decimal

import httpx
from pydantic import BaseModel

from energy_weather.collectors.types import MeasurementInput
from energy_weather.models.measurement import MeasurementKind

HOURLY_VARIABLES = (
    "temperature_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
    "cloud_cover",
    "shortwave_radiation",
)


class OpenMeteoHourly(BaseModel):
    time: list[datetime]
    temperature_2m: list[float | None]
    relative_humidity_2m: list[float | None]
    wind_speed_10m: list[float | None]
    cloud_cover: list[float | None]
    shortwave_radiation: list[float | None]


class OpenMeteoHourlyUnits(BaseModel):
    temperature_2m: str
    relative_humidity_2m: str
    wind_speed_10m: str
    cloud_cover: str
    shortwave_radiation: str


class OpenMeteoResponse(BaseModel):
    hourly: OpenMeteoHourly
    hourly_units: OpenMeteoHourlyUnits


class OpenMeteoClient:
    def __init__(self, base_url: str, client: httpx.AsyncClient | None = None) -> None:
        self.base_url = base_url
        self._client = client

    async def fetch(
        self,
        *,
        latitude: float,
        longitude: float,
        forecast_hours: int,
        past_hours: int,
    ) -> OpenMeteoResponse:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": ",".join(HOURLY_VARIABLES),
            "timezone": "UTC",
            "forecast_hours": forecast_hours,
            "past_hours": past_hours,
        }
        if self._client is not None:
            response = await self._client.get(self.base_url, params=params)
        else:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(self.base_url, params=params)
        response.raise_for_status()
        return OpenMeteoResponse.model_validate(response.json())


def parse_weather_response(
    response: OpenMeteoResponse,
    *,
    location: str,
    collected_at: datetime | None = None,
) -> list[MeasurementInput]:
    collected_at = collected_at or datetime.now(UTC)
    hourly = response.hourly
    units = response.hourly_units
    variables = (
        (hourly.temperature_2m, MeasurementKind.TEMPERATURE, units.temperature_2m),
        (
            hourly.relative_humidity_2m,
            MeasurementKind.RELATIVE_HUMIDITY,
            units.relative_humidity_2m,
        ),
        (hourly.wind_speed_10m, MeasurementKind.WIND_SPEED, units.wind_speed_10m),
        (hourly.cloud_cover, MeasurementKind.CLOUD_COVER, units.cloud_cover),
        (
            hourly.shortwave_radiation,
            MeasurementKind.SHORTWAVE_RADIATION,
            units.shortwave_radiation,
        ),
    )

    expected_length = len(hourly.time)
    if any(len(values) != expected_length for values, _, _ in variables):
        raise ValueError("Open-Meteo returned hourly arrays with different lengths")

    measurements: list[MeasurementInput] = []
    for index, observed_at in enumerate(hourly.time):
        if observed_at.tzinfo is None:
            observed_at = observed_at.replace(tzinfo=UTC)
        for values, kind, unit in variables:
            value = values[index]
            if value is not None:
                measurements.append(
                    MeasurementInput(
                        source="open-meteo",
                        location=location,
                        kind=kind,
                        value=Decimal(str(value)),
                        unit=unit,
                        observed_at=observed_at,
                        collected_at=collected_at,
                    )
                )
    return measurements
