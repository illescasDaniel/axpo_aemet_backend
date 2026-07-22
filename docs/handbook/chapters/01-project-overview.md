# Project overview

## What this backend is

**meteo-service** is a Python API for an Axpo take-home assignment. It:

1. Accepts HTTP queries for weather observations over a date range.
2. Fetches data from Spain’s meteorological agency **AEMET**<sup>2</sup> (Antartida / Antarctic product).
3. Caches raw ~10-minute samples in **SQLite**<sup>38</sup>.
4. Optionally aggregates (hourly / daily / monthly means) and projects fields.
5. Returns clean **JSON**<sup>22</sup> via a **FastAPI**<sup>17</sup> HTTP API.

Package name: `meteo-service` (import path `meteo_service`). Version `0.1.0`.

## Public surface

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Liveness: `{"status":"ok"}` |
| `GET` | `/api/v1/observations` | Observations for a station and time range |

Part 1 of the assignment used `/api/v1/observations/antartida`. Part 2 asked for a more open station surface, so the path became generic `GET /api/v1/observations`. In practice only AEMET’s **Antartida** product matches the historical date-range + ~10‑min + field shape (`nombre` / `fhora` / `temp` / `pres` / `vel`), so `station_id` is allowlisted to:

- `89064` — Juan Carlos I
- `89070` — Gabriel de Castilla

Other station ids return **422**. Mainland Spanish stations are **not** supported on `main` (a dual-product experiment lives on branch `archive/aemet-dual-product` and was not merged).

## Example request

```bash
curl "http://127.0.0.1:8000/api/v1/observations?start=2025-01-15T00:00:00&end=2025-01-15T06:00:00&station_id=89064&location=UTC"
```

Response rows look like:

```json
{
  "station": {"id": "89064", "name": "Juan Carlos I"},
  "datetime": "2025-01-15T01:00:00+01:00",
  "temperature": -2.1,
  "pressure": 980.5,
  "speed": 4.2
}
```

`datetime` is always emitted in `Europe/Madrid` (CET/CEST with offset). Metrics may be `null`.

## What it deliberately does *not* include

- No authentication for API callers (take-home choice).
- No Alembic migrations (schema via `create_all` on startup).
- No Redis / multi-worker cache coalescing.
- No gap-fill cache policy (v1: any rows = hit; empty = miss).

## Explain out loud

> “I built a small hexagonal FastAPI service that proxies AEMET Antarctic observations, caches raw samples in SQLite, and applies aggregation at read time so one cache serves many query shapes.”
