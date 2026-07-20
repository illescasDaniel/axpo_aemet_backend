from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field


router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"status": "ok"}]})

    status: str = Field(examples=["ok"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")
