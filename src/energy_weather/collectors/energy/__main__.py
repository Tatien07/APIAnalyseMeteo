import asyncio
import logging
from time import perf_counter
from uuid import uuid4

from energy_weather.collectors.energy.service import collect_energy
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
        "Energy collection started",
        extra={"event": "energy_collection_started", "run_id": run_id},
    )
    try:
        async with SessionFactory() as session:
            received, inserted = await collect_energy(session, settings)
    except Exception:
        logger.exception(
            "Energy collection failed",
            extra={
                "event": "energy_collection_failed",
                "run_id": run_id,
                "duration_ms": round((perf_counter() - started_at) * 1000, 2),
            },
        )
        raise
    logger.info(
        "Energy collection completed",
        extra={
            "event": "energy_collection_completed",
            "run_id": run_id,
            "received": received,
            "inserted": inserted,
            "duration_ms": round((perf_counter() - started_at) * 1000, 2),
        },
    )


if __name__ == "__main__":
    asyncio.run(run())
