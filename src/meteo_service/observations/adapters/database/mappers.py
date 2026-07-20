from datetime import UTC, datetime

from meteo_service.observations.adapters.database.orm_models import ObservationRow
from meteo_service.observations.domain.observation import Observation
from meteo_service.observations.domain.station import Station


def _ensure_utc(observed_at: datetime) -> datetime:
    if observed_at.tzinfo is None:
        return observed_at.replace(tzinfo=UTC)
    return observed_at.astimezone(UTC)


def to_domain(row: ObservationRow) -> Observation:
    return Observation(
        station=Station(id=row.station_id, name=row.station_name),
        observed_at=_ensure_utc(row.observed_at),
        temperature_c=row.temperature_c,
        pressure_hpa=row.pressure_hpa,
        speed_ms=row.speed_ms,
    )


def to_row(observation: Observation) -> ObservationRow:
    return ObservationRow(
        station_id=observation.station.id,
        observed_at=observation.observed_at,
        station_name=observation.station.name,
        temperature_c=observation.temperature_c,
        pressure_hpa=observation.pressure_hpa,
        speed_ms=observation.speed_ms,
    )


def to_row_dict(observation: Observation) -> dict[str, object]:
    row = to_row(observation)
    return {
        "station_id": row.station_id,
        "observed_at": row.observed_at,
        "station_name": row.station_name,
        "temperature_c": row.temperature_c,
        "pressure_hpa": row.pressure_hpa,
        "speed_ms": row.speed_ms,
    }
