from dataclasses import dataclass
from datetime import datetime

from meteo_service.observations.domain.station import Station


@dataclass(frozen=True, slots=True)
class Observation:
    station: Station
    observed_at: datetime
    pressure_hpa: float | None
    speed_ms: float | None
    temperature_c: float | None
