from typing import Annotated

import httpx2
from fastapi import APIRouter, Depends, HTTPException, Query

from meteo_service.observations.adapters.api.dependencies import get_observations_use_case
from meteo_service.observations.adapters.api.mappers import to_observation_response
from meteo_service.observations.adapters.api.schemas import GetObservationsQuery, ObservationResponse
from meteo_service.observations.application.get_observations import GetObservations


router = APIRouter(tags=["Observations"])


@router.get("/observations")
async def get_observations(
    query: Annotated[GetObservationsQuery, Query()],
    use_case: Annotated[GetObservations, Depends(get_observations_use_case)],
) -> list[ObservationResponse]:
    try:
        rows = await use_case.execute(
            station_id=query.station_id,
            start=query.start,
            end=query.end,
            station_location=query.resolved_station_location(),
            location=query.location,
            time_aggregation=query.time_aggregation,
            data_fields=query.data_fields,
        )
    except (RuntimeError, httpx2.HTTPError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return [to_observation_response(row) for row in rows]
