from sqlalchemy.ext.asyncio import AsyncSession

from energy_weather.collectors.weather.open_meteo import OpenMeteoClient, parse_weather_response
from energy_weather.core.config import Settings
from energy_weather.repositories.measurements import MeasurementRepository


async def collect_weather(
    session: AsyncSession,
    settings: Settings,
    client: OpenMeteoClient | None = None,
) -> tuple[int, int]:
    client = client or OpenMeteoClient(settings.weather_api_url)
    repository = MeasurementRepository(session)
    received = 0
    inserted = 0
    for location in settings.weather_locations:
        response = await client.fetch(
            latitude=location.latitude,
            longitude=location.longitude,
            forecast_hours=settings.weather_forecast_hours,
            past_hours=settings.weather_past_hours,
        )
        measurements = parse_weather_response(response, location=location.name)
        received += len(measurements)
        inserted += await repository.add_many(measurements)
    return received, inserted
