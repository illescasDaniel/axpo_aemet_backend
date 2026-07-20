import asyncio
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest
from tests.conftest import STATION_JCI, get_observations_with_fakes
from tests.fakes.observation_repository import FakeObservationRepository
from tests.fakes.unit_of_work import FakeUnitOfWork
from tests.fakes.weather_source import FakeWeatherSource

from meteo_service.observations.application.get_observations import GetObservations
from meteo_service.observations.application.models.enums import ObservationDataField, TimeAggregation
from meteo_service.observations.domain.observation import Observation
from meteo_service.shared.single_flight import SingleFlight


pytestmark = pytest.mark.unit

_STATION_ID = "89064"
_STATION_LOCATION = ZoneInfo("UTC")
_INPUT_LOCATION = ZoneInfo("UTC")
_KALININGRAD = ZoneInfo("Europe/Kaliningrad")  # fixed UTC+2, useful for bucket-boundary tests


async def test_given_naive_input_with_location_when_execute_then_interprets_in_that_zone():
    # given
    rows = [
        Observation(
            station=STATION_JCI,
            observed_at=datetime(2024, 1, 1, 10, 10, 0, tzinfo=UTC),
            temperature_c=-4.0,
            pressure_hpa=990.0,
            speed_ms=5.0,
        )
    ]
    use_case = get_observations_with_fakes(FakeWeatherSource(rows=rows))

    # when — naive 10:00–11:00 in UTC covers the sample
    result = await use_case.execute(
        station_id=_STATION_ID,
        start=datetime(2024, 1, 1, 10, 0, 0),
        end=datetime(2024, 1, 1, 11, 0, 0),
        station_location=_STATION_LOCATION,
        location=_INPUT_LOCATION,
    )

    # then
    assert len(result) == 1
    assert result[0].temperature_c == -4.0


async def test_given_no_aggregation_and_selected_fields_when_execute_then_projects_requested_fields():
    # given
    rows = [
        Observation(
            station=STATION_JCI,
            observed_at=datetime(2024, 1, 1, 10, 10, 0, tzinfo=UTC),
            temperature_c=-4.0,
            pressure_hpa=990.0,
            speed_ms=5.0,
        )
    ]
    use_case = get_observations_with_fakes(FakeWeatherSource(rows=rows))

    # when
    result = await use_case.execute(
        station_id=_STATION_ID,
        start=datetime(2024, 1, 1, 10, 0, 0),
        end=datetime(2024, 1, 1, 11, 0, 0),
        station_location=_STATION_LOCATION,
        location=_INPUT_LOCATION,
        data_fields={ObservationDataField.TEMPERATURE, ObservationDataField.SPEED},
    )

    # then
    assert len(result) == 1
    assert result[0].station.name == "Juan Carlos I"
    assert result[0].temperature_c == -4.0
    assert result[0].speed_ms == 5.0
    assert result[0].pressure_hpa is None
    assert result[0].observed_at == datetime(2024, 1, 1, 11, 10, 0, tzinfo=ZoneInfo("Europe/Madrid"))


async def test_given_hourly_aggregation_with_station_timezone_when_execute_then_groups_by_station_hour_start():
    # given
    rows = [
        Observation(
            station=STATION_JCI,
            observed_at=datetime(2024, 1, 1, 22, 50, 0, tzinfo=UTC),
            temperature_c=0.0,
            pressure_hpa=1000.0,
            speed_ms=2.0,
        ),
        Observation(
            station=STATION_JCI,
            observed_at=datetime(2024, 1, 1, 23, 30, 0, tzinfo=UTC),
            temperature_c=4.0,
            pressure_hpa=1008.0,
            speed_ms=6.0,
        ),
    ]
    use_case = get_observations_with_fakes(FakeWeatherSource(rows=rows))

    # when
    result = await use_case.execute(
        station_id=_STATION_ID,
        start=datetime(2024, 1, 1, 22, 0, 0),
        end=datetime(2024, 1, 2, 0, 0, 0),
        station_location=_KALININGRAD,
        location=_INPUT_LOCATION,
        time_aggregation=TimeAggregation.HOURLY,
    )

    # then
    assert len(result) == 2
    assert result[0].temperature_c == 0.0
    assert result[1].temperature_c == 4.0
    assert result[0].observed_at == datetime(2024, 1, 1, 23, 0, 0, tzinfo=ZoneInfo("Europe/Madrid"))
    assert result[1].observed_at == datetime(2024, 1, 2, 0, 0, 0, tzinfo=ZoneInfo("Europe/Madrid"))


async def test_given_daily_aggregation_with_station_timezone_when_execute_then_groups_by_station_day_start():
    # given
    rows = [
        Observation(
            station=STATION_JCI,
            observed_at=datetime(2024, 1, 1, 23, 30, 0, tzinfo=UTC),
            temperature_c=0.0,
            pressure_hpa=1000.0,
            speed_ms=2.0,
        ),
        Observation(
            station=STATION_JCI,
            observed_at=datetime(2024, 1, 2, 0, 10, 0, tzinfo=UTC),
            temperature_c=2.0,
            pressure_hpa=1004.0,
            speed_ms=4.0,
        ),
    ]
    use_case = get_observations_with_fakes(FakeWeatherSource(rows=rows))

    # when
    result = await use_case.execute(
        station_id=_STATION_ID,
        start=datetime(2024, 1, 1, 23, 0, 0),
        end=datetime(2024, 1, 2, 1, 0, 0),
        station_location=_KALININGRAD,
        location=_INPUT_LOCATION,
        time_aggregation=TimeAggregation.DAILY,
    )

    # then
    assert len(result) == 1
    assert result[0].temperature_c == 1.0
    assert result[0].pressure_hpa == 1002.0
    assert result[0].speed_ms == 3.0
    assert result[0].observed_at == datetime(2024, 1, 1, 23, 0, 0, tzinfo=ZoneInfo("Europe/Madrid"))


