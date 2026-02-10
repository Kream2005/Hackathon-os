# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""HTTP Middleware — request ID propagation and Prometheus metrics."""
import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.metrics import REQUEST_COUNT, REQUEST_LATENCY, HTTP_ERRORS

SKIP_PATHS = ("/health", "/health/ready", "/metrics", "/openapi.json", "/docs", "/redoc")


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start
        path = request.url.path
        if path not in SKIP_PATHS:
            REQUEST_COUNT.labels(method=request.method, endpoint=path, status=str(response.status_code)).inc()
            REQUEST_LATENCY.labels(method=request.method, endpoint=path).observe(duration)
            if response.status_code >= 400:
                HTTP_ERRORS.labels(method=request.method, endpoint=path, status=str(response.status_code)).inc()
        return response
