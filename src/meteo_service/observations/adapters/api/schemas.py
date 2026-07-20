from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from meteo_service.observations.adapters.aemet.station_timezones import station_location
from meteo_service.observations.application.models.enums import ObservationDataField, TimeAggregation


# AEMET Antartida product stations only (Juan Carlos I, Gabriel de Castilla).
AntarcticStationId = Literal["89064", "89070"]


class GetObservationsQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_default=True)

    start: datetime = Field(description="AAAA-MM-DDTHH:MM:SS")
    end: datetime = Field(description="AAAA-MM-DDTHH:MM:SS")
    station_id: AntarcticStationId = Field(description="Antarctic AEMET station id (89064 or 89070)")
    location: ZoneInfo = Field(  # pyright: ignore[reportAssignmentType]
        default="Europe/Madrid",
        description="IANA timezone for naive start/end, e.g. Europe/Madrid (default)",
    )
    time_aggregation: TimeAggregation | None = None
    data_fields: set[ObservationDataField] | None = None

    @field_validator("start", "end", mode="before")
    @classmethod
    def parse_naive_datetime(cls, value: object) -> datetime:
        if not isinstance(value, str):
            raise TypeError("start/end must be a string")
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")

    @field_validator("location", mode="before")
    @classmethod
    def parse_location(cls, value: object) -> ZoneInfo:
        if not isinstance(value, str):
            raise TypeError("location must be a string")
        try:
            return ZoneInfo(value)
        except Exception as exc:
            raise ValueError(f"invalid IANA timezone: {value}") from exc

    @model_validator(mode="after")
    def validate_range(self) -> "GetObservationsQuery":
        if self.start > self.end:
            raise ValueError("start must be before or equal to end")
        return self

    def resolved_station_location(self) -> ZoneInfo:
        return station_location(self.station_id)


class StationResponse(BaseModel):
    id: str
    name: str


class ObservationResponse(BaseModel):
    station: StationResponse
    datetime: datetime
    temperature: float | None = None
    pressure: float | None = None
    speed: float | None = None
