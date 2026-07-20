from contextlib import asynccontextmanager

import httpx2
from fastapi import FastAPI

from meteo_service.observations.domain.observation import Observation
from meteo_service.shared.config import get_settings
from meteo_service.shared.database import Database
from meteo_service.shared.logging import configure_logging
from meteo_service.shared.single_flight import SingleFlight


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    async with Database(get_settings().database_url) as db:
        app.state.db = db
        app.state.single_flight = SingleFlight[list[Observation]]()

        async with httpx2.AsyncClient(timeout=60.0) as client:
            app.state.http_client = client
            yield
