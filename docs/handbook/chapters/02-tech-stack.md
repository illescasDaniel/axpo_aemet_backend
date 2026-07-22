# Tech stack

## Language and tooling

| Piece | Role in this project |
|-------|----------------------|
| **Python**<sup>34</sup> ≥3.12 | Runtime (`.python-version` = `3.12`) |
| **uv**<sup>42</sup> | Package manager, lockfile (`uv.lock`), build backend (`uv_build`) |
| **taskipy**<sup>39</sup> | Dev tasks: `dev`, `tests`, `checks`, `checks-fix` |

## Runtime libraries

| Library | Role |
|---------|------|
| **FastAPI** (`fastapi[standard]`) | HTTP API on **ASGI**<sup>7</sup> |
| **httpx2**<sup>20</sup> | Async HTTP client for AEMET and async API tests |
| **SQLAlchemy**<sup>37</sup> (async) | ORM / sessions |
| **aiosqlite**<sup>3</sup> | Async SQLite driver |
| **Pydantic**<sup>30</sup> | Request/response and AEMET payload models |
| **pydantic-settings**<sup>31</sup> | Env-validated `Settings` |

There is **no** Redis, Alembic, auth library, or sync `TestClient` in this codebase.

## Quality / test tooling

| Tool | Role |
|------|------|
| **ruff**<sup>35</sup> | Lint + format (line length 120, spaces) |
| **basedpyright**<sup>9</sup> | Strict type checking |
| **pytest**<sup>32</sup> + **pytest-asyncio**<sup>33</sup> | Tests (`asyncio_mode = auto`) |
| **pytest-httpx2** | Mock AEMET HTTP in adapter tests |
| **pip-audit**<sup>26</sup> | Dependency vulnerability scan |

Quality gate from `backend/`:

```bash
./scripts/quality/checks.sh --fix   # autofix + full gate
./scripts/quality/checks.sh           # verify clean
# or: uv run task checks-fix / uv run task checks
```

Gate order: ruff → shellcheck/shfmt → basedpyright → pip-audit → `uv build` → pytest.

## Settings (how config is loaded)

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    aemet_api_key: str = Field(min_length=1)
    database_url: str = Field(min_length=1)
    cors_origins: list[str] = Field(default_factory=list)


@lru_cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]
```

Source: `src/meteo_service/shared/config.py`. Env vars: `AEMET_API_KEY`, `DATABASE_URL`, `CORS_ORIGINS` (JSON array). Injected via FastAPI `Depends` / lifespan — not re-parsed ad hoc in modules.

## Explain out loud

> “Stack is intentionally small: FastAPI + httpx2 + async SQLAlchemy/SQLite + pydantic-settings, with a strict quality gate (ruff, basedpyright, pip-audit, pytest) run through one script.”
