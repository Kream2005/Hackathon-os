"""
API Gateway — FastAPI service (port 8080)
Proxies all requests to the backend microservices:
  - Alert Ingestion   (port 8001)
  - Incident Management (port 8002)
  - On-Call Service     (port 8003)
  - Notification Service (port 8004)
Also exposes /health and /metrics for Prometheus.
"""

import os
import time
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

# ---------------------------------------------------------------------------
# Config — service URLs (Docker service names by default)
# ---------------------------------------------------------------------------
ALERT_INGESTION_URL = os.getenv("ALERT_INGESTION_URL", "http://alert-ingestion:8001")
INCIDENT_MANAGEMENT_URL = os.getenv("INCIDENT_MANAGEMENT_URL", "http://incident-management:8002")
ONCALL_SERVICE_URL = os.getenv("ONCALL_SERVICE_URL", "http://oncall-service:8003")
NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification-service:8004")

# ---------------------------------------------------------------------------
# API Key Authentication
# ---------------------------------------------------------------------------
_raw_keys = os.getenv("API_KEYS", "")
API_KEYS: set[str] = {k.strip() for k in _raw_keys.split(",") if k.strip()}
AUTH_ENABLED = len(API_KEYS) > 0

# User credentials for the login page (username:password pairs)
# Format: "admin:admin123,operator:op456"
_raw_users = os.getenv("AUTH_USERS", "admin:admin,operator:operator")
USER_CREDENTIALS: dict[str, str] = {}
for pair in _raw_users.split(","):
    pair = pair.strip()
    if ":" in pair:
        u, p = pair.split(":", 1)
        USER_CREDENTIALS[u.strip()] = p.strip()

# The API key returned on successful login
LOGIN_API_KEY = os.getenv("LOGIN_API_KEY", list(API_KEYS)[0] if API_KEYS else "default-key")

# Paths that bypass authentication (monitoring / health probes / login)
AUTH_BYPASS_PATHS: set[str] = {"/health", "/metrics", "/api/services/health", "/api/v1/auth/login"}

SERVICE_MAP: dict[str, str] = {
    "alerts": ALERT_INGESTION_URL,
    "incidents": INCIDENT_MANAGEMENT_URL,
    "oncall": ONCALL_SERVICE_URL,
    "schedules": ONCALL_SERVICE_URL,
    "escalate": ONCALL_SERVICE_URL,
    "notify": NOTIFICATION_SERVICE_URL,
    "notifications": NOTIFICATION_SERVICE_URL,
}

# ---------------------------------------------------------------------------
# Prometheus metrics
# ---------------------------------------------------------------------------
GATEWAY_REQUESTS = Counter(
    "gateway_requests_total",
    "Total requests proxied through the gateway",
    ["method", "service", "status"],
)
GATEWAY_LATENCY = Histogram(
    "gateway_request_duration_seconds",
    "Latency of proxied requests",
    ["service"],
)

# ---------------------------------------------------------------------------
# Shared HTTP client
# ---------------------------------------------------------------------------
http_client: httpx.AsyncClient | None = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global http_client
    http_client = httpx.AsyncClient(timeout=10.0)
    yield
    await http_client.aclose()


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Incident Platform — API Gateway",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, lock this down
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# API Key Authentication Middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def api_key_auth(request: Request, call_next):
    """Enforce API key on all routes except health/metrics."""
    # Always allow preflight CORS requests, health probes, and login
    if (
        not AUTH_ENABLED
        or request.method == "OPTIONS"
        or request.url.path in AUTH_BYPASS_PATHS
    ):
        return await call_next(request)

    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return Response(
            content='{"detail":"Missing API key. Provide X-API-Key header."}',
            status_code=401,
            media_type="application/json",
        )
    if api_key not in API_KEYS:
        return Response(
            content='{"detail":"Invalid API key."}',
            status_code=403,
            media_type="application/json",
        )
    return await call_next(request)


