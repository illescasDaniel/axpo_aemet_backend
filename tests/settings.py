from meteo_service.shared.config import Settings


TEST_SETTINGS = Settings(
    aemet_api_key="test-aemet-key",
    database_url="sqlite+aiosqlite:///:memory:",
)
