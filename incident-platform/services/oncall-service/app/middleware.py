# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""
HTTP Middleware — request ID propagation and Prometheus metrics.
Separated from main.py for clean architecture.
"""

import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.metrics.prometheus import REQUEST_COUNT, REQUEST_LATENCY, HTTP_ERRORS

KNOWN_SEGMENTS: set[str] = {
    "api", "v1", "schedules", "oncall", "current", "override",
    "overrides", "escalate", "escalations", "teams", "health",
    "metrics", "history", "stats", "ready",
}

SKIP_PATHS: tuple[str, ...] = (
    "/health", "/health/ready", "/metrics", "/openapi.json", "/docs", "/redoc",
)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Propagate or generate X-Request-ID for distributed tracing."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    """Track request count, latency, and error rate via Prometheus."""

    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start

        path = request.url.path
        parts = path.strip("/").split("/")
        normalized = (
            "/"
            + "/".join(p if p in KNOWN_SEGMENTS else "{param}" for p in parts)
            if parts != [""]
            else path
        )

        if path not in SKIP_PATHS:
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=normalized,
                status=str(response.status_code),
            ).inc()
            REQUEST_LATENCY.labels(
                method=request.method,
                endpoint=normalized,
            ).observe(duration)
            if response.status_code >= 400:
                HTTP_ERRORS.labels(
                    method=request.method,
                    endpoint=normalized,
                    status=str(response.status_code),
                ).inc()

        return response
