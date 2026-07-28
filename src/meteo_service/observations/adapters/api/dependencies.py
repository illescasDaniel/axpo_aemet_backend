from typing import Annotated, AsyncGenerator

from fastapi import Depends, Request
from httpx2 import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from meteo_service.observations.adapters.aemet.aemet_client import AemetClient
from meteo_service.observations.adapters.database.sqlalchemy_observation_repository import (
    SqlAlchemyObservationRepository,
)
from meteo_service.observations.application.get_observations import GetObservations
from meteo_service.observations.domain.observation import Observation
from meteo_service.shared.adapters.api.app_state import get_app_state
from meteo_service.shared.adapters.sqlalchemy_unit_of_work import SqlAlchemyUnitOfWork
from meteo_service.shared.config import Settings, get_settings
from meteo_service.shared.single_flight import SingleFlight


def get_http_client(request: Request) -> AsyncClient:
    return get_app_state(request).http_client


def get_weather_source(
    client: Annotated[AsyncClient, Depends(get_http_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AemetClient:
    return AemetClient(client, settings.aemet_api_key)


async def get_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    async with get_app_state(request).db.session() as session:
        yield session


def get_observation_repository(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SqlAlchemyObservationRepository:
    return SqlAlchemyObservationRepository(session)


def get_unit_of_work(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SqlAlchemyUnitOfWork:
    return SqlAlchemyUnitOfWork(session)


def get_single_flight(request: Request) -> SingleFlight[list[Observation]]:
    return get_app_state(request).single_flight


def get_observations_use_case(
    weather_source: Annotated[AemetClient, Depends(get_weather_source)],
    repository: Annotated[SqlAlchemyObservationRepository, Depends(get_observation_repository)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_unit_of_work)],
    single_flight: Annotated[SingleFlight[list[Observation]], Depends(get_single_flight)],
) -> GetObservations:
    return GetObservations(weather_source, repository, uow, single_flight)
