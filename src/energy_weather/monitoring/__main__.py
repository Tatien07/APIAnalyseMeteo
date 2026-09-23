import asyncio
import logging
from datetime import UTC, datetime
from time import perf_counter
from uuid import uuid4

from energy_weather.core.config import get_settings
from energy_weather.core.logging import configure_logging
from energy_weather.db.session import SessionFactory
from energy_weather.models.measurement import MeasurementKind
from energy_weather.repositories.measurements import MeasurementRepository
from energy_weather.services.freshness import build_freshness_response

logger = logging.getLogger(__name__)


async def check_data_freshness() -> bool:
    settings = get_settings()
    configure_logging(settings.app_log_level, settings.app_log_format)
    run_id = str(uuid4())
    started_at = perf_counter()
    logger.info(
        "Data freshness check started",
        extra={"event": "data_freshness_check_started", "run_id": run_id},
    )
    try:
        async with SessionFactory() as session:
            repository = MeasurementRepository(session)
            weather_collected_at = await repository.latest_collected_at(
                kind=MeasurementKind.TEMPERATURE,
                location="paris",
            )
            energy_collected_at = await repository.latest_collected_at(
                kind=MeasurementKind.ELECTRICITY_CONSUMPTION,
                location="france",
            )
    except Exception:
        logger.exception(
            "Data freshness check failed",
            extra={
                "event": "data_freshness_check_failed",
                "run_id": run_id,
                "duration_ms": round((perf_counter() - started_at) * 1000, 2),
            },
        )
        return False

    result = build_freshness_response(
        weather_collected_at,
        energy_collected_at,
        now=datetime.now(UTC),
        threshold_minutes=settings.freshness_threshold_minutes,
    )
    log_details = {
        "run_id": run_id,
        "weather_status": result.weather.status,
        "weather_age_minutes": result.weather.age_minutes,
        "energy_status": result.energy.status,
        "energy_age_minutes": result.energy.age_minutes,
        "threshold_minutes": result.threshold_minutes,
        "duration_ms": round((perf_counter() - started_at) * 1000, 2),
    }
    if result.status == "degraded":
        logger.error(
            "Collected data is stale or missing",
            extra={"event": "data_freshness_failed", **log_details},
        )
        return False

    logger.info(
        "Collected data is fresh",
        extra={"event": "data_freshness_check_completed", **log_details},
    )
    return True


if __name__ == "__main__":
    raise SystemExit(0 if asyncio.run(check_data_freshness()) else 1)
