from datetime import UTC, datetime

import pytest
from tests.conftest import (
    DEFAULT_ROWS,
    OBSERVATIONS_PATH,
    STATION_GDC,
    STATION_JCI,
    ApiClientFixture,
    get_observations_with_fakes,
    valid_params,
)
from tests.fakes.weather_source import FailingWeatherSource, FakeWeatherSource

from meteo_service.observations.adapters.api.dependencies import get_observations_use_case
from meteo_service.observations.domain.observation import Observation


pytestmark = pytest.mark.integration


async def test_given_valid_query_when_getting_observations_then_returns_mapped_json(api_client: ApiClientFixture):
    # given
    client, app = api_client
    app.dependency_overrides[get_observations_use_case] = lambda: get_observations_with_fakes(
        FakeWeatherSource(DEFAULT_ROWS)
    )

    # when
    response = await client.get(
        OBSERVATIONS_PATH,
        params=valid_params(data_fields=["temperature", "speed"]),
    )

    # then
    assert response.status_code == 200
    assert response.json() == [
        {
            "station": {"id": "89064", "name": "Juan Carlos I"},
            "datetime": "2024-01-01T11:10:00+01:00",
            "temperature": -4.0,
            "pressure": None,
            "speed": 5.0,
        }
    ]


async def test_given_valid_query_without_data_fields_when_getting_observations_then_returns_all_fields(
    api_client: ApiClientFixture,
):
    # given
    client, app = api_client
    app.dependency_overrides[get_observations_use_case] = lambda: get_observations_with_fakes(
        FakeWeatherSource(DEFAULT_ROWS)
    )

    # when
    response = await client.get(OBSERVATIONS_PATH, params=valid_params())

    # then
    assert response.status_code == 200
    row = response.json()[0]
    assert row["temperature"] == -4.0
    assert row["pressure"] == 990.0
    assert row["speed"] == 5.0


async def test_given_hourly_aggregation_when_getting_observations_then_returns_bucketed_rows(
    api_client: ApiClientFixture,
):
    # given
    client, app = api_client
    rows = [
        Observation(
            station=STATION_JCI,
            observed_at=datetime(2024, 1, 1, 10, 10, 0, tzinfo=UTC),
            temperature_c=0.0,
            pressure_hpa=1000.0,
            speed_ms=2.0,
        ),
        Observation(
            station=STATION_JCI,
            observed_at=datetime(2024, 1, 1, 10, 50, 0, tzinfo=UTC),
            temperature_c=4.0,
            pressure_hpa=1008.0,
            speed_ms=6.0,
        ),
    ]
    app.dependency_overrides[get_observations_use_case] = lambda: get_observations_with_fakes(FakeWeatherSource(rows))

    # when
    response = await client.get(
        OBSERVATIONS_PATH,
        params=valid_params(time_aggregation="hourly"),
    )

    # then
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["temperature"] == 2.0
    assert data[0]["pressure"] == 1004.0
    assert data[0]["speed"] == 4.0


async def test_given_daily_aggregation_when_getting_observations_then_returns_single_bucket(
    api_client: ApiClientFixture,
):
    # given
    client, app = api_client
    rows = [
        Observation(
            station=STATION_JCI,
            observed_at=datetime(2024, 1, 1, 10, 10, 0, tzinfo=UTC),
            temperature_c=0.0,
            pressure_hpa=1000.0,
            speed_ms=2.0,
        ),
        Observation(
            station=STATION_JCI,
            observed_at=datetime(2024, 1, 1, 22, 10, 0, tzinfo=UTC),
            temperature_c=4.0,
            pressure_hpa=1008.0,
            speed_ms=6.0,
        ),
    ]
    app.dependency_overrides[get_observations_use_case] = lambda: get_observations_with_fakes(FakeWeatherSource(rows))

    # when
    response = await client.get(
        OBSERVATIONS_PATH,
        params=valid_params(
            start="2024-01-01T00:00:00",
            end="2024-01-01T23:59:59",
            time_aggregation="daily",
        ),
    )

    # then
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["temperature"] == 2.0


