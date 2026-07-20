from meteo_service.observations.adapters.api.schemas import ObservationResponse, StationResponse
from meteo_service.observations.application.models.observation_view import ObservationView


def to_observation_response(view: ObservationView) -> ObservationResponse:
    return ObservationResponse(
        station=StationResponse(id=view.station.id, name=view.station.name),
        datetime=view.observed_at,
        temperature=view.temperature_c,
        pressure=view.pressure_hpa,
        speed=view.speed_ms,
    )
