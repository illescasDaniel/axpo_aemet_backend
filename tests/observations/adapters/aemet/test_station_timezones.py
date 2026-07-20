from zoneinfo import ZoneInfo

from meteo_service.observations.adapters.aemet.station_timezones import station_location


def test_given_antarctic_station_when_resolving_location_then_returns_utc():
    assert station_location("89064") == ZoneInfo("UTC")
    assert station_location("89070") == ZoneInfo("UTC")


def test_given_canary_station_when_resolving_location_then_returns_atlantic_canary():
    assert station_location("C449C") == ZoneInfo("Atlantic/Canary")


def test_given_peninsular_station_when_resolving_location_then_returns_europe_madrid():
    assert station_location("3195") == ZoneInfo("Europe/Madrid")
