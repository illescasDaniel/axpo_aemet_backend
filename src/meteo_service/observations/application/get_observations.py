# ruff: noqa: E501

import logging
from collections import defaultdict
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from meteo_service.observations.application.mappers import MADRID_TIME_ZONE, to_raw_views
from meteo_service.observations.application.models.enums import ObservationDataField, TimeAggregation
from meteo_service.observations.application.models.observation_view import ObservationView
from meteo_service.observations.application.ports.observation_repository import ObservationRepository
from meteo_service.observations.application.ports.weather_source import WeatherSource
from meteo_service.observations.domain.observation import Observation
from meteo_service.shared.single_flight import SingleFlight
from meteo_service.shared.unit_of_work import UnitOfWork
from meteo_service.shared.utils.stats import optional_mean


logger = logging.getLogger(__name__)


class GetObservations:
    def __init__(
        self,
        weather_source: WeatherSource,
        repository: ObservationRepository,
        uow: UnitOfWork,
        single_flight: SingleFlight[list[Observation]],
    ):
        self._weather_source = weather_source
        self._repository = repository
        self._uow = uow
        self._single_flight = single_flight

    async def execute(
        self,
        station_id: str,
        start: datetime,
        end: datetime,
        *,
        station_location: ZoneInfo,
        location: ZoneInfo,
        time_aggregation: TimeAggregation | None = None,
        data_fields: set[ObservationDataField] | None = None,
    ) -> list[ObservationView]:
        """
        Fetch observations for a station and time range.

        - ``station_location`` defines the station timezone for hourly/daily/monthly bucket boundaries.
        - ``location`` IANA timezone for interpreting naive ``start``/``end``.
        - ``time_aggregation`` ``None`` means raw 10-minute samples.
        - ``data_fields`` empty or ``None`` means all of temperature, pressure, speed.
        """
        fields = data_fields or set(ObservationDataField)
        start_utc = self._to_utc(start, location)
        end_utc = self._to_utc(end, location)

        observations = await self._load_observations(station_id, start_utc, end_utc)
        if time_aggregation is None:
            return to_raw_views(observations, fields)
        return self._to_aggregated_views(observations, fields, time_aggregation, station_location)

    async def _load_observations(self, station_id: str, start_utc: datetime, end_utc: datetime) -> list[Observation]:
        observations = await self._repository.get_range(station_id, start_utc, end_utc)
        if observations:
            logger.info("cache hit station_id=%s start=%s end=%s rows=%d", station_id, start_utc.isoformat(), end_utc.isoformat(), len(observations))  # noqa: E501 # fmt: skip
        else:
            logger.info("cache miss station_id=%s start=%s end=%s", station_id, start_utc.isoformat(), end_utc.isoformat())  # noqa: E501 # fmt: skip
            observations = await self._single_flight.do(
                (station_id, start_utc, end_utc),
                lambda: self._fetch_and_upsert(station_id, start_utc, end_utc),
            )
        observations.sort(key=lambda x: x.observed_at)
        return observations

    async def _fetch_and_upsert(self, station_id: str, start_utc: datetime, end_utc: datetime) -> list[Observation]:
        observations = await self._weather_source.fetch(station_id, start_utc, end_utc)
        logger.info("AEMET fetch station_id=%s start=%s end=%s rows=%d", station_id, start_utc.isoformat(), end_utc.isoformat(), len(observations))  # noqa: E501 # fmt: skip
        async with self._uow:
            await self._repository.upsert_many(observations)
        logger.info("cache upsert station_id=%s rows=%d", station_id, len(observations))
        return observations

    def _to_aggregated_views(
        self,
        observations: list[Observation],
        fields: set[ObservationDataField],
        time_aggregation: TimeAggregation,
        station_location: ZoneInfo,
    ) -> list[ObservationView]:
        grouped: defaultdict[datetime, list[Observation]] = defaultdict(list)
        for observation in observations:
            bucket = self._bucket_start_utc(observation.observed_at, time_aggregation, station_location)
            grouped[bucket].append(observation)

        return [
            ObservationView(
                station=bucket_obs[0].station,
                observed_at=bucket_start.astimezone(MADRID_TIME_ZONE),
                pressure_hpa=(
                    optional_mean(x.pressure_hpa for x in bucket_obs)
                    if ObservationDataField.PRESSURE in fields
                    else None
                ),
                speed_ms=(
                    optional_mean(x.speed_ms for x in bucket_obs) if ObservationDataField.SPEED in fields else None
                ),
                temperature_c=(
                    optional_mean(x.temperature_c for x in bucket_obs)
                    if ObservationDataField.TEMPERATURE in fields
                    else None
                ),
            )
            for bucket_start, bucket_obs in sorted(grouped.items())
        ]

    def _to_utc(self, dt: datetime, location: ZoneInfo) -> datetime:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=location)
        return dt.astimezone(UTC)

    def _bucket_start_utc(
        self,
        observed_at: datetime,
        time_aggregation: TimeAggregation,
        station_location: ZoneInfo,
    ) -> datetime:
        # observed_at must be timezone-aware (AEMET fhora ends with Z → UTC).
        # Naive datetimes would make astimezone() use the system local zone — messy.
        local_dt = observed_at.astimezone(station_location)
        match time_aggregation:
            case TimeAggregation.HOURLY:
                local_bucket_start = local_dt.replace(minute=0, second=0, microsecond=0)
            case TimeAggregation.DAILY:
                local_bucket_start = local_dt.replace(hour=0, minute=0, second=0, microsecond=0)
            case TimeAggregation.MONTHLY:
                local_bucket_start = local_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return local_bucket_start.astimezone(UTC)
