from typing import AsyncGenerator

import pytest
from httpx2 import ASGITransport, AsyncClient
from tests.settings import TEST_SETTINGS

from meteo_service.shared.adapters.api.app import create_app


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    app = create_app(TEST_SETTINGS)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


async def test_health_returns_ok(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
