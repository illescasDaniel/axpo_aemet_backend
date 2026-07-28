from collections.abc import AsyncGenerator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import cast

import httpx2
from fastapi import FastAPI

from meteo_service.observations.domain.observation import Observation
from meteo_service.shared.adapters.api.app_state import AppState
from meteo_service.shared.database import Database
from meteo_service.shared.logging import configure_logging
from meteo_service.shared.single_flight import SingleFlight


def build_lifespan(database_url: str) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        configure_logging()
        async with Database(database_url) as db:
            state = cast(AppState, app.state)
            state.db = db
            state.single_flight = SingleFlight[list[Observation]]()

            async with httpx2.AsyncClient(timeout=60.0) as client:
                state.http_client = client
                yield

    return lifespan
