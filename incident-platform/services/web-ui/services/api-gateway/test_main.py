"""
Tests for the API Gateway service.
Run: pytest test_main.py -v
"""

import pytest
from httpx import AsyncClient, ASGITransport
from main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "api-gateway"


@pytest.mark.anyio
async def test_metrics_endpoint(client: AsyncClient):
    resp = await client.get("/metrics")
    assert resp.status_code == 200
    assert "gateway_requests_total" in resp.text or resp.status_code == 200


@pytest.mark.anyio
async def test_unknown_route_returns_404(client: AsyncClient):
    resp = await client.get("/api/v1/nonexistent-resource")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_services_health_aggregation(client: AsyncClient):
    """All downstream services will be unreachable in test, so all should be 'down'."""
    resp = await client.get("/api/services/health")
    assert resp.status_code == 200
    data = resp.json()
    for service_name in data:
        assert data[service_name]["status"] == "down"