async def test_given_cache_miss_when_execute_then_commits_unit_of_work():
    # given
    rows = [
        Observation(
            station=STATION_JCI,
            observed_at=datetime(2024, 1, 1, 10, 10, 0, tzinfo=UTC),
            temperature_c=-4.0,
            pressure_hpa=990.0,
            speed_ms=5.0,
        )
    ]
    uow = FakeUnitOfWork()
    use_case = GetObservations(
        FakeWeatherSource(rows=rows),
        FakeObservationRepository(),
        uow,
        SingleFlight[list[Observation]](),
    )

    # when
    await use_case.execute(
        station_id=_STATION_ID,
        start=datetime(2024, 1, 1, 10, 0, 0),
        end=datetime(2024, 1, 1, 11, 0, 0),
        station_location=_STATION_LOCATION,
        location=_INPUT_LOCATION,
    )

    # then
    assert uow.committed
    assert not uow.rolled_back


async def test_given_cache_hit_when_execute_then_logs_hit(caplog: pytest.LogCaptureFixture):
    # given
    rows = [
        Observation(
            station=STATION_JCI,
            observed_at=datetime(2024, 1, 1, 10, 10, 0, tzinfo=UTC),
            temperature_c=-4.0,
            pressure_hpa=990.0,
            speed_ms=5.0,
        )
    ]
    use_case = GetObservations(
        FakeWeatherSource(rows=[]),
        FakeObservationRepository(rows=rows),
        FakeUnitOfWork(),
        SingleFlight[list[Observation]](),
    )

    # when
    with caplog.at_level("INFO"):
        await use_case.execute(
            station_id=_STATION_ID,
            start=datetime(2024, 1, 1, 10, 0, 0),
            end=datetime(2024, 1, 1, 11, 0, 0),
            station_location=_STATION_LOCATION,
            location=_INPUT_LOCATION,
        )

    # then
    assert any("cache hit" in record.message for record in caplog.records)
    assert not any("cache miss" in record.message for record in caplog.records)


async def test_given_concurrent_cache_misses_same_range_when_execute_then_fetches_once():
    # given
    rows = [
        Observation(
            station=STATION_JCI,
            observed_at=datetime(2024, 1, 1, 10, 10, 0, tzinfo=UTC),
            temperature_c=-4.0,
            pressure_hpa=990.0,
            speed_ms=5.0,
        )
    ]
    weather_source = FakeWeatherSource(rows=rows, delay_seconds=0.05)
    single_flight = SingleFlight[list[Observation]]()
    use_case_a = get_observations_with_fakes(weather_source, single_flight=single_flight)
    use_case_b = get_observations_with_fakes(weather_source, single_flight=single_flight)
    start = datetime(2024, 1, 1, 10, 0, 0)
    end = datetime(2024, 1, 1, 11, 0, 0)

    # when
    result_a, result_b = await asyncio.gather(
        use_case_a.execute(
            station_id=_STATION_ID,
            start=start,
            end=end,
            station_location=_STATION_LOCATION,
            location=_INPUT_LOCATION,
        ),
        use_case_b.execute(
            station_id=_STATION_ID,
            start=start,
            end=end,
            station_location=_STATION_LOCATION,
            location=_INPUT_LOCATION,
        ),
    )

    # then
    assert weather_source.fetch_count == 1
    assert len(result_a) == 1
    assert len(result_b) == 1


async def test_given_concurrent_cache_misses_different_ranges_when_execute_then_fetches_per_key():
    # given
    rows = [
        Observation(
            station=STATION_JCI,
            observed_at=datetime(2024, 1, 1, 10, 10, 0, tzinfo=UTC),
            temperature_c=-4.0,
            pressure_hpa=990.0,
            speed_ms=5.0,
        ),
        Observation(
            station=STATION_JCI,
            observed_at=datetime(2024, 1, 1, 12, 10, 0, tzinfo=UTC),
            temperature_c=-3.0,
            pressure_hpa=991.0,
            speed_ms=4.0,
        ),
    ]
    weather_source = FakeWeatherSource(rows=rows, delay_seconds=0.05)
    single_flight = SingleFlight[list[Observation]]()
    use_case_a = get_observations_with_fakes(weather_source, single_flight=single_flight)
    use_case_b = get_observations_with_fakes(weather_source, single_flight=single_flight)

    # when
    await asyncio.gather(
        use_case_a.execute(
            station_id=_STATION_ID,
            start=datetime(2024, 1, 1, 10, 0, 0),
            end=datetime(2024, 1, 1, 11, 0, 0),
            station_location=_STATION_LOCATION,
            location=_INPUT_LOCATION,
        ),
        use_case_b.execute(
            station_id=_STATION_ID,
            start=datetime(2024, 1, 1, 12, 0, 0),
            end=datetime(2024, 1, 1, 13, 0, 0),
            station_location=_STATION_LOCATION,
            location=_INPUT_LOCATION,
        ),
    )

    # then
    assert weather_source.fetch_count == 2
