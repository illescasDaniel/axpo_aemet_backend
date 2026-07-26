# API layer

## App entry

- `meteo_service.main:app` → `create_app(get_settings())` in `shared/adapters/api/app.py`
- Lifespan (`shared/adapters/api/lifespan.py`) opens `Database`, shared `httpx2.AsyncClient` (60s timeout), and process-wide `SingleFlight`

## Routes

```python
@router.get("/observations")
async def get_observations(
    query: Annotated[GetObservationsQuery, Query()],
    use_case: Annotated[GetObservations, Depends(get_observations_use_case)],
) -> list[ObservationResponse]:
    try:
        rows = await use_case.execute(
            station_id=query.station_id,
            start=query.start,
            end=query.end,
            station_location=query.resolved_station_location(),
            location=query.location,
            time_aggregation=query.time_aggregation,
            data_fields=query.data_fields,
        )
    except (RuntimeError, httpx2.HTTPError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return [to_observation_response(row) for row in rows]
```

Source: `observations/adapters/api/v1/router.py`. Mounted under `/api/v1`.

## Query model

`GetObservationsQuery` (Pydantic):

| Param | Required | Notes |
|-------|----------|-------|
| `start` / `end` | yes | Naive strings `AAAA-MM-DDTHH:MM:SS` (offsets like `+02:00` rejected) |
| `station_id` | yes | **`Literal`**<sup>23</sup>`["89064","89070"]` |
| `location` | no | IANA zone for naive bounds (default `Europe/Madrid`) |
| `time_aggregation` | no | `hourly` / `daily` / `monthly` |
| `data_fields` | no | Repeatable: `temperature`, `pressure`, `speed` |

Invalid input → **422**. Upstream failures → **502**. AEMET “no data” (HATEOAS 404) → empty list **200**.

## Dependency injection

FastAPI **dependency injection**<sup>13</sup> wires adapters in `dependencies.py`:

```python
def get_observations_use_case(
    weather_source: Annotated[AemetClient, Depends(get_weather_source)],
    repository: Annotated[SqlAlchemyObservationRepository, Depends(get_observation_repository)],
    uow: Annotated[SqlAlchemyUnitOfWork, Depends(get_unit_of_work)],
    single_flight: Annotated[SingleFlight[list[Observation]], Depends(get_single_flight)],
) -> GetObservations:
    return GetObservations(weather_source, repository, uow, single_flight)
```

HTTP client, DB, and SingleFlight come from `request.app.state` set in lifespan.

## CORS

If `cors_origins` is non-empty, **CORS**<sup>11</sup> middleware allows `GET` and `OPTIONS` with `allow_headers=["*"]` — for the frontend SPA.

## Security (honest take-home note)

No login, tokens, or caller API keys. Fine for a local exercise; not for public production exposure.

## Explain out loud

> “The router is thin: validate query with Pydantic, call the use case via Depends, map views to responses, translate upstream errors to 502.”
