from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from meteo_service.observations.adapters.database.mappers import to_domain, to_row_dict
from meteo_service.observations.adapters.database.orm_models import ObservationRow
from meteo_service.observations.domain.observation import Observation


class SqlAlchemyObservationRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_range(self, station_id: str, start: datetime, end: datetime) -> list[Observation]:
        stmt = (
            select(ObservationRow)
            .where(
                ObservationRow.station_id == station_id,
                ObservationRow.observed_at >= start,
                ObservationRow.observed_at <= end,
            )
            .order_by(ObservationRow.observed_at)
        )
        rows = (await self._session.scalars(stmt)).all()
        return [to_domain(row) for row in rows]

    async def upsert_many(self, observations: list[Observation]):
        if not observations:
            return

        values = [to_row_dict(observation) for observation in observations]
        stmt = insert(ObservationRow).values(values)
        stmt = stmt.on_conflict_do_update(
            index_elements=[ObservationRow.station_id, ObservationRow.observed_at],
            set_={
                "station_name": stmt.excluded.station_name,
                "temperature_c": stmt.excluded.temperature_c,
                "pressure_hpa": stmt.excluded.pressure_hpa,
                "speed_ms": stmt.excluded.speed_ms,
            },
        )
        await self._session.execute(stmt)