async def test_given_monthly_aggregation_when_getting_observations_then_returns_one_bucket_per_month(
    api_client: ApiClientFixture,
):
    # given
    client, app = api_client
    rows = [
        Observation(
            station=STATION_JCI,
            observed_at=datetime(2024, 1, 10, 10, 0, 0, tzinfo=UTC),
            temperature_c=0.0,
            pressure_hpa=1000.0,
            speed_ms=2.0,
        ),
        Observation(
            station=STATION_JCI,
            observed_at=datetime(2024, 1, 25, 10, 0, 0, tzinfo=UTC),
            temperature_c=2.0,
            pressure_hpa=1004.0,
            speed_ms=4.0,
        ),
        Observation(
            station=STATION_JCI,
            observed_at=datetime(2024, 2, 5, 10, 0, 0, tzinfo=UTC),
            temperature_c=6.0,
            pressure_hpa=1012.0,
            speed_ms=8.0,
        ),
    ]
    app.dependency_overrides[get_observations_use_case] = lambda: get_observations_with_fakes(FakeWeatherSource(rows))

    # when
    response = await client.get(
        OBSERVATIONS_PATH,
        params=valid_params(
            start="2024-01-01T00:00:00",
            end="2024-02-28T23:59:59",
            time_aggregation="monthly",
        ),
    )

    # then
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["datetime"] == "2024-01-01T01:00:00+01:00"
    assert data[0]["temperature"] == 1.0
    assert data[1]["datetime"] == "2024-02-01T01:00:00+01:00"
    assert data[1]["temperature"] == 6.0


async def test_given_winter_observation_when_getting_observations_then_returns_cet_offset(api_client: ApiClientFixture):
    # given
    client, app = api_client
    rows = [
        Observation(
            station=STATION_JCI,
            observed_at=datetime(2024, 1, 15, 10, 10, 0, tzinfo=UTC),
            temperature_c=-3.0,
            pressure_hpa=990.0,
            speed_ms=5.0,
        )
    ]
    app.dependency_overrides[get_observations_use_case] = lambda: get_observations_with_fakes(FakeWeatherSource(rows))

    # when
    response = await client.get(
        OBSERVATIONS_PATH,
        params=valid_params(
            start="2024-01-15T10:00:00",
            end="2024-01-15T11:00:00",
        ),
    )

    # then
    assert response.status_code == 200
    assert response.json()[0]["datetime"] == "2024-01-15T11:10:00+01:00"


async def test_given_summer_observation_when_getting_observations_then_returns_cest_offset(
    api_client: ApiClientFixture,
):
    # given
    client, app = api_client
    rows = [
        Observation(
            station=STATION_JCI,
            observed_at=datetime(2024, 7, 15, 10, 10, 0, tzinfo=UTC),
            temperature_c=1.0,
            pressure_hpa=995.0,
            speed_ms=7.0,
        )
    ]
    app.dependency_overrides[get_observations_use_case] = lambda: get_observations_with_fakes(FakeWeatherSource(rows))

    # when
    response = await client.get(
        OBSERVATIONS_PATH,
        params=valid_params(
            start="2024-07-15T10:00:00",
            end="2024-07-15T11:00:00",
        ),
    )

    # then
    assert response.status_code == 200
    assert response.json()[0]["datetime"] == "2024-07-15T12:10:00+02:00"


async def test_given_gabriel_station_when_getting_observations_then_returns_data(api_client: ApiClientFixture):
    # given
    client, app = api_client
    rows = [
        Observation(
            station=STATION_GDC,
            observed_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC),
            temperature_c=-8.0,
            pressure_hpa=985.0,
            speed_ms=11.0,
        )
    ]
    app.dependency_overrides[get_observations_use_case] = lambda: get_observations_with_fakes(FakeWeatherSource(rows))

    # when
    response = await client.get(
        OBSERVATIONS_PATH,
        params=valid_params(
            station_id="89070",
            start="2024-01-01T11:00:00",
            end="2024-01-01T13:00:00",
        ),
    )

    # then
    assert response.status_code == 200
    assert response.json()[0]["station"] == {"id": "89070", "name": "Gabriel de Castilla"}


async def test_given_no_matching_rows_when_getting_observations_then_returns_empty_list(api_client: ApiClientFixture):
    # given
    client, app = api_client
    app.dependency_overrides[get_observations_use_case] = lambda: get_observations_with_fakes(FakeWeatherSource([]))

    # when
    response = await client.get(OBSERVATIONS_PATH, params=valid_params())

    # then
    assert response.status_code == 200
    assert response.json() == []


