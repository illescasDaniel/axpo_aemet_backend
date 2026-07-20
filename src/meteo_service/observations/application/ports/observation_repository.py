from datetime import datetime
from typing import Protocol

from meteo_service.observations.domain.observation import Observation


class ObservationRepository(Protocol):
    async def get_range(self, station_id: str, start: datetime, end: datetime) -> list[Observation]: ...
    async def upsert_many(self, observations: list[Observation]) -> None: ...
