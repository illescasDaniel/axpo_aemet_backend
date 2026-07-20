from dataclasses import dataclass
from datetime import datetime

from meteo_service.observations.domain.station import Station


@dataclass(frozen=True, slots=True)
class ObservationView:
    station: Station
    observed_at: datetime  # Europe/Madrid with offset
    pressure_hpa: float | None = None
    speed_ms: float | None = None
    temperature_c: float | None = None
