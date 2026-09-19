from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import DateTime, Enum, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from energy_weather.db.base import Base


class MeasurementKind(StrEnum):
    TEMPERATURE = "temperature"
    RELATIVE_HUMIDITY = "relative_humidity"
    WIND_SPEED = "wind_speed"
    CLOUD_COVER = "cloud_cover"
    SHORTWAVE_RADIATION = "shortwave_radiation"
    ELECTRICITY_CONSUMPTION = "electricity_consumption"
    CARBON_INTENSITY = "carbon_intensity"
    NUCLEAR_PRODUCTION = "nuclear_production"
    WIND_PRODUCTION = "wind_production"
    SOLAR_PRODUCTION = "solar_production"
    HYDRO_PRODUCTION = "hydro_production"
    GAS_PRODUCTION = "gas_production"
    COAL_PRODUCTION = "coal_production"
    OIL_PRODUCTION = "oil_production"
    BIOENERGY_PRODUCTION = "bioenergy_production"


class Measurement(Base):
    __tablename__ = "measurements"
    __table_args__ = (
        UniqueConstraint(
            "source", "location", "kind", "observed_at", name="uq_measurement_identity"
        ),
        Index("ix_measurements_kind_location_time", "kind", "location", "observed_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(50))
    location: Mapped[str] = mapped_column(String(100))
    kind: Mapped[MeasurementKind] = mapped_column(Enum(MeasurementKind, native_enum=False))
    value: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    unit: Mapped[str] = mapped_column(String(20))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
