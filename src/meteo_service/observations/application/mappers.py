from zoneinfo import ZoneInfo

from meteo_service.observations.application.models.enums import ObservationDataField
from meteo_service.observations.application.models.observation_view import ObservationView
from meteo_service.observations.domain.observation import Observation


MADRID_TIME_ZONE = ZoneInfo("Europe/Madrid")


def to_raw_views(observations: list[Observation], fields: set[ObservationDataField]) -> list[ObservationView]:
    return [
        ObservationView(
            station=x.station,
            observed_at=x.observed_at.astimezone(MADRID_TIME_ZONE),
            pressure_hpa=x.pressure_hpa if ObservationDataField.PRESSURE in fields else None,
            speed_ms=x.speed_ms if ObservationDataField.SPEED in fields else None,
            temperature_c=x.temperature_c if ObservationDataField.TEMPERATURE in fields else None,
        )
        for x in observations
    ]
