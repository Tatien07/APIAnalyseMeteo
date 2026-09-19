from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from energy_weather.models.measurement import MeasurementKind


class MeasurementRead(BaseModel):
    id: int
    source: str
    location: str
    kind: MeasurementKind
    value: Decimal
    unit: str
    observed_at: datetime
    collected_at: datetime

    model_config = ConfigDict(from_attributes=True)
