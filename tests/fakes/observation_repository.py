from datetime import datetime

from meteo_service.observations.domain.observation import Observation


class FakeObservationRepository:
    def __init__(self, rows: list[Observation] | None = None):
        self._rows = list(rows or [])

    async def get_range(self, station_id: str, start: datetime, end: datetime) -> list[Observation]:
        return [row for row in self._rows if row.station.id == station_id and start <= row.observed_at <= end]

    async def upsert_many(self, observations: list[Observation]):
        for observation in observations:
            key = (observation.station.id, observation.observed_at)
            self._rows = [row for row in self._rows if (row.station.id, row.observed_at) != key]
            self._rows.append(observation)
