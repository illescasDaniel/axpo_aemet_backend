from datetime import datetime

from sqlalchemy import DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from meteo_service.shared.database import Base


class ObservationRow(Base):
    """Cached raw observation from AEMET (not aggregated)."""

    __tablename__ = "observations"

    station_id: Mapped[str] = mapped_column(String, primary_key=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)

    station_name: Mapped[str] = mapped_column(String)
    temperature_c: Mapped[float | None] = mapped_column(Float)
    pressure_hpa: Mapped[float | None] = mapped_column(Float)
    speed_ms: Mapped[float | None] = mapped_column(Float)
