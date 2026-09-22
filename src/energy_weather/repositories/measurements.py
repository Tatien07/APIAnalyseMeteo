from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import Select, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from energy_weather.collectors.types import MeasurementInput
from energy_weather.models.measurement import Measurement, MeasurementKind


class MeasurementRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_many(self, measurements: list[MeasurementInput]) -> int:
        if not measurements:
            return 0

        statement = insert(Measurement).values(
            [
                {
                    "source": item.source,
                    "location": item.location,
                    "kind": item.kind,
                    "value": item.value,
                    "unit": item.unit,
                    "observed_at": item.observed_at,
                    "collected_at": item.collected_at,
                }
                for item in measurements
            ]
        )
        statement = statement.on_conflict_do_nothing(
            constraint="uq_measurement_identity"
        ).returning(Measurement.id)
        result = await self.session.execute(statement)
        inserted_ids = result.scalars().all()
        await self.session.commit()
        return len(inserted_ids)

    async def find(
        self,
        *,
        kind: MeasurementKind | None = None,
        location: str | None = None,
        observed_from: datetime | None = None,
        observed_to: datetime | None = None,
        limit: int = 100,
    ) -> list[Measurement]:
        statement: Select[tuple[Measurement]] = select(Measurement)
        if kind is not None:
            statement = statement.where(Measurement.kind == kind)
        if location is not None:
            statement = statement.where(Measurement.location == location)
        if observed_from is not None:
            statement = statement.where(Measurement.observed_at >= observed_from)
        if observed_to is not None:
            statement = statement.where(Measurement.observed_at <= observed_to)
        statement = statement.order_by(Measurement.observed_at.desc()).limit(limit)
        result = await self.session.scalars(statement)
        return list(result)

    async def latest_collected_at(
        self,
        *,
        kind: MeasurementKind,
        location: str,
    ) -> datetime | None:
        statement = select(func.max(Measurement.collected_at)).where(
            Measurement.kind == kind,
            Measurement.location == location,
        )
        return await self.session.scalar(statement)

    async def hourly_temperature_consumption(
        self,
        *,
        hours: int,
        weather_location: str = "paris",
        energy_location: str = "france",
    ) -> list[tuple[datetime, Decimal, Decimal]]:
        cutoff = datetime.now(UTC) - timedelta(hours=hours)
        weather_hour = func.date_trunc("hour", Measurement.observed_at).label("hour")
        energy_hour = func.date_trunc("hour", Measurement.observed_at).label("hour")

        weather = (
            select(
                weather_hour,
                func.avg(Measurement.value).label("temperature_c"),
            )
            .where(
                Measurement.kind == MeasurementKind.TEMPERATURE,
                Measurement.location == weather_location,
                Measurement.observed_at >= cutoff,
                Measurement.observed_at <= datetime.now(UTC),
            )
            .group_by(weather_hour)
            .subquery()
        )
        energy = (
            select(
                energy_hour,
                func.avg(Measurement.value).label("consumption_mw"),
            )
            .where(
                Measurement.kind == MeasurementKind.ELECTRICITY_CONSUMPTION,
                Measurement.location == energy_location,
                Measurement.observed_at >= cutoff,
                Measurement.observed_at <= datetime.now(UTC),
            )
            .group_by(energy_hour)
            .subquery()
        )

        statement = (
            select(weather.c.hour, weather.c.temperature_c, energy.c.consumption_mw)
            .join(energy, weather.c.hour == energy.c.hour)
            .order_by(weather.c.hour)
        )
        result = await self.session.execute(statement)
        return [(row.hour, row.temperature_c, row.consumption_mw) for row in result]
