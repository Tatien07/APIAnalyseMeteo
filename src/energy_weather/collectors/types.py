from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from energy_weather.models.measurement import MeasurementKind


@dataclass(frozen=True, slots=True)
class MeasurementInput:
    source: str
    location: str
    kind: MeasurementKind
    value: Decimal
    unit: str
    observed_at: datetime
    collected_at: datetime
