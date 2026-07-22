# Glossary

Terms are numbered in **alphabetical order**. In earlier chapters, the first mention uses a superscript (e.g. FastAPI<sup>17</sup>) that points here.

1. **Adapter** — Concrete code that talks to the outside world (FastAPI router, AemetClient, SQLAlchemy repository) or drives the app.
2. **AEMET** — Agencia Estatal de Meteorología (Spain’s national weather service). This API uses its OpenData Antartida product.
3. **aiosqlite** — Async driver that lets SQLAlchemy talk to SQLite without blocking the event loop.
4. **API key** — Secret token identifying the caller to AEMET (`api_key` header). Stored in env as `AEMET_API_KEY`, not for authenticating *our* API’s callers.
5. **Application layer** — Use cases / application services that orchestrate domain objects through ports (`GetObservations`).
6. **Arithmetic mean** — Average of numeric samples in an aggregation bucket; `None` values are skipped (`optional_mean`).
7. **ASGI** — Asynchronous Server Gateway Interface; the async equivalent of WSGI. FastAPI apps are ASGI apps.
8. **ASGITransport** — httpx transport that sends requests into an ASGI app in-process (used instead of a real network server in API tests).
9. **basedpyright** — Strict static type checker for Python (Pyright-based), configured `typeCheckingMode = "strict"`.
10. **Bounded context** — DDD term for a cohesive model boundary with its own ubiquitous language. Here: `observations`.
11. **CORS** — Cross-Origin Resource Sharing: browser rules for calling an API from another origin (configured for the frontend SPA).
12. **Dataclass** — `@dataclass` helper that auto-generates `__init__` / equality. Here entities are `frozen=True` (immutable).
13. **Dependency injection (DI)** — Providing collaborators from the outside (constructors / FastAPI `Depends`) instead of constructing them inside the use case.
14. **Domain layer** — Innermost code: entities and rules with no framework imports (`observations/domain/`).
15. **DTO (Data Transfer Object)** — Object shaped for carrying data across a boundary (e.g. `ObservationView` out of the use case), not for rich domain behavior.
16. **Fake** — Test double that provides a working in-memory implementation of a port (not a mock framework stub). Lives under `tests/fakes/`.
17. **FastAPI** — Modern Python web framework for building APIs on ASGI, with automatic OpenAPI docs and Pydantic validation.
18. **HATEOAS** — Hypermedia API style where a response includes links to related resources. AEMET returns a metadata object with a `datos` URL to fetch next.
19. **Hexagonal architecture** — Design style that keeps business logic in the centre and pushes frameworks to the outside (“hexagon”), connected through ports.
20. **httpx2** — Async-capable HTTP client library used to call AEMET and to drive ASGI tests.
21. **IANA timezone** — Named timezone from the IANA database (e.g. `Europe/Madrid`, `UTC`), as used by `zoneinfo.ZoneInfo`.
22. **JSON** — JavaScript Object Notation; the HTTP response format for observations.
23. **Literal type** — `typing.Literal[...]` restricts a value to an exact set of constants (here `station_id` to `"89064"` | `"89070"`).
24. **Namespace package** — Python package without `__init__.py` in every subfolder (implicit namespace). This repo keeps only the top-level `meteo_service/__init__.py` for the build backend.
25. **ORM** — Object-Relational Mapper: maps tables to Python classes (`ObservationRow`) and back.
26. **pip-audit** — Tool that checks installed dependencies for known security vulnerabilities.
27. **Ports and adapters** — Another name for hexagonal architecture: *ports* are interfaces the core needs; *adapters* implement or drive those ports (HTTP, DB, external APIs).
28. **Primary key** — Column(s) that uniquely identify a row. Here `(station_id, observed_at)`.
29. **Protocol** — `typing.Protocol`: structural interface. Classes match if they have the right methods, without inheriting a base class.
30. **Pydantic** — Data validation library using Python type hints; powers request/response and AEMET payload models.
31. **pydantic-settings** — Pydantic extension that loads and validates settings from environment variables / `.env`.
32. **pytest** — Python testing framework used for unit and integration tests.
33. **pytest-asyncio** — Pytest plugin that runs `async def` tests (here with `asyncio_mode = auto`).
34. **Python** — The programming language (this project requires ≥3.12).
35. **ruff** — Extremely fast Python linter and formatter (replaces flake8/isort/black-style workflows here).
36. **SingleFlight** — In-process helper: concurrent callers with the same key share one in-flight async task (coalesce duplicate work).
37. **SQLAlchemy** — Python SQL toolkit and ORM. This project uses the async API with SQLite.
38. **SQLite** — Embedded relational database stored as a local file (or `:memory:` in tests). Used here as the observation cache.
39. **taskipy** — Tiny task runner configured in `pyproject.toml` (`uv run task …`).
40. **Unit of Work (UoW)** — Pattern that groups work into a single transactional boundary (commit or rollback together). Repositories do not commit themselves.
41. **Upsert** — Insert a row, or update it if the primary key already exists (`ON CONFLICT DO UPDATE`).
42. **uv** — Fast Python package manager and project toolchain (lockfile, sync, build). Used instead of pip/poetry here.
43. **uvicorn** — ASGI server commonly used to run FastAPI (including via `fastapi dev` / task runners). Multiple worker processes do not share in-memory SingleFlight state.
44. **WAL (Write-Ahead Logging)** — SQLite journal mode that improves concurrent readers with a single writer (`PRAGMA journal_mode=WAL`).
