# AEMET integration

## Adapter: `AemetClient`

Implements the `WeatherSource` port. Lives in `observations/adapters/aemet/aemet_client.py`.

AEMET OpenData uses a **HATEOAS**<sup>18</sup> style: first call returns metadata + a `datos` URL; second call downloads the payload.

![AEMET Antartida — HATEOAS two-step](../slides/generated/04-aemet-hateoas.svg)

```python
async def fetch(self, station_id: str, start: datetime, end: datetime) -> list[Observation]:
    start_s = start.strftime("%Y-%m-%dT%H:%M:%SUTC")
    end_s = end.strftime("%Y-%m-%dT%H:%M:%SUTC")
    headers = {"accept": "application/json", "api_key": self._api_key}
    url = (
        "https://opendata.aemet.es/opendata/api/antartida/datos/"
        f"fechaini/{start_s}/fechafin/{end_s}/estacion/{station_id}"
    )
    response = await self._client.get(url, headers=headers)
    response.raise_for_status()
    hateoas = AemetHateoasResponse.model_validate_json(response.content)
    if hateoas.status == 404:
        return []
    if hateoas.status != 200:
        raise RuntimeError(f"AEMET error {hateoas.status}: {hateoas.description}")
    data_response = await self._client.get(hateoas.data_url, headers=headers)
    rows = TypeAdapter(list[AemetObservation]).validate_json(data_response.content)
    return to_observations(rows, station_id)
```

Callers must pass **UTC** datetimes (the use case already normalizes).

Auth to AEMET is an **API key**<sup>4</sup> header (`api_key`), from `Settings.aemet_api_key`.

## Payload mapping

AEMET fields → domain:

| AEMET | Domain |
|-------|--------|
| `nombre` | `Station.name` |
| `fhora` | `observed_at` |
| `temp` | `temperature_c` |
| `pres` | `pressure_hpa` |
| `vel` | `speed_ms` |

## Why not “all Spanish stations”?

AEMET has **no** single product that is “Antartida but for every station”:

| Product | Date range? | Granularity | Same fields? | Antarctic | Mainland |
|---------|-------------|-------------|--------------|-----------|----------|
| **Antartida** (this service) | Yes | ~10 min | Yes | Yes | No |
| Observación convencional | ≈ last 24h | ~hourly | Different | No | Yes |
| Climatología diaria | Yes | Daily aggregates | Different | No | Yes |

Supporting mainland properly means a second client, different coverage, and different mappers — a real product change. That experiment exists on `archive/aemet-dual-product` but was **not** merged into `main`.

## Smoke script

```bash
uv run python scripts/smoke_aemet_fetch.py
```

Loads `.env`, fetches a short summer window for `89064`, prints row count.

## Explain out loud

> “Outbound adapter does the AEMET HATEOAS two-step, validates with Pydantic, maps to domain Observations. Station allowlist at the API matches what Antartida actually serves.”
