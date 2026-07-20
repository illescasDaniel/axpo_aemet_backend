# meteo-service

Python API that fetches weather observations from AEMET, caches raw samples in SQLite, applies optional time aggregation, and returns a clean JSON dataset.

## Setup

From the `backend/` directory:

```bash
uv sync
cp .env.example .env
```

Edit `.env` and set:

- `AEMET_API_KEY` — register at [AEMET Open Data](https://opendata.aemet.es/centrodedescargas/inicio)
- `DATABASE_URL` — see `.env.example` (example uses a local SQLite file under `./data/`)
- `CORS_ORIGINS` — JSON array of SPA origins allowed to call the API directly, e.g. `["http://localhost:3000"]`. Use `[]` only if you never call the API from a browser on another origin (same-origin proxy only).

## Run the API

```bash
uv run task dev
```

Health check: `GET http://127.0.0.1:8000/health`

Interactive docs: http://127.0.0.1:8000/docs

## Observations endpoint

```http
GET /api/v1/observations
```

Part 1 originally exposed `/api/v1/observations/antartida` and only allowed the two Antarctic station ids. Part 2 requires allowing multiple stations, so the public path was renamed to a generic `/observations` endpoint that accepts any `station_id` string.

Query parameters:

| Parameter | Required | Notes |
|-----------|----------|-------|
| `start` | yes | Naive datetime, format `AAAA-MM-DDTHH:MM:SS` |
| `end` | yes | Same format as `start` |
| `station_id` | yes | Any non-empty AEMET station id (e.g. `89064`, `89070`, or other ids) |
| `location` | no | IANA timezone for naive `start`/`end` (default `Europe/Madrid`); offsets like `+02:00` are rejected |
| `time_aggregation` | no | `hourly`, `daily`, or `monthly`; omit for raw 10-minute samples |
| `data_fields` | no | Repeatable: `temperature`, `pressure`, `speed`; omit for all three |

Example:

```bash
curl "http://127.0.0.1:8000/api/v1/observations?start=2025-01-15T00:00:00&end=2025-01-15T06:00:00&station_id=89064&location=UTC"
```

Response rows use field names `station`, `datetime`, `temperature`, `pressure`, `speed`. The `station` value is an object with `id` (AEMET station id) and `name` (station display name from AEMET). The `datetime` value is always in `Europe/Madrid` with offset (CET/CEST).

When AEMET reports that no data matches the selection, the API returns an empty list (`200`). Other upstream failures (HTTP errors, unexpected AEMET responses) yield `502`. Antarctic stations often have no data in mid-winter.

### Upstream AEMET products

AEMET has no single “any station + date range + 10‑min” product. The client routes by `station_id`:

| Stations | OpenData product | Notes |
|----------|------------------|-------|
| Antarctic (`89064`, `89070`) | `/api/antartida/datos/fechaini/.../fechafin/.../estacion/{id}` | Historical window; ~10‑min; fields `nombre`/`fhora`/`temp`/`pres`/`vel` |
| Everything else | `/api/observacion/convencional/datos/estacion/{id}` | Last ~24h only (no date params upstream); we filter by `start`/`end`; fields map `ubi`/`fint`/`ta`/`pres`/`vv` → same domain |

So mainland/Canary queries only return rows that fall in both the requested window **and** AEMET’s recent convencional payload. Older historical ranges for those stations will be empty (climatología diaria exists but is a different daily-aggregate product — not wired).

### Station timezone (aggregation buckets)

Used for hourly/daily/monthly bucket boundaries (not for the output `datetime`, which is always Madrid):

| Stations | Timezone |
|----------|----------|
| Known Antarctic (`89064`, `89070`) | `UTC` |
| Curated Canary ids (e.g. `C449C`, `C447A`, …) | `Atlantic/Canary` |
| Everything else (default) | `Europe/Madrid` |

## SQLite cache

Observations are stored as raw 10-minute samples (before aggregation). Policy for v1:

1. Read the requested `(station_id, start, end)` range from SQLite.
2. **Cache hit** — any rows found → serve from cache (no AEMET call).
3. **Cache miss** — empty range → fetch the whole window from AEMET, upsert into SQLite, then serve.

Aggregation and field projection still happen at read time, so the same cached rows can answer raw, hourly, daily, or monthly requests.

Logs (stderr, INFO) include cache hit/miss, AEMET fetch row counts, and upsert counts — useful when troubleshooting under load.

**Future improvement (not implemented):** partial coverage — serve the overlapping subrange from SQLite and fetch only missing gaps from AEMET, then merge/upsert. Today a non-empty but incomplete window is treated as a full hit.

### Concurrency (implemented)

Under concurrent cache misses for the same `(station_id, start, end)`:

- **In-process dedupe** (`SingleFlight` in `shared/single_flight.py`): only one AEMET fetch + upsert runs; other waiters reuse that result. The shared task stays registered until the work finishes, so a cancelled waiter does not start a second fetch.
- **SQLite pragmas** (on every connection): `PRAGMA journal_mode=WAL` and `PRAGMA busy_timeout=5000` so readers and one writer coexist better under API load.

Limits of this take-home setup (by design):

- Deduping is **one process / one event loop** only. Several uvicorn workers or hosts can still stampede AEMET for the same miss.
- SQLite still allows only **one writer at a time** per database file.

### Scale / ops (out of assignment scope)

Not implemented here; natural next steps if this left a take-home:

- **Migrations:** replace startup `Base.metadata.create_all` with **Alembic** (versioned upgrades; keep SQLAlchemy models as the source of truth).
- **Beyond SQLite:** for multi-instance / “thousands of requests,” move the durable observation cache to **PostgreSQL** (async SQLAlchemy URL + dialect-aware upsert). Use **Redis** (or Postgres advisory locks) if you also need cross-process miss coalescing.

## Smoke script (AEMET connectivity)

To check that your API key and the AEMET client work outside the HTTP layer:

```bash
uv run python scripts/smoke_aemet_fetch.py
```

The script loads `.env`, fetches a short summer window for Juan Carlos I (`89064`), and prints how many observations came back. Adjust `_STATION_ID` and the date range in the script if you want to try another station or period.

## Tests and quality gate

```bash
uv run task tests
uv run task checks-fix   # autofix + full gate
uv run task checks       # verify clean
```

Unit tests mock AEMET and the cache. Integration tests exercise the full FastAPI stack with fake weather source and in-memory repository.

## Architecture

Hexagonal layout under `src/meteo_service/observations/`: domain and use cases in the centre, FastAPI and AEMET on the outside.

Timezones:

- `location` interprets naive `start`/`end` (optional on the HTTP API; defaults to `Europe/Madrid`).
- Station timezone (see table above) is used for aggregation bucket boundaries.
- Output datetimes are converted to `Europe/Madrid`.

## Assumptions and quirks

These are deliberate take-home choices, not silent bugs:

- **Public path:** `GET /api/v1/observations` (renamed from Part 1’s `/antartida` for Part 2). Upstream: Antartida for Antarctic ids, observación convencional for others (see table above).
- **`location`:** assignment marks it optional. The use case always requires a timezone for naive `start`/`end`. The HTTP API defaults omitted `location` to `Europe/Madrid` so callers can skip it. IANA only; offsets like `+02:00` are rejected. `start`/`end` must be naive.
- **Aggregation:** arithmetic **mean** of samples in each bucket (assignment does not specify the method).
- **Cache:** v1 empty = miss / any rows = hit (see future gap-fill note above). No TTL / `fetched_at`, no negative cache for empty AEMET windows.
- **Database URL:** the app does not create parent directories for file-based SQLite URLs; that is up to whoever configures `DATABASE_URL`.

## CORS (frontend)

When the SPA runs on another origin (e.g. Bun on `http://localhost:3000`) and calls `http://127.0.0.1:8000` directly, set `CORS_ORIGINS` to that origin list. The app then adds `CORSMiddleware` for `GET`/`OPTIONS`.

If `CORS_ORIGINS` is empty or unset, no CORS middleware is registered. A Bun (or other) same-origin `/api` proxy does not need CORS — the browser only talks to the SPA origin.

## Security

This assignment does **not** include authentication. The API has **no login, tokens, or API keys for callers**. That is acceptable for a local coding exercise and **not** suitable for production exposure.

A production deployment would typically need: authn/authz (or strong network isolation), rate limiting, secrets management for `AEMET_API_KEY`, sanitized error responses (avoid leaking upstream details), HTTPS, and least-privilege database access. Keep `CORS_ORIGINS` locked to known frontend origins (already supported; see **CORS** above).

## Production / scale gaps

Out of scope for time / take-home size:

- Historical mainland series via climatología diaria (different granularity/fields); convencional only covers ~last day.
- Cross-process cache-miss coordination, Alembic migrations, and leaving SQLite for PostgreSQL (+ Redis for distributed coalescing) — see **Scale / ops** under SQLite cache above.
- Readiness probe that checks DB writability (today `/health` only returns `ok`).
- Structured / request-id logging.
- Cache freshness policy despite AEMET updating only a few times per day.
- Exhaustive Canary (or Ceuta/Melilla) station catalogs for timezone resolution.
