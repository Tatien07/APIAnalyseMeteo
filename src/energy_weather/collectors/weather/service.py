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
    response = await client.fetch(
        latitude=settings.weather_latitude,
        longitude=settings.weather_longitude,
        forecast_hours=settings.weather_forecast_hours,
        past_hours=settings.weather_past_hours,
    )
    measurements = parse_weather_response(response, location=settings.weather_location_name)
    inserted = await MeasurementRepository(session).add_many(measurements)
    return len(measurements), inserted
