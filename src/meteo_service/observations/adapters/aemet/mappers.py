from meteo_service.observations.adapters.aemet.schemas import AemetConvencionalObservation, AemetObservation
from meteo_service.observations.domain.observation import Observation
from meteo_service.observations.domain.station import Station


def to_observation(row: AemetObservation | AemetConvencionalObservation, station_id: str) -> Observation:
    return Observation(
        station=Station(id=station_id, name=row.station_name),
        observed_at=row.observed_at,
        temperature_c=row.temperature_c,
        pressure_hpa=row.pressure_hpa,
        speed_ms=row.speed_ms,
    )


def to_observations(
    rows: list[AemetObservation] | list[AemetConvencionalObservation],
    station_id: str,
) -> list[Observation]:
    return [to_observation(row, station_id) for row in rows]
