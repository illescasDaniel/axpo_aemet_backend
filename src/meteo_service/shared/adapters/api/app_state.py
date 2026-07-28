from typing import cast

from fastapi import Request
from httpx2 import AsyncClient

from meteo_service.observations.domain.observation import Observation
from meteo_service.shared.database import Database
from meteo_service.shared.single_flight import SingleFlight


class AppState:
    db: Database
    http_client: AsyncClient
    single_flight: SingleFlight[list[Observation]]


def get_app_state(request: Request) -> AppState:
    return cast(AppState, request.app.state)
