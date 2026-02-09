"""
Tests for the Notification Service.
Run: pytest test_main.py -v
"""

import pytest
from httpx import AsyncClient, ASGITransport
from main import app, notification_log


@pytest.fixture
async def client():
    notification_log.clear()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "notification-service"


@pytest.mark.anyio
async def test_metrics_endpoint(client: AsyncClient):
    resp = await client.get("/metrics")
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_send_notification_mock(client: AsyncClient):
    payload = {
        "incident_id": "incident-001",
        "channel": "mock",
        "recipient": "alice@example.com",
        "message": "CRITICAL: Server on fire",
    }
    resp = await client.post("/api/v1/notify", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "sent"
    assert data["incident_id"] == "incident-001"
    assert data["recipient"] == "alice@example.com"
    assert data["channel"] == "mock"


@pytest.mark.anyio
async def test_send_notification_email_channel(client: AsyncClient):
    payload = {
        "incident_id": "incident-002",
        "channel": "email",
        "recipient": "bob@example.com",
        "message": "HIGH: Payment service degraded",
    }
    resp = await client.post("/api/v1/notify", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "sent"
    assert data["channel"] == "email"


@pytest.mark.anyio
async def test_send_notification_slack_channel(client: AsyncClient):
    payload = {
        "incident_id": "incident-003",
        "channel": "slack",
        "recipient": "#alerts",
        "message": "MEDIUM: Auth login failures",
    }
    resp = await client.post("/api/v1/notify", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["channel"] == "slack"


@pytest.mark.anyio
async def test_list_notifications(client: AsyncClient):
    # Send two notifications
    for i in range(2):
        await client.post("/api/v1/notify", json={
            "incident_id": f"incident-{i}",
            "channel": "mock",
            "recipient": "test@example.com",
            "message": f"Test notification {i}",
        })

    resp = await client.get("/api/v1/notifications")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


@pytest.mark.anyio
async def test_invalid_payload_returns_422(client: AsyncClient):
    resp = await client.post("/api/v1/notify", json={"bad": "data"})
    assert resp.status_code == 422
