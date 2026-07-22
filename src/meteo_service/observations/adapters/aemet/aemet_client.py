import logging
from datetime import datetime

from httpx2 import AsyncClient
from pydantic import TypeAdapter

from meteo_service.observations.adapters.aemet.mappers import to_observations
from meteo_service.observations.adapters.aemet.schemas import AemetHateoasResponse, AemetObservation
from meteo_service.observations.domain.observation import Observation


logger = logging.getLogger(__name__)

_AEMET_DT = "%Y-%m-%dT%H:%M:%SUTC"
_AEMET_SUCCESS_STATUS = 200
_AEMET_NO_DATA_STATUS = 404


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
        API Spec: https://opendata.aemet.es/dist/index.html?#/antartida

        Callers (use case) must pass UTC datetimes.
        """
        start_s = start.strftime(_AEMET_DT)
        end_s = end.strftime(_AEMET_DT)
        headers = {"accept": "application/json", "api_key": self._api_key}
        url = (
            "https://opendata.aemet.es/opendata/api/antartida/datos/"
            f"fechaini/{start_s}/fechafin/{end_s}/estacion/{station_id}"
        )
        logger.info("AEMET request url=%s", url)

        response = await self._client.get(url, headers=headers)
        response.raise_for_status()
        hateoas = AemetHateoasResponse.model_validate_json(response.content)
        logger.info("AEMET HATEOAS: %s", hateoas)
        if hateoas.status == _AEMET_NO_DATA_STATUS:
            logger.info("AEMET no data for selection: %s", hateoas.description)
            return []
        if hateoas.status != _AEMET_SUCCESS_STATUS:
            raise RuntimeError(f"AEMET error {hateoas.status}: {hateoas.description}")
        if hateoas.data_url is None:
            raise RuntimeError("AEMET success response missing data_url")

        data_response = await self._client.get(hateoas.data_url, headers=headers)
        data_response.raise_for_status()
        rows = TypeAdapter(list[AemetObservation]).validate_json(data_response.content)
        logger.info("AEMET observations (%d), first: %s", len(rows), rows[0] if len(rows) > 0 else "None")
        return to_observations(rows, station_id)
