from datetime import UTC, datetime

import httpx2
import pytest
from pydantic import ValidationError
from respx import Router

from meteo_service.observations.adapters.aemet.client import AemetClient


pytestmark = pytest.mark.unit

_API_KEY = "test-api-key"
_STATION_ID = "89064"
_START = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
_END = datetime(2024, 1, 1, 1, 0, 0, tzinfo=UTC)
_DATA_URL = "https://opendata.aemet.es/opendata/api/antartida/datos/data.json"
_META_URL = "https://opendata.aemet.es/opendata/api/antartida/datos/meta.json"
_ANTARTIDA_URL_RE = r"https://opendata\.aemet\.es/opendata/api/antartida/datos/fechaini/.+/fechafin/.+/estacion/.+"


def _hateoas(*, status: int = 200, description: str = "Éxito") -> dict[str, object]:
    return {
        "descripcion": description,
        "estado": status,
        "datos": _DATA_URL,
        "metadatos": _META_URL,
    }


def _observation_payload() -> list[dict[str, object]]:
    return [
        {
            "nombre": "Juan Carlos I",
            "fhora": "2024-01-01T00:10:00Z",
            "temp": -5.2,
            "pres": 980.1,
            "vel": 12.3,
        }
    ]


async def test_given_valid_hateoas_and_observations_when_fetching_then_returns_mapped_domain_rows(
    httpx2_mock: Router,
):
    # given
    httpx2_mock.get(url__regex=_ANTARTIDA_URL_RE).respond(json=_hateoas())
    httpx2_mock.get(_DATA_URL).respond(json=_observation_payload())

    # when
    async with httpx2.AsyncClient() as http:
        client = AemetClient(http, api_key=_API_KEY)
        rows = await client.fetch(_STATION_ID, _START, _END)

    # then
    assert len(rows) == 1
    assert rows[0].station.id == "89064"
    assert rows[0].station.name == "Juan Carlos I"
    assert rows[0].observed_at == datetime(2024, 1, 1, 0, 10, tzinfo=UTC)
    assert rows[0].temperature_c == -5.2
    assert rows[0].pressure_hpa == 980.1
    assert rows[0].speed_ms == 12.3


async def test_given_utc_range_when_fetching_then_requests_expected_url_with_api_key(
    httpx2_mock: Router,
):
    # given
    expected_url = (
        "https://opendata.aemet.es/opendata/api/antartida/datos/"
        "fechaini/2024-01-01T00:00:00UTC/fechafin/2024-01-01T01:00:00UTC/"
        f"estacion/{_STATION_ID}"
    )
    route = httpx2_mock.get(expected_url).respond(json=_hateoas())
    data_route = httpx2_mock.get(_DATA_URL).respond(json=_observation_payload())

    # when
    async with httpx2.AsyncClient() as http:
        client = AemetClient(http, api_key=_API_KEY)
        await client.fetch(_STATION_ID, _START, _END)

    # then
    assert route.called
    assert route.calls.last.request.headers["api_key"] == _API_KEY
    assert data_route.called
    assert data_route.calls.last.request.headers["api_key"] == _API_KEY


async def test_given_hateoas_no_data_status_when_fetching_then_returns_empty_list(
    httpx2_mock: Router,
):
    # given
    httpx2_mock.get(url__regex=_ANTARTIDA_URL_RE).respond(
        json=_hateoas(status=404, description="No hay datos que satisfacer esta selección")
    )

    async with httpx2.AsyncClient() as http:
        client = AemetClient(http, api_key=_API_KEY)

        # when
        rows = await client.fetch(_STATION_ID, _START, _END)

    # then
    assert rows == []


async def test_given_hateoas_error_status_when_fetching_then_raises_runtime_error(
    httpx2_mock: Router,
):
    # given
    httpx2_mock.get(url__regex=_ANTARTIDA_URL_RE).respond(
        json=_hateoas(status=401, description="API key no valida o caducada")
    )

    async with httpx2.AsyncClient() as http:
        client = AemetClient(http, api_key=_API_KEY)

        # when/then
        with pytest.raises(RuntimeError, match="AEMET error 401"):
            await client.fetch(_STATION_ID, _START, _END)


async def test_given_http_503_when_fetching_then_raises_http_status_error(httpx2_mock: Router):
    # given
    httpx2_mock.get(url__regex=_ANTARTIDA_URL_RE).respond(status_code=503)

    async with httpx2.AsyncClient() as http:
        client = AemetClient(http, api_key=_API_KEY)

        # when/then
        with pytest.raises(httpx2.HTTPStatusError):
            await client.fetch(_STATION_ID, _START, _END)


async def test_given_invalid_observation_payload_when_fetching_then_raises_validation_error(
    httpx2_mock: Router,
):
    # given
    httpx2_mock.get(url__regex=_ANTARTIDA_URL_RE).respond(json=_hateoas())
    httpx2_mock.get(_DATA_URL).respond(json=[{"temp": -1.0}])

    async with httpx2.AsyncClient() as http:
        client = AemetClient(http, api_key=_API_KEY)

        # when/then
        with pytest.raises(ValidationError):
            await client.fetch(_STATION_ID, _START, _END)


_MAINLAND_ID = "3195"
_CONVENCIONAL_URL = f"https://opendata.aemet.es/opendata/api/observacion/convencional/datos/estacion/{_MAINLAND_ID}"
_CONV_DATA_URL = "https://opendata.aemet.es/opendata/api/observacion/convencional/data.json"


def _convencional_hateoas() -> dict[str, object]:
    return {
        "descripcion": "exito",
        "estado": 200,
        "datos": _CONV_DATA_URL,
        "metadatos": _META_URL,
    }


def _convencional_payload() -> list[dict[str, object]]:
    return [
        {
            "ubi": "MADRID, RETIRO",
            "fint": "2024-01-01T00:30:00+0000",
            "ta": 8.1,
            "pres": 940.0,
            "vv": 2.5,
        },
        {
            "ubi": "MADRID, RETIRO",
            "fint": "2024-01-01T02:00:00+0000",
            "ta": 7.0,
            "pres": 941.0,
            "vv": 1.0,
        },
    ]


async def test_given_mainland_station_when_fetching_then_uses_convencional_url_and_maps_fields(
    httpx2_mock: Router,
):
    # given
    route = httpx2_mock.get(_CONVENCIONAL_URL).respond(json=_convencional_hateoas())
    httpx2_mock.get(_CONV_DATA_URL).respond(json=_convencional_payload())

    # when
    async with httpx2.AsyncClient() as http:
        client = AemetClient(http, api_key=_API_KEY)
        rows = await client.fetch(_MAINLAND_ID, _START, _END)

    # then
    assert route.called
    assert len(rows) == 1
    assert rows[0].station.id == _MAINLAND_ID
    assert rows[0].station.name == "MADRID, RETIRO"
    assert rows[0].observed_at == datetime(2024, 1, 1, 0, 30, tzinfo=UTC)
    assert rows[0].temperature_c == 8.1
    assert rows[0].pressure_hpa == 940.0
    assert rows[0].speed_ms == 2.5
