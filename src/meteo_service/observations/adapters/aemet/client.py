import logging
from datetime import datetime

from httpx2 import AsyncClient
from pydantic import TypeAdapter

from meteo_service.observations.adapters.aemet.mappers import to_observations
from meteo_service.observations.adapters.aemet.schemas import (
    AemetConvencionalObservation,
    AemetHateoasResponse,
    AemetObservation,
)
from meteo_service.observations.adapters.aemet.station_timezones import is_antarctic_station
from meteo_service.observations.domain.observation import Observation


logger = logging.getLogger(__name__)

_AEMET_DT = "%Y-%m-%dT%H:%M:%SUTC"
_AEMET_SUCCESS_STATUS = 200
_AEMET_NO_DATA_STATUS = 404
_BASE = "https://opendata.aemet.es/opendata/api"


class AemetClient:
    def __init__(self, client: AsyncClient, api_key: str):
        self._client = client
        self._api_key = api_key

    async def fetch(
        self,
        station_id: str,
        start: datetime,
        end: datetime,
    ) -> list[Observation]:
        """
        Antarctic stations → Antartida product (date range, ~10 min).
        Other stations → observación convencional (last ~24h; filtered by start/end).

        Callers (use case) must pass UTC datetimes.
        """
        headers = {"accept": "application/json", "api_key": self._api_key}
        if is_antarctic_station(station_id):
            start_s = start.strftime(_AEMET_DT)
            end_s = end.strftime(_AEMET_DT)
            url = f"{_BASE}/antartida/datos/fechaini/{start_s}/fechafin/{end_s}/estacion/{station_id}"
            payload = await self._fetch_datos(url, headers)
            if payload is None:
                return []
            rows = TypeAdapter(list[AemetObservation]).validate_json(payload)
            return to_observations(rows, station_id)

        url = f"{_BASE}/observacion/convencional/datos/estacion/{station_id}"
        payload = await self._fetch_datos(url, headers)
        if payload is None:
            return []
        rows = TypeAdapter(list[AemetConvencionalObservation]).validate_json(payload)
        return [o for o in to_observations(rows, station_id) if start <= o.observed_at <= end]

    async def _fetch_datos(self, url: str, headers: dict[str, str]) -> bytes | None:
        logger.info("AEMET request url=%s", url)
        response = await self._client.get(url, headers=headers)
        response.raise_for_status()
        hateoas = AemetHateoasResponse.model_validate_json(response.content)
        logger.info("AEMET HATEOAS: %s", hateoas)
        if hateoas.status == _AEMET_NO_DATA_STATUS:
            logger.info("AEMET no data for selection: %s", hateoas.description)
            return None
        if hateoas.status != _AEMET_SUCCESS_STATUS:
            raise RuntimeError(f"AEMET error {hateoas.status}: {hateoas.description}")
        if hateoas.data_url is None:
            raise RuntimeError("AEMET success response missing data_url")

        data_response = await self._client.get(hateoas.data_url, headers=headers)
        data_response.raise_for_status()
        logger.info("AEMET datos bytes=%d", len(data_response.content))
        return data_response.content
