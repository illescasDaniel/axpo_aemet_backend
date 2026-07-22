# Architecture (hexagonal)

## Why hexagonal here

The service is organized as **hexagonal architecture**<sup>19</sup> (also called **ports and adapters**<sup>27</sup>): domain and application logic sit in the centre; frameworks (FastAPI, httpx2, SQLAlchemy) live only in adapters.

That lets you:

- Unit-test the use case with in-memory **fakes**<sup>16</sup> (no HTTP, no DB).
- Swap AEMET or SQLite without rewriting business rules.
- Keep explanations crisp: “core is pure; edges are adapters.”

![Hexagonal layout — observations](../slides/generated/02-hexagonal.svg)

## Package layout

**Bounded context**<sup>10</sup>: **observations**. Cross-cutting helpers live under **shared**.

```text
src/meteo_service/
├── main.py                          # app = create_app()
├── observations/
│   ├── domain/                      # entities only
│   ├── application/                 # use case + ports + views
│   │   └── ports/                   # Protocol ports
│   └── adapters/
│       ├── api/                     # FastAPI inbound
│       ├── aemet/                   # AemetClient → WeatherSource
│       └── database/                # SqlAlchemyObservationRepository → ObservationRepository
└── shared/
    ├── config, database, logging, single_flight, unit_of_work
    └── adapters/api/, sqlalchemy_unit_of_work
```

Only `meteo_service/__init__.py` exists as a package marker (**namespace packages**<sup>24</sup> elsewhere; `uv_build` needs that top-level `__init__.py`).

## Layers

| Layer | Path | May depend on |
|-------|------|----------------|
| **Domain**<sup>14</sup> | `observations/domain/` | Nothing framework-related |
| **Application**<sup>5</sup> | `observations/application/` | Domain + ports + shared UoW / SingleFlight |
| **Adapters**<sup>1</sup> | `observations/adapters/*`, `shared/adapters/*` | Application/domain + FastAPI / httpx / SQLAlchemy |

## Ports (contracts)

Ports are `typing.Protocol`<sup>29</sup> — structural typing, so fakes need no inheritance.

**WeatherSource** (`application/ports/weather_source.py`):

```python
class WeatherSource(Protocol):
    async def fetch(
        self,
        station_id: str,
        start: datetime,
        end: datetime,
    ) -> list[Observation]: ...
```

**ObservationRepository** — `get_range`, `upsert_many`.

**UnitOfWork** — async context manager; commit on success, rollback on error.

## Request flow

![Request flow — GET /api/v1/observations](../slides/generated/01-request-flow.svg)

## Dependency direction

> “Dependencies point inward. The use case depends on Protocols, not on AemetClient or SQLAlchemy. FastAPI wires concrete adapters through Depends.”

## Explain out loud

> “Hexagonal layout around an observations bounded context: domain entities, application use case + ports, adapters for API / AEMET / SQLite. Fakes live under tests/, not in production adapters.”
