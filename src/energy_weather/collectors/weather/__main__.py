import asyncio
import logging
from time import perf_counter
from uuid import uuid4

from energy_weather.collectors.weather.service import collect_weather
from energy_weather.core.config import get_settings
from energy_weather.core.logging import configure_logging
from energy_weather.db.session import SessionFactory

logger = logging.getLogger(__name__)


async def run() -> None:
    settings = get_settings()
    configure_logging(settings.app_log_level, settings.app_log_format)
    run_id = str(uuid4())
    started_at = perf_counter()
    logger.info(
        "Weather collection started",
        extra={"event": "weather_collection_started", "run_id": run_id},
    )
    try:
        async with SessionFactory() as session:
            received, inserted = await collect_weather(session, settings)
    except Exception:
        logger.exception(
            "Weather collection failed",
            extra={
                "event": "weather_collection_failed",
                "run_id": run_id,
                "duration_ms": round((perf_counter() - started_at) * 1000, 2),
            },
        )
        raise
    logger.info(
        "Weather collection completed",
        extra={
            "event": "weather_collection_completed",
            "run_id": run_id,
            "received": received,
            "inserted": inserted,
            "duration_ms": round((perf_counter() - started_at) * 1000, 2),
        },
    )


if __name__ == "__main__":
    asyncio.run(run())
