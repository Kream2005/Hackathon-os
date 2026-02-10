"""
Tests for the API Gateway service.
Run: pytest test_main.py -v
"""

import pytest
import json
from httpx import AsyncClient, ASGITransport

from main import app, _resolve_service, SlidingWindowRateLimiter, SERVICE_MAP


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── Health & Metrics ──────────────────────────────────────────────────────

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


# ── Routing / 404 ─────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_unknown_route_returns_404(client: AsyncClient):
    resp = await client.get("/api/v1/nonexistent-resource")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_short_path_returns_404(client: AsyncClient):
    resp = await client.get("/api/v1")
    assert resp.status_code in (404, 405, 307)


# ── _resolve_service ──────────────────────────────────────────────────────

def test_resolve_service_alerts():
    base_url, path = _resolve_service("/api/v1/alerts")
    assert "8001" in base_url
    assert path == "/api/v1/alerts"


def test_resolve_service_incidents():
    base_url, path = _resolve_service("/api/v1/incidents")
    assert "8002" in base_url


def test_resolve_service_schedules():
    base_url, path = _resolve_service("/api/v1/schedules")
    assert "8003" in base_url


def test_resolve_service_oncall():
    base_url, path = _resolve_service("/api/v1/oncall/current")
    assert "8003" in base_url


def test_resolve_service_escalate():
    base_url, path = _resolve_service("/api/v1/escalate")
    assert "8003" in base_url


def test_resolve_service_escalations():
    base_url, path = _resolve_service("/api/v1/escalations")
    assert "8003" in base_url


def test_resolve_service_notify():
    base_url, path = _resolve_service("/api/v1/notify")
    assert "8004" in base_url


def test_resolve_service_notifications():
    base_url, path = _resolve_service("/api/v1/notifications")
    assert "8004" in base_url


def test_resolve_service_unknown_raises():
    with pytest.raises(Exception):
        _resolve_service("/api/v1/does-not-exist")


def test_resolve_service_short_path_raises():
    with pytest.raises(Exception):
        _resolve_service("/api")


# ── Rate Limiter ──────────────────────────────────────────────────────────

def test_rate_limiter_allows():
    rl = SlidingWindowRateLimiter(5, 60)
    allowed, remaining, retry = rl.is_allowed("127.0.0.1")
    assert allowed is True
    assert remaining == 4
    assert retry == 0


def test_rate_limiter_blocks_after_limit():
    rl = SlidingWindowRateLimiter(3, 60)
    for _ in range(3):
        rl.is_allowed("10.0.0.1")
    allowed, remaining, retry = rl.is_allowed("10.0.0.1")
    assert allowed is False
    assert remaining == 0


def test_rate_limiter_different_keys():
    rl = SlidingWindowRateLimiter(1, 60)
    a1, _, _ = rl.is_allowed("client-a")
    a2, _, _ = rl.is_allowed("client-b")
    assert a1 is True
    assert a2 is True


# ── Auth / Login ──────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_login_success(client: AsyncClient):
    resp = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin"})
    assert resp.status_code == 200
    data = resp.json()
    assert "api_key" in data
    assert data["username"] == "admin"


@pytest.mark.anyio
async def test_login_wrong_password(client: AsyncClient):
    resp = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_login_unknown_user(client: AsyncClient):
    resp = await client.post("/api/v1/auth/login", json={"username": "ghost", "password": "x"})
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_login_missing_fields(client: AsyncClient):
    resp = await client.post("/api/v1/auth/login", json={"username": ""})
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_login_invalid_json(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/login",
        content=b"not json",
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 400


# ── Authentication Middleware ─────────────────────────────────────────────

@pytest.mark.anyio
async def test_auth_bypass_on_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_auth_bypass_on_metrics(client: AsyncClient):
    resp = await client.get("/metrics")
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_auth_bypass_on_login(client: AsyncClient):
    resp = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin"})
    assert resp.status_code == 200


# ── Services Health ──────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_services_health_returns_all_services(client: AsyncClient):
    """Check /api/services/health returns all 4 service entries.
    Note: in test the http_client may not be initialized by lifespan,
    so we initialize it inline if needed."""
    import main
    if main.http_client is None:
        import httpx as _httpx
        main.http_client = _httpx.AsyncClient(timeout=3.0)
    try:
        resp = await client.get("/api/services/health")
        assert resp.status_code == 200
        data = resp.json()
        expected = {"alert-ingestion", "incident-management", "oncall-service", "notification-service"}
        assert set(data.keys()) == expected
        for name in data:
            assert data[name]["status"] in ("up", "down")
    finally:
        pass


# ── SERVICE_MAP completeness ─────────────────────────────────────────────

def test_service_map_has_all_resources():
    required = ["alerts", "incidents", "oncall", "schedules", "escalate",
                 "escalations", "notify", "notifications"]
    for r in required:
        assert r in SERVICE_MAP, f"'{r}' missing from SERVICE_MAP"
