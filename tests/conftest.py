from collections.abc import AsyncGenerator
from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from httpx2 import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.fakes.observation_repository import FakeObservationRepository
from tests.fakes.unit_of_work import FakeUnitOfWork
from tests.fakes.weather_source import FakeWeatherSource
from tests.settings import TEST_SETTINGS

from meteo_service.observations.adapters.api.dependencies import get_observations_use_case
from meteo_service.observations.application.get_observations import GetObservations
from meteo_service.observations.application.ports.weather_source import WeatherSource
from meteo_service.observations.domain.observation import Observation
from meteo_service.observations.domain.station import Station
from meteo_service.shared.adapters.api.app import create_app
from meteo_service.shared.database import Database
from meteo_service.shared.single_flight import SingleFlight


OBSERVATIONS_PATH = "/api/v1/observations"

STATION_JCI = Station(id="89064", name="Juan Carlos I")
STATION_GDC = Station(id="89070", name="Gabriel de Castilla")

DEFAULT_ROWS = [
    Observation(
        station=STATION_JCI,
        observed_at=datetime(2024, 1, 1, 10, 10, 0, tzinfo=UTC),
        temperature_c=-4.0,
        pressure_hpa=990.0,
        speed_ms=5.0,
    )
]

type ApiClientFixture = tuple[AsyncClient, FastAPI]


QueryParamValue = str | list[str]


def valid_params(**overrides: QueryParamValue) -> dict[str, QueryParamValue]:
    params: dict[str, QueryParamValue] = {
        "start": "2024-01-01T10:00:00",
        "end": "2024-01-01T11:00:00",
        "station_id": "89064",
        "location": "UTC",
    }
    params.update(overrides)
    return params


def get_observations_with_fakes(
    weather_source: WeatherSource,
    *,
    single_flight: SingleFlight[list[Observation]] | None = None,
) -> GetObservations:
    return GetObservations(
        weather_source,
        FakeObservationRepository(),
        FakeUnitOfWork(),
        single_flight if single_flight is not None else SingleFlight[list[Observation]](),
    )


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with Database(TEST_SETTINGS.database_url) as db:
        async with db.session() as session:
            yield session


@pytest.fixture
async def api_client() -> AsyncGenerator[ApiClientFixture, None]:
    app = create_app(TEST_SETTINGS)
    app.dependency_overrides[get_observations_use_case] = lambda: get_observations_with_fakes(FakeWeatherSource([]))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client, app
    app.dependency_overrides.clear()
