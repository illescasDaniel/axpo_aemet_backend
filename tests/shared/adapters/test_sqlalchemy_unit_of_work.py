from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from tests.conftest import STATION_JCI

from meteo_service.observations.adapters.database.observation_repository import SqlAlchemyObservationRepository
from meteo_service.observations.domain.observation import Observation
from meteo_service.shared.adapters.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


pytestmark = pytest.mark.integration


def _observation(*, observed_at: datetime, temperature_c: float = -4.0) -> Observation:
    return Observation(
        station=STATION_JCI,
        observed_at=observed_at,
        temperature_c=temperature_c,
        pressure_hpa=990.0,
        speed_ms=5.0,
    )


async def test_given_upsert_inside_uow_when_block_exits_then_commits(db_session: AsyncSession):
    # given
    repo = SqlAlchemyObservationRepository(db_session)
    uow = SqlAlchemyUnitOfWork(db_session)
    observed_at = datetime(2024, 1, 1, 10, 10, 0, tzinfo=UTC)

    # when
    async with uow:
        await repo.upsert_many([_observation(observed_at=observed_at)])

    result = await repo.get_range(STATION_JCI.id, observed_at, observed_at)

    # then
    assert len(result) == 1
    assert result[0].temperature_c == -4.0


async def test_given_exception_inside_uow_when_block_exits_then_rolls_back(db_session: AsyncSession):
    # given
    repo = SqlAlchemyObservationRepository(db_session)
    uow = SqlAlchemyUnitOfWork(db_session)
    observed_at = datetime(2024, 1, 1, 10, 10, 0, tzinfo=UTC)

    # when/then
    with pytest.raises(RuntimeError, match="boom"):
        async with uow:
            await repo.upsert_many([_observation(observed_at=observed_at)])
            raise RuntimeError("boom")

    result = await repo.get_range(STATION_JCI.id, observed_at, observed_at)
    assert result == []
