from meteo_service.observations.adapters.aemet.schemas import AemetObservation
from meteo_service.observations.domain.observation import Observation
from meteo_service.observations.domain.station import Station


def to_observation(row: AemetObservation, station_id: str) -> Observation:
    return Observation(
        station=Station(id=station_id, name=row.station_name),
        observed_at=row.observed_at,
        temperature_c=row.temperature_c,
        pressure_hpa=row.pressure_hpa,
        speed_ms=row.speed_ms,
    )


def to_observations(rows: list[AemetObservation], station_id: str) -> list[Observation]:
    return [to_observation(row, station_id) for row in rows]
