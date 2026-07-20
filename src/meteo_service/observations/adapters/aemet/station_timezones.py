from zoneinfo import ZoneInfo


_UTC = ZoneInfo("UTC")
_ATLANTIC_CANARY = ZoneInfo("Atlantic/Canary")
_EUROPE_MADRID = ZoneInfo("Europe/Madrid")

# Known Antarctic stations on AEMET Antartida product (Juan Carlos I, Gabriel de Castilla).
_ANTARCTIC_STATIONS = frozenset({"89064", "89070"})

# Curated Canary Islands AEMET station ids (idema). Not exhaustive.
_CANARY_STATIONS = frozenset(
    {
        "C447A",  # Tenerife Norte / Los Rodeos
        "C449C",  # Tenerife Sur / Reina Sofía
        "C029O",  # Gran Canaria / Aeropuerto
        "C139E",  # Lanzarote / Aeropuerto
        "C929I",  # Fuerteventura / Aeropuerto
        "C659T",  # La Palma / Aeropuerto
    }
)


def station_location(station_id: str) -> ZoneInfo:
    """Timezone used for hourly/daily/monthly aggregation bucket boundaries."""
    if station_id in _ANTARCTIC_STATIONS:
        return _UTC
    if station_id in _CANARY_STATIONS:
        return _ATLANTIC_CANARY
    return _EUROPE_MADRID