# ---------------------------------------------------------------------------
# Health & Metrics
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "ok", "service": "api-gateway"}


@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ---------------------------------------------------------------------------
# Proxy helpers
# ---------------------------------------------------------------------------
def _resolve_service(path: str) -> tuple[str, str]:
    """
    Given /api/v1/<resource>/..., return (base_url, downstream_path).
    """
    # path looks like /api/v1/alerts, /api/v1/incidents/abc, etc.
    parts = path.strip("/").split("/")
    # parts = ["api", "v1", "alerts", ...]
    if len(parts) < 3:
        raise HTTPException(status_code=404, detail="Unknown route")

    resource = parts[2]  # "alerts", "incidents", "oncall", "schedules", "escalate", "notify"
    base_url = SERVICE_MAP.get(resource)
    if not base_url:
        raise HTTPException(status_code=404, detail=f"No service registered for '{resource}'")

    return base_url, path


async def _proxy(request: Request, service_label: str, base_url: str, downstream_path: str) -> Response:
    """
    Forward the request to the downstream service and return its response.
    """
    assert http_client is not None
    url = f"{base_url}{downstream_path}"

    # Read body (may be empty for GET/DELETE)
    body = await request.body()

    headers = dict(request.headers)
    # Remove hop-by-hop headers
    for h in ("host", "content-length", "transfer-encoding"):
        headers.pop(h, None)

    start = time.monotonic()
    try:
        resp = await http_client.request(
            method=request.method,
            url=url,
            content=body if body else None,
            headers=headers,
            params=dict(request.query_params),
        )
        duration = time.monotonic() - start
        GATEWAY_REQUESTS.labels(method=request.method, service=service_label, status=resp.status_code).inc()
        GATEWAY_LATENCY.labels(service=service_label).observe(duration)

        return Response(
            content=resp.content,
            status_code=resp.status_code,
            headers=dict(resp.headers),
            media_type=resp.headers.get("content-type"),
        )
    except httpx.RequestError as exc:
        GATEWAY_REQUESTS.labels(method=request.method, service=service_label, status=502).inc()
        raise HTTPException(status_code=502, detail=f"Upstream service unreachable: {exc}")


# ---------------------------------------------------------------------------
# Auth endpoint — login
# ---------------------------------------------------------------------------
@app.post("/api/v1/auth/login")
async def login(request: Request):
    """Validate username/password and return an API key."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    username = body.get("username", "").strip()
    password = body.get("password", "")

    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password required")

    expected = USER_CREDENTIALS.get(username)
    if expected is None or expected != password:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    return {
        "api_key": LOGIN_API_KEY,
        "username": username,
        "message": "Login successful",
    }


# ---------------------------------------------------------------------------
# Catch-all proxy route — matches /api/v1/**
# ---------------------------------------------------------------------------
@app.api_route("/api/v1/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_api(request: Request, path: str):
    full_path = f"/api/v1/{path}"
    base_url, downstream_path = _resolve_service(full_path)
    resource = path.split("/")[0]
    return await _proxy(request, resource, base_url, downstream_path)


# ---------------------------------------------------------------------------
# Proxy health endpoints for individual services (optional convenience)
# ---------------------------------------------------------------------------
@app.get("/api/services/health")
async def all_services_health():
    """Hit /health on every backend and aggregate the results."""
    assert http_client is not None
    results: dict[str, object] = {}
    for name, url in [
        ("alert-ingestion", ALERT_INGESTION_URL),
        ("incident-management", INCIDENT_MANAGEMENT_URL),
        ("oncall-service", ONCALL_SERVICE_URL),
        ("notification-service", NOTIFICATION_SERVICE_URL),
    ]:
        try:
            r = await http_client.get(f"{url}/health", timeout=3.0)
            results[name] = {"status": "up", "code": r.status_code}
        except httpx.RequestError:
            results[name] = {"status": "down"}
    return results
