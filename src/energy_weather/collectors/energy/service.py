from sqlalchemy.ext.asyncio import AsyncSession

from energy_weather.collectors.energy.eco2mix import Eco2MixClient, parse_eco2mix_response
from energy_weather.core.config import Settings
from energy_weather.repositories.measurements import MeasurementRepository


async def collect_energy(
    session: AsyncSession,
    settings: Settings,
    client: Eco2MixClient | None = None,
) -> tuple[int, int]:
    client = client or Eco2MixClient(settings.energy_api_url)
    response = await client.fetch_latest(limit=settings.energy_record_limit)
    measurements = parse_eco2mix_response(response)
    inserted = await MeasurementRepository(session).add_many(measurements)
    return len(measurements), inserted
