from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from meteo_service.observations.adapters.api.v1.router import router as observations_router
from meteo_service.shared.adapters.api.health_router import router as health_router
from meteo_service.shared.adapters.api.lifespan import lifespan
from meteo_service.shared.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings if settings is not None else get_settings()
    app = FastAPI(title="meteo-service", lifespan=lifespan)
    if resolved.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=resolved.cors_origins,
            allow_methods=["GET", "OPTIONS"],
            allow_headers=["*"],
        )
    app.include_router(health_router)
    app.include_router(observations_router, prefix="/api/v1")
    return app
