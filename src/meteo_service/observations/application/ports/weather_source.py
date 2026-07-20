from datetime import datetime
from typing import Protocol

from meteo_service.observations.domain.observation import Observation


class WeatherSource(Protocol):
    async def fetch(
        self,
        station_id: str,
        start: datetime,
        end: datetime,
    ) -> list[Observation]: ...
