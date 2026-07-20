import pytest
from httpx2 import ASGITransport, AsyncClient

from meteo_service.shared.adapters.api.app import create_app
from meteo_service.shared.config import Settings


ALLOWED_ORIGIN = "http://localhost:3000"
OTHER_ORIGIN = "http://evil.example"


def _settings(*, cors_origins: list[str]) -> Settings:
    return Settings(
        aemet_api_key="test-key",
        database_url="sqlite+aiosqlite:///:memory:",
        cors_origins=cors_origins,
    )


@pytest.fixture
async def cors_client():
    app = create_app(_settings(cors_origins=[ALLOWED_ORIGIN]))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


async def test_given_allowed_origin_when_get_health_then_allow_origin_header(cors_client: AsyncClient):
    response = await cors_client.get("/health", headers={"Origin": ALLOWED_ORIGIN})

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN


async def test_given_disallowed_origin_when_get_health_then_no_allow_origin(cors_client: AsyncClient):
    response = await cors_client.get("/health", headers={"Origin": OTHER_ORIGIN})

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") is None


async def test_given_allowed_origin_when_options_preflight_then_cors_headers(cors_client: AsyncClient):
    response = await cors_client.options(
        "/api/v1/observations",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code in {200, 204}
    assert response.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN
    allow_methods = response.headers.get("access-control-allow-methods", "")
    assert "GET" in allow_methods.upper()


async def test_given_empty_cors_origins_when_get_with_origin_then_no_allow_origin():
    app = create_app(_settings(cors_origins=[]))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/health", headers={"Origin": ALLOWED_ORIGIN})

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") is None
