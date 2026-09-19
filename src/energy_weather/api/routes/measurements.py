from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from energy_weather.db.session import get_db_session
from energy_weather.models.measurement import MeasurementKind
from energy_weather.repositories.measurements import MeasurementRepository
from energy_weather.schemas.measurement import MeasurementRead

router = APIRouter()
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("", response_model=list[MeasurementRead])
async def list_measurements(
    session: DatabaseSession,
    kind: MeasurementKind | None = None,
    location: str | None = None,
    observed_from: datetime | None = None,
    observed_to: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
) -> list[MeasurementRead]:
    measurements = await MeasurementRepository(session).find(
        kind=kind,
        location=location,
        observed_from=observed_from,
        observed_to=observed_to,
        limit=limit,
    )
    return [MeasurementRead.model_validate(item) for item in measurements]
