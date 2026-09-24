from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from energy_weather.db.session import get_db_session
from energy_weather.repositories.measurements import MeasurementRepository
from energy_weather.schemas.analytics import EnergyWeatherAnalysis
from energy_weather.services.analytics import build_energy_weather_analysis

router = APIRouter()
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("/weather-energy", response_model=EnergyWeatherAnalysis)
async def weather_energy_analysis(
    session: DatabaseSession,
    hours: Annotated[int, Query(ge=2, le=168)] = 24,
    weather_location: Annotated[str, Query(min_length=1, max_length=100)] = "paris",
) -> EnergyWeatherAnalysis:
    rows = await MeasurementRepository(session).hourly_temperature_consumption(
        hours=hours,
        weather_location=weather_location.lower(),
    )
    return build_energy_weather_analysis(rows, hours_requested=hours)
