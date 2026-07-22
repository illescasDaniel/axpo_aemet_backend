# Testing and quality

## Test layout

```text
tests/
├── conftest.py
├── fakes/                    # FakeObservationRepository, FakeWeatherSource, FakeUnitOfWork, …
├── test_health.py
├── observations/
│   ├── application/          # unit: cache, aggregation, single-flight
│   └── adapters/
│       ├── aemet/            # httpx2 mock / Router
│       ├── api/              # ASGI integration + schema tests
│       └── database/         # in-memory SQLite
└── shared/                   # CORS, Database pragmas, SqlAlchemy UoW
```

Markers: `@pytest.mark.unit` / `integration`. Naming style: `given_…_when_…_then_…`.

## Fakes vs production adapters

Production adapters live under `src/.../adapters/`. **Fakes** live under `tests/fakes/` and implement the same Protocols — no inheritance required.

That is the payoff of hexagonal ports: swap `AemetClient` for `FakeWeatherSource` in unit tests.

## API tests (async, not TestClient)

API tests use async `httpx2.AsyncClient` + **ASGITransport**<sup>8</sup> against the FastAPI app (not sync `TestClient`).

Override the use case:

```python
app.dependency_overrides[get_observations_use_case] = lambda: fake_use_case
```

DB fixture often uses `Database("sqlite+aiosqlite:///:memory:")`.

AEMET client tests mock HTTP with `pytest-httpx2`.

## Quality gate

```bash
uv run task tests
uv run task checks-fix
uv run task checks
```

`./scripts/quality/checks.sh` runs: ruff → shell → basedpyright (strict) → pip-audit → build → pytest.

CI: `backend/.github/workflows/ci.yml` with uv sync and the same script (`CI=true`).

## Explain out loud

> “Unit tests hit the use case with fakes; integration tests exercise FastAPI over ASGITransport and SQLite in memory. The quality gate is one script so CI and local match.”
