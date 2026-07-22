---
marp: true
title: meteo-service — Backend walkthrough
author: Daniel Illescas Romero
paginate: true
size: 16:9
theme: default
style: |
  /* Force light scheme so theme `light-dark()` tokens stay readable in PDF print. */
  section {
    color-scheme: only light;
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    color: #1a1a1a;
    background: #fafaf8;
  }
  h1, h2 {
    color: #0f3d4c;
    font-weight: 700;
  }
  h1 { font-size: 48px; }
  h2 { font-size: 36px; }
  section::after {
    color: #666;
  }
  strong { color: #0b57d0; }
  code {
    background: #eef2f4;
    color: #1a1a1a;
    font-size: 0.9em;
  }
  /* Light code panels + explicit token colors (print-safe, no light-dark()). */
  pre, pre code, marp-pre, marp-pre code {
    background: #f4f6f8 !important;
    color: #1a1a1a !important;
    border: 1px solid #d0d7de;
    border-radius: 8px;
    font-size: 18px;
    line-height: 1.35;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }
  pre code, marp-pre code {
    border: none;
    background: transparent !important;
  }
  pre .hljs,
  marp-pre .hljs {
    background: transparent !important;
    color: #1a1a1a !important;
  }
  .hljs-keyword, .hljs-selector-tag { color: #cf222e !important; }
  .hljs-string, .hljs-attr, .hljs-attribute { color: #0a3069 !important; }
  .hljs-comment { color: #6e7781 !important; }
  .hljs-title, .hljs-section, .hljs-title.function_ { color: #8250df !important; }
  .hljs-built_in, .hljs-type { color: #953800 !important; }
  .hljs-literal, .hljs-number { color: #0550ae !important; }
  table {
    font-size: 22px;
  }
  img {
    display: block;
    margin: 0 auto;
    max-height: 420px;
  }
  footer {
    color: #888;
    font-size: 14px;
  }
  section.lead h1 { font-size: 56px; }
  section.lead p { font-size: 26px; color: #444; }
  section.center { text-align: center; }
---

<!-- _class: lead center -->

# 1. meteo-service

### Axpo take-home — backend walkthrough

AEMET observations · SQLite cache · FastAPI

---

# 2. What it does

1. **Fetch** Antarctic weather observations from AEMET
2. **Cache** raw ~10-minute samples in SQLite
3. **Serve** them over HTTP with optional aggregation

---

# 3. Public API

`GET /api/v1/observations`

```bash
?start=2025-01-15T00:00:00
&end=2025-01-15T06:00:00
&station_id=89064
&location=UTC
```

Also: `GET /health` → `{"status":"ok"}`

---

# 4. Stations (allowlist)

| ID | Station |
|----|---------|
| `89064` | Juan Carlos I |
| `89070` | Gabriel de Castilla |

Only AEMET **Antartida** matches the historical date-range + field shape.

Other ids → **422**. Mainland products = different API (out of scope on `main`).

---

# 5. Architecture

Hexagonal (ports & adapters) around **observations**

![hexagonal](generated/02-hexagonal.svg)

---

# 6. Ports (contracts)

Three Protocols — no framework types in the centre

| Port | Role |
|------|------|
| `WeatherSource` | Fetch upstream observations |
| `ObservationRepository` | Cache read / upsert |
| `UnitOfWork` | Commit / rollback boundary |

**Why Protocol?** Structural typing → easy fakes in tests.

---

# 7. Request flow

![request flow](generated/01-request-flow.svg)

---

# 8. Use case: `GetObservations`

Owns the orchestration:

- Normalize naive `start` / `end` → UTC
- **Cache or fetch** (via SingleFlight on miss)
- Aggregate (hourly / daily / monthly) **or** return raw
- Project fields (`temperature` / `pressure` / `speed`)

---

# 9. Cache policy

![cache policy](generated/03-cache-policy.svg)

---

# 10. Design choice: cache raw

- Store **raw** samples once
- Aggregate / project **at read time**
- One cache answers many query shapes

**v1 shortcut:** any rows = hit (no gap-fill yet)

---

# 11. AEMET integration

![aemet hateoas](generated/04-aemet-hateoas.svg)

---

# 12. Timezones (three roles)

| Role | Who |
|------|-----|
| Interpret naive `start`/`end` | Query `location` (default Madrid) |
| Aggregation buckets | Station timezone (Antarctic → UTC) |
| Response `datetime` | Always **Europe/Madrid** |

---

# 13. Snippet — port shape

```python
class WeatherSource(Protocol):
    async def fetch(
        self,
        station_id: str,
        start: datetime,
        end: datetime,
    ) -> list[Observation]: ...
```

Adapters implement this; the use case never imports AEMET.

---

# 14. Snippet — SingleFlight

```python
class SingleFlight[T]:
    async def do(self, key, factory):
        if (task := self._inflight.get(key)) is None:
            task = asyncio.create_task(factory())
            self._inflight[key] = task
        return await task
```

Same miss key → **one** AEMET fetch (per process).

---

# 15. Testing

- **Unit:** use case + in-memory fakes (`tests/fakes/`)
- **API:** async `httpx2` + `ASGITransport` (not sync TestClient)
- **AEMET:** HTTP mocked with pytest-httpx2
- Naming: `given_…_when_…_then_…`

---

# 16. Quality gate

One script, same locally and in CI:

**ruff → shellcheck → basedpyright → pip-audit → build → pytest**

```bash
./scripts/quality/checks.sh --fix
```

---

# 17. Deliberate non-goals

Take-home choices, not silent bugs:

- No caller authentication
- No Alembic (startup `create_all`)
- No gap-fill cache / TTL
- No multi-worker SingleFlight (in-process only)

---

# 18. Ask me about…

- Why hexagonal + Protocol ports?
- Why cache raw and aggregate on read?
- Why only two stations on `main`?
- SingleFlight vs multi-instance scale?
- What I'd do next in production

---

<!-- _class: lead center -->

# 19. Thanks — questions?

meteo-service · FastAPI · hexagonal · AEMET