async def test_given_aemet_error_when_getting_observations_then_returns_502(api_client: ApiClientFixture):
    # given
    client, app = api_client
    app.dependency_overrides[get_observations_use_case] = lambda: get_observations_with_fakes(FailingWeatherSource())

    # when
    response = await client.get(OBSERVATIONS_PATH, params=valid_params())

    # then
    assert response.status_code == 502
    assert "AEMET error 401" in response.json()["detail"]


async def test_given_unknown_station_id_when_getting_observations_then_returns_422(
    api_client: ApiClientFixture,
):
    # given
    client, _app = api_client

    # when
    response = await client.get(
        OBSERVATIONS_PATH,
        params=valid_params(station_id="99999"),
    )

    # then
    assert response.status_code == 422


async def test_given_empty_station_id_when_getting_observations_then_returns_422(api_client: ApiClientFixture):
    # given
    client, _app = api_client

    # when
    response = await client.get(
        OBSERVATIONS_PATH,
        params=valid_params(station_id=""),
    )

    # then
    assert response.status_code == 422


async def test_given_omitted_location_when_getting_observations_then_defaults_to_europe_madrid(
    api_client: ApiClientFixture,
):
    # given — DEFAULT_ROWS sample is 10:10 UTC (= 11:10 Europe/Madrid in January)
    client, app = api_client
    app.dependency_overrides[get_observations_use_case] = lambda: get_observations_with_fakes(
        FakeWeatherSource(DEFAULT_ROWS)
    )
    params = {
        "start": "2024-01-01T11:00:00",
        "end": "2024-01-01T12:00:00",
        "station_id": "89064",
    }

    # when
    response = await client.get(OBSERVATIONS_PATH, params=params)

    # then
    assert response.status_code == 200
    assert len(response.json()) == 1


async def test_given_offset_location_when_getting_observations_then_returns_422(api_client: ApiClientFixture):
    # given
    client, _app = api_client

    # when
    response = await client.get(
        OBSERVATIONS_PATH,
        params=valid_params(location="+02:00"),
    )

    # then
    assert response.status_code == 422


async def test_given_invalid_iana_location_when_getting_observations_then_returns_422(api_client: ApiClientFixture):
    # given
    client, _app = api_client

    # when
    response = await client.get(
        OBSERVATIONS_PATH,
        params=valid_params(location="Not/A/Timezone"),
    )

    # then
    assert response.status_code == 422


async def test_given_start_after_end_when_getting_observations_then_returns_422(api_client: ApiClientFixture):
    # given
    client, _app = api_client

    # when
    response = await client.get(
        OBSERVATIONS_PATH,
        params=valid_params(start="2024-01-02T00:00:00", end="2024-01-01T00:00:00"),
    )

    # then
    assert response.status_code == 422


async def test_given_missing_required_param_when_getting_observations_then_returns_422(api_client: ApiClientFixture):
    # given
    client, _app = api_client

    # when — station_id is required; location has a default
    response = await client.get(
        OBSERVATIONS_PATH,
        params={
            "start": "2024-01-01T10:00:00",
            "end": "2024-01-01T11:00:00",
            "location": "UTC",
        },
    )

    # then
    assert response.status_code == 422


async def test_given_invalid_datetime_format_when_getting_observations_then_returns_422(api_client: ApiClientFixture):
    # given
    client, _app = api_client

    # when
    response = await client.get(
        OBSERVATIONS_PATH,
        params=valid_params(start="2024-01-01"),
    )

    # then
    assert response.status_code == 422


async def test_given_invalid_time_aggregation_when_getting_observations_then_returns_422(api_client: ApiClientFixture):
    # given
    client, _app = api_client

    # when
    response = await client.get(
        OBSERVATIONS_PATH,
        params=valid_params(time_aggregation="weekly"),
    )

    # then
    assert response.status_code == 422


async def test_given_invalid_data_field_when_getting_observations_then_returns_422(api_client: ApiClientFixture):
    # given
    client, _app = api_client

    # when
    response = await client.get(
        OBSERVATIONS_PATH,
        params=valid_params(data_fields=["humidity"]),
    )

    # then
    assert response.status_code == 422
