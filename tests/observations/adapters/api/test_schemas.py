import pytest
from pydantic import ValidationError

from meteo_service.observations.adapters.api.schemas import GetObservationsQuery
from meteo_service.observations.application.models.enums import ObservationDataField, TimeAggregation


def test_given_valid_query_when_parsing_then_accepts_set_data_fields():
    # given/when
    query = GetObservationsQuery.model_validate(
        {
            "start": "2024-01-01T00:00:00",
            "end": "2024-01-01T01:00:00",
            "station_id": "89064",
            "location": "Europe/Madrid",
            "time_aggregation": TimeAggregation.HOURLY,
            "data_fields": {ObservationDataField.TEMPERATURE, ObservationDataField.SPEED},
        }
    )

    # then
    assert query.station_id == "89064"
    assert query.data_fields == {ObservationDataField.TEMPERATURE, ObservationDataField.SPEED}


def test_given_unknown_station_id_when_parsing_then_raises_validation_error():
    # given/when/then
    with pytest.raises(ValidationError):
        GetObservationsQuery.model_validate(
            {
                "start": "2024-01-01T00:00:00",
                "end": "2024-01-01T01:00:00",
                "station_id": "99999",
                "location": "UTC",
            }
        )


def test_given_omitted_location_when_parsing_then_defaults_to_europe_madrid():
    # given/when
    query = GetObservationsQuery.model_validate(
        {
            "start": "2024-01-01T00:00:00",
            "end": "2024-01-01T01:00:00",
            "station_id": "89064",
        }
    )

    # then
    assert query.location.key == "Europe/Madrid"


def test_given_offset_location_when_parsing_then_raises_validation_error():
    # given/when/then
    with pytest.raises(ValidationError):
        GetObservationsQuery.model_validate(
            {
                "start": "2024-01-01T00:00:00",
                "end": "2024-01-01T01:00:00",
                "station_id": "89064",
                "location": "+02:00",
            }
        )
