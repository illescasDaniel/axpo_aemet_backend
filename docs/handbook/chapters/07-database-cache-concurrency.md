# Database, cache, and concurrency

## SQLite as observation cache

URL example: `sqlite+aiosqlite:///./data/meteo.sqlite`.

`Database` (`shared/database.py`) is an async context manager: create engine, apply pragmas, `Base.metadata.create_all` on startup (imports ORM models for metadata registration). **No Alembic.**

### ORM model

```python
class ObservationRow(Base):
    """Cached raw observation from AEMET (not aggregated)."""

    __tablename__ = "observations"

    station_id: Mapped[str] = mapped_column(String, primary_key=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)

    station_name: Mapped[str] = mapped_column(String)
    temperature_c: Mapped[float | None] = mapped_column(Float)
    pressure_hpa: Mapped[float | None] = mapped_column(Float)
    speed_ms: Mapped[float | None] = mapped_column(Float)
```

Composite **primary key**<sup>28</sup> `(station_id, observed_at)`. This is the **ORM**<sup>25</sup> row; domain mapping happens in `database/mappers.py`.

### Repository + upsert

Repositories do **not** commit. `upsert_many` uses SQLite `INSERT ... ON CONFLICT DO UPDATE` (**upsert**<sup>41</sup>):

```python
stmt = insert(ObservationRow).values(values)
stmt = stmt.on_conflict_do_update(
    index_elements=[ObservationRow.station_id, ObservationRow.observed_at],
    set_={
        "station_name": stmt.excluded.station_name,
        "temperature_c": stmt.excluded.temperature_c,
        "pressure_hpa": stmt.excluded.pressure_hpa,
        "speed_ms": stmt.excluded.speed_ms,
    },
)
await self._session.execute(stmt)
```

`SqlAlchemyUnitOfWork` commits on clean exit, rolls back on exception.

## Cache policy (v1)

![Cache policy (v1) + SingleFlight](../slides/generated/03-cache-policy.svg)

1. Read `(station_id, start, end)` from SQLite.
2. **Any rows** → **cache hit** (no AEMET call).
3. **Empty** → **cache miss** → fetch whole window from AEMET, upsert, serve.

Aggregation and field projection happen **at read time**, so the same raw rows answer raw / hourly / daily / monthly queries.

**Not implemented:** gap-fill (partial coverage → fetch only missing ranges). A non-empty but incomplete window is treated as a full hit. No TTL / `fetched_at`, no negative cache for empty AEMET windows.

## Concurrency

### SingleFlight

```python
class SingleFlight[T]:
    """If several callers ask for the same key at once, only one runs factory; others await that result."""

    async def do(self, key: Hashable, factory: Callable[[], Coroutine[Any, Any, T]]) -> T:
        if (task := self._inflight.get(key)) is None:
            task = asyncio.create_task(factory())
            self._inflight[key] = task
            task.add_done_callback(lambda _: self._inflight.pop(key, None))
        return await task
```

Source: `shared/single_flight.py`. **In-process only** — multiple **uvicorn**<sup>43</sup> workers can still stampede AEMET.

### SQLite pragmas

On every connection:

- `PRAGMA journal_mode=WAL`<sup>44</sup> — readers and one writer coexist better
- `PRAGMA busy_timeout=5000`

SQLite still allows only **one writer at a time** per file.

## Scale next steps (out of take-home scope)

- Alembic migrations instead of `create_all`
- PostgreSQL for multi-instance durable cache
- Redis (or Postgres advisory locks) for cross-process miss coalescing

## Explain out loud

> “I cache raw samples only, upsert on miss, and let the Unit of Work own commits. SingleFlight plus WAL keep concurrent same-key misses from hammering AEMET inside one process.”
