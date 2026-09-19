import asyncio

from energy_weather.collectors.energy.service import collect_energy
from energy_weather.core.config import get_settings
from energy_weather.db.session import SessionFactory


async def run() -> None:
    settings = get_settings()
    async with SessionFactory() as session:
        received, inserted = await collect_energy(session, settings)
    print(f"Energy collection completed: received={received}, inserted={inserted}")


if __name__ == "__main__":
    asyncio.run(run())
