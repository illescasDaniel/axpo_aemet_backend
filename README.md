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

Part 1 originally exposed `/api/v1/observations/antartida`. Part 2 asked for a more open station surface, so the public path is the generic `GET /api/v1/observations`. In practice only AEMET’s **Antartida** product matches this assignment’s date-range + ~10‑min + `nombre`/`fhora`/`temp`/`pres`/`vel` shape, so `station_id` is validated to the two Antarctic ids (`89064`, `89070`). Other ids return `422`.

Query parameters:

| Parameter | Required | Notes |
|-----------|----------|-------|
| `start` | yes | Naive datetime, format `AAAA-MM-DDTHH:MM:SS` |
| `end` | yes | Same format as `start` |
| `station_id` | yes | `89064` (Juan Carlos I) or `89070` (Gabriel de Castilla) |
| `location` | no | IANA timezone for naive `start`/`end` (default `Europe/Madrid`); offsets like `+02:00` are rejected |
| `time_aggregation` | no | `hourly`, `daily`, or `monthly`; omit for raw 10-minute samples |
| `data_fields` | no | Repeatable: `temperature`, `pressure`, `speed`; omit for all three |

Example:

```bash
curl "http://127.0.0.1:8000/api/v1/observations?start=2025-01-15T00:00:00&end=2025-01-15T06:00:00&station_id=89064&location=UTC"
```

Response rows use field names `station`, `datetime`, `temperature`, `pressure`, `speed`. The `station` value is an object with `id` (AEMET station id) and `name` (AEMET `nombre`). The `datetime` value is always in `Europe/Madrid` with offset (CET/CEST).

When AEMET reports that no data matches the selection, the API returns an empty list (`200`). Other upstream failures (HTTP errors, unexpected AEMET responses) yield `502`. Antarctic stations often have no data in mid-winter.

### Important: why not “all Spanish stations”?

AEMET OpenData has **no single product** that is “Antartida but for every station”:

| Product | Date range? | Granularity | Same fields as Part 1? | Works for Antarctic? | Works for mainland? |
|---------|-------------|-------------|------------------------|----------------------|---------------------|
| **Antartida** (this service) | Yes | ~10 min | Yes (`nombre`/`fhora`/`temp`/`pres`/`vel`) | Yes | No (HATEOAS 404) |
| Observación convencional | No (≈ last 24h) | ~hourly / recent | Different (`ubi`/`fint`/`ta`/`pres`/`vv`) | No | Yes |
| Climatología diaria | Yes | Daily aggregates | Different (`tmed`/`velmedia`/…) | No | Yes |

Wiring mainland stations properly means a **second upstream client**, different input coverage (no historical window on convencional), and different payload → domain mapping. That is a real product change, not a URL swap.

A **minimal dual-product experiment** (Antartida for Antarctic ids + observación convencional for others, shared HATEOAS helper, field remapping, client-side `start`/`end` filter) lives on git branch `archive/aemet-dual-product`. It was **not merged into `main`**: for a short take-home, supporting divergent AEMET endpoints and models is out of scope; Part 2 here keeps Antartida + SQLite cache + logging, with `station_id` limited to the two stations that product actually serves.

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

- **Public path:** `GET /api/v1/observations` (renamed from Part 1’s `/antartida`). `station_id` allowlisted to `89064` / `89070`; upstream is Antartida only (see **Important: why not “all Spanish stations”?**).
- **`location`:** assignment marks it optional. The use case always requires a timezone for naive `start`/`end`. The HTTP API defaults omitted `location` to `Europe/Madrid` so callers can skip it. IANA only; offsets like `+02:00` are rejected. `start`/`end` must be naive.
- **Aggregation:** arithmetic **mean** of samples in each bucket (assignment does not specify the method).
- **Cache:** v1 empty = miss / any rows = hit (see future gap-fill note above). No TTL / `fetched_at`, no negative cache for empty AEMET windows.
- **Database URL:** the app does not create parent directories for file-based SQLite URLs; that is up to whoever configures `DATABASE_URL`.

## Security

This assignment does **not** include authentication. The API has **no login, tokens, or API keys for callers**. That is acceptable for a local coding exercise and **not** suitable for production exposure.

A production deployment would typically need: authn/authz (or strong network isolation), rate limiting, CORS locked to known frontends, secrets management for `AEMET_API_KEY`, sanitized error responses (avoid leaking upstream details), HTTPS, and least-privilege database access.

## Production / scale gaps

Out of scope for time / take-home size:

- Merging multi-product AEMET adapters into `main` (see branch `archive/aemet-dual-product` and the section above).
- Cross-process cache-miss coordination, Alembic migrations, and leaving SQLite for PostgreSQL (+ Redis for distributed coalescing) — see **Scale / ops** under SQLite cache above.
- Readiness probe that checks DB writability (today `/health` only returns `ok`).
- Structured / request-id logging.
- Cache freshness policy despite AEMET updating only a few times per day.
- Exhaustive Canary (or Ceuta/Melilla) station catalogs for timezone resolution.
