from enum import StrEnum


class TimeAggregation(StrEnum):
    HOURLY = "hourly"
    DAILY = "daily"
    MONTHLY = "monthly"


class ObservationDataField(StrEnum):
    TEMPERATURE = "temperature"
    PRESSURE = "pressure"
    SPEED = "speed"
