"""Quick manual check that the AEMET client can fetch observations."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path

import httpx2
from dotenv import load_dotenv

from meteo_service.observations.adapters.aemet.client import AemetClient
from meteo_service.shared.config import get_settings
from meteo_service.shared.logging import configure_logging


# Antarctic (Antartida product): 89064 / 89070 — use an austral summer window.
# Mainland (convencional, last ~24h): e.g. 3195 — set start/end to "today" UTC.
_STATION_ID = "89064"


async def main():
    _ = configure_logging()
    get_settings.cache_clear()
    settings = get_settings()

    start = datetime(2025, 1, 15, 0, 0, 0, tzinfo=UTC)
    end = datetime(2025, 1, 15, 6, 0, 0, tzinfo=UTC)

    async with httpx2.AsyncClient(timeout=60.0) as http:
        client = AemetClient(http, api_key=settings.aemet_api_key)
        rows = await client.fetch(_STATION_ID, start, end)

    print(f"Fetched {len(rows)} observation(s) for station {_STATION_ID}.")
    if rows:
        first = rows[0]
        print(f"First: {first.observed_at.isoformat()} temp={first.temperature_c} pres={first.pressure_hpa} vel={first.speed_ms}")


if __name__ == "__main__":
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    get_settings.cache_clear()
    asyncio.run(main())
