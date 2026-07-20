from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from tests.conftest import STATION_GDC, STATION_JCI

from meteo_service.observations.adapters.database.observation_repository import SqlAlchemyObservationRepository
from meteo_service.observations.domain.observation import Observation
from meteo_service.observations.domain.station import Station
from meteo_service.shared.adapters.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork


pytestmark = pytest.mark.integration


def _observation(
    *,
    station: Station = STATION_JCI,
    observed_at: datetime,
    temperature_c: float = -4.0,
    pressure_hpa: float = 990.0,
    speed_ms: float = 5.0,
) -> Observation:
    return Observation(
        station=station,
        observed_at=observed_at,
        temperature_c=temperature_c,
        pressure_hpa=pressure_hpa,
        speed_ms=speed_ms,
    )


async def _upsert(repo: SqlAlchemyObservationRepository, uow: SqlAlchemyUnitOfWork, observations: list[Observation]):
    async with uow:
        await repo.upsert_many(observations)


async def test_given_upserted_rows_when_get_range_then_returns_matching_domain_observations(
    db_session: AsyncSession,
):
    # given
    repo = SqlAlchemyObservationRepository(db_session)
    uow = SqlAlchemyUnitOfWork(db_session)
    first = _observation(observed_at=datetime(2024, 1, 1, 10, 10, 0, tzinfo=UTC))
    second = _observation(
        observed_at=datetime(2024, 1, 1, 10, 50, 0, tzinfo=UTC),
        temperature_c=-2.0,
        pressure_hpa=992.0,
        speed_ms=6.0,
    )
    await _upsert(repo, uow, [first, second])

    # when
    result = await repo.get_range(
        STATION_JCI.id,
        datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC),
        datetime(2024, 1, 1, 11, 0, 0, tzinfo=UTC),
    )

    # then
    assert len(result) == 2
    assert result[0].station == STATION_JCI
    assert result[0].observed_at == first.observed_at
    assert result[0].temperature_c == -4.0
    assert result[1].observed_at == second.observed_at
    assert result[1].temperature_c == -2.0


async def test_given_existing_row_when_upserting_same_key_then_updates_metrics(db_session: AsyncSession):
    # given
    repo = SqlAlchemyObservationRepository(db_session)
    uow = SqlAlchemyUnitOfWork(db_session)
    observed_at = datetime(2024, 1, 1, 10, 10, 0, tzinfo=UTC)
    await _upsert(
        repo,
        uow,
        [_observation(observed_at=observed_at)],
    )

    # when
    updated_station = Station(id=STATION_JCI.id, name="JCI Estacion meteorologica")
    await _upsert(
        repo,
        uow,
        [
            _observation(
                station=updated_station,
                observed_at=observed_at,
                temperature_c=-1.0,
                pressure_hpa=995.0,
                speed_ms=7.0,
            )
        ],
    )
    result = await repo.get_range(STATION_JCI.id, observed_at, observed_at)

    # then
    assert len(result) == 1
    assert result[0].station.name == "JCI Estacion meteorologica"
    assert result[0].temperature_c == -1.0
    assert result[0].pressure_hpa == 995.0
    assert result[0].speed_ms == 7.0


async def test_given_no_rows_when_get_range_then_returns_empty_list(db_session: AsyncSession):
    # given
    repo = SqlAlchemyObservationRepository(db_session)

    # when
    result = await repo.get_range(
        STATION_JCI.id,
        datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        datetime(2024, 1, 2, 0, 0, 0, tzinfo=UTC),
    )

    # then
    assert result == []


async def test_given_rows_outside_range_when_get_range_then_returns_empty_list(db_session: AsyncSession):
    # given
    repo = SqlAlchemyObservationRepository(db_session)
    uow = SqlAlchemyUnitOfWork(db_session)
    await _upsert(
        repo,
        uow,
        [_observation(observed_at=datetime(2024, 1, 1, 10, 10, 0, tzinfo=UTC))],
    )

    # when
    result = await repo.get_range(
        STATION_JCI.id,
        datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
        datetime(2024, 1, 1, 13, 0, 0, tzinfo=UTC),
    )

    # then
    assert result == []


async def test_given_rows_for_other_station_when_get_range_then_returns_empty_list(db_session: AsyncSession):
    # given
    repo = SqlAlchemyObservationRepository(db_session)
    uow = SqlAlchemyUnitOfWork(db_session)
    await _upsert(
        repo,
        uow,
        [_observation(observed_at=datetime(2024, 1, 1, 10, 10, 0, tzinfo=UTC))],
    )

    # when
    result = await repo.get_range(
        STATION_GDC.id,
        datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC),
        datetime(2024, 1, 1, 11, 0, 0, tzinfo=UTC),
    )

    # then
    assert result == []


async def test_given_empty_observations_when_upserting_then_does_nothing(db_session: AsyncSession):
    # given
    repo = SqlAlchemyObservationRepository(db_session)
    uow = SqlAlchemyUnitOfWork(db_session)

    # when
    async with uow:
        await repo.upsert_many([])
    result = await repo.get_range(
        STATION_JCI.id,
        datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC),
        datetime(2024, 1, 2, 0, 0, 0, tzinfo=UTC),
    )

    # then
    assert result == []
