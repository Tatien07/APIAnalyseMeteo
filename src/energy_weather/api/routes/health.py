from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from energy_weather.db.session import get_db_session
from energy_weather.models.measurement import MeasurementKind
from energy_weather.repositories.measurements import MeasurementRepository
from energy_weather.schemas.health import DataFreshnessResponse, HealthResponse, ReadinessResponse
from energy_weather.services.freshness import evaluate_freshness

router = APIRouter()
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse()


@router.get("/ready", response_model=ReadinessResponse)
async def readiness(session: DatabaseSession) -> ReadinessResponse:
    await session.execute(text("SELECT 1"))
    return ReadinessResponse()


@router.get("/data-freshness", response_model=DataFreshnessResponse)
async def data_freshness(
    session: DatabaseSession,
    threshold_minutes: Annotated[int, Query(ge=15, le=1440)] = 180,
) -> DataFreshnessResponse:
    repository = MeasurementRepository(session)
    weather_collected_at = await repository.latest_collected_at(
        kind=MeasurementKind.TEMPERATURE,
        location="paris",
    )
    energy_collected_at = await repository.latest_collected_at(
        kind=MeasurementKind.ELECTRICITY_CONSUMPTION,
        location="france",
    )
    now = datetime.now(UTC)
    threshold = timedelta(minutes=threshold_minutes)
    weather = evaluate_freshness(weather_collected_at, now=now, threshold=threshold)
    energy = evaluate_freshness(energy_collected_at, now=now, threshold=threshold)
    status = "healthy" if weather.status == energy.status == "fresh" else "degraded"
    return DataFreshnessResponse(
        status=status,
        threshold_minutes=threshold_minutes,
        weather=weather,
        energy=energy,
    )
