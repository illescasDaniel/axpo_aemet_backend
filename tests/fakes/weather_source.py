import asyncio
from datetime import datetime

from meteo_service.observations.domain.observation import Observation


class FakeWeatherSource:
    def __init__(self, rows: list[Observation], *, delay_seconds: float = 0.0):
        self._rows = rows
        self._delay_seconds = delay_seconds
        self.fetch_count = 0

    async def fetch(self, station_id: str, start: datetime, end: datetime) -> list[Observation]:
        self.fetch_count += 1
        if self._delay_seconds:
            await asyncio.sleep(self._delay_seconds)
        return [row for row in self._rows if row.station.id == station_id and start <= row.observed_at <= end]


class FailingWeatherSource:
    def __init__(self, message: str = "AEMET error 401: API key no valida o caducada"):
        self._message = message

    async def fetch(self, station_id: str, start: datetime, end: datetime) -> list[Observation]:
        raise RuntimeError(self._message)
