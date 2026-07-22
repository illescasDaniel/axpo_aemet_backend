# Domain and application layer

## Domain entities

Frozen **dataclasses**<sup>12</sup> with `slots=True` — immutable value objects.

```python
@dataclass(frozen=True, slots=True)
class Station:
    id: str
    name: str


@dataclass(frozen=True, slots=True)
class Observation:
    station: Station
    observed_at: datetime
    pressure_hpa: float | None
    speed_ms: float | None
    temperature_c: float | None
```

Sources: `observations/domain/station.py`, `observation.py`.

Domain stays free of FastAPI / httpx / SQLAlchemy types.

## Application view vs domain

- **Observation** — domain entity (internal names: `temperature_c`, `pressure_hpa`, `speed_ms`).
- **ObservationView** — application **DTO**<sup>15</sup> for the use-case return path (`observed_at` documented as Europe/Madrid with offset).
- **ObservationResponse** — API JSON shape (`temperature`, `pressure`, `speed`, nested `station`).

Thin mappers at each boundary keep layers decoupled.

## Enums

- `TimeAggregation`: `hourly` | `daily` | `monthly`
- `ObservationDataField`: `temperature` | `pressure` | `speed`

## Use case: `GetObservations`

Constructor injection: `WeatherSource`, `ObservationRepository`, `UnitOfWork`<sup>40</sup>, `SingleFlight`<sup>36</sup>.

```python
class GetObservations:
    def __init__(
        self,
        weather_source: WeatherSource,
        repository: ObservationRepository,
        uow: UnitOfWork,
        single_flight: SingleFlight[list[Observation]],
    ):
        ...

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
        fields = data_fields or set(ObservationDataField)
        start_utc = self._to_utc(start, location)
        end_utc = self._to_utc(end, location)

        observations = await self._load_observations(station_id, start_utc, end_utc)
        if time_aggregation is None:
            return to_raw_views(observations, fields)
        return self._to_aggregated_views(observations, fields, time_aggregation, station_location)
```

Source: `observations/application/get_observations.py`.

### Cache load path

```python
async def _load_observations(...):
    observations = await self._repository.get_range(station_id, start_utc, end_utc)
    if observations:
        # cache hit
        ...
    else:
        # cache miss → coalesce concurrent fetches
        observations = await self._single_flight.do(
            (station_id, start_utc, end_utc),
            lambda: self._fetch_and_upsert(station_id, start_utc, end_utc),
        )
```

`_fetch_and_upsert`: call weather source → `async with self._uow: repository.upsert_many(...)`.

### Timezones (three roles)

| Concern | Who decides |
|---------|-------------|
| Interpreting naive `start`/`end` | Query `location` (**IANA timezone**<sup>21</sup>, default `Europe/Madrid`) |
| Aggregation bucket boundaries | `station_location` (Antarctic → `UTC`; curated Canary ids → `Atlantic/Canary`; else Madrid) |
| Output `datetime` | Always converted to `Europe/Madrid` |

### Aggregation

Arithmetic **mean**<sup>6</sup> of present values per bucket (`optional_mean` skips `None`). Assignment did not specify the method; mean is the deliberate choice.

## Explain out loud

> “The use case owns cache-or-fetch, SingleFlight coalescing, and read-time aggregation. Domain entities stay frozen dataclasses; HTTP and ORM shapes map at the edges.”
