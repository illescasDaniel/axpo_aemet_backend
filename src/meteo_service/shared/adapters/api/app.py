from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from meteo_service.observations.adapters.api.v1.router import router as observations_router
from meteo_service.shared.adapters.api.health_router import router as health_router
from meteo_service.shared.adapters.api.lifespan import build_lifespan
from meteo_service.shared.config import Settings


def create_app(settings: Settings) -> FastAPI:
    app = FastAPI(title="meteo-service", lifespan=build_lifespan(settings.database_url))
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_methods=["GET", "OPTIONS"],
            allow_headers=["*"],
        )
    app.include_router(health_router)
    app.include_router(observations_router, prefix="/api/v1")
    return app
