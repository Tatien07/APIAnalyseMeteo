from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from energy_weather.db.session import get_db_session
from energy_weather.schemas.health import HealthResponse, ReadinessResponse

router = APIRouter()
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse()


@router.get("/ready", response_model=ReadinessResponse)
async def readiness(session: DatabaseSession) -> ReadinessResponse:
    await session.execute(text("SELECT 1"))
    return ReadinessResponse()
