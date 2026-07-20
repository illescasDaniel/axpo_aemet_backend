from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AemetHateoasResponse(BaseModel):
    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)

    description: str = Field(alias="descripcion")
    status: int = Field(alias="estado")
    data_url: str | None = Field(default=None, alias="datos")
    metadata_url: str | None = Field(default=None, alias="metadatos")


class AemetObservation(BaseModel):
    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)

    station_name: str = Field(alias="nombre")
    observed_at: datetime = Field(alias="fhora")
    temperature_c: float | None = Field(default=None, alias="temp")
    pressure_hpa: float | None = Field(default=None, alias="pres")
    speed_ms: float | None = Field(default=None, alias="vel")
