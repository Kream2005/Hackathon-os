# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""HTTP Middleware — API key auth and rate limiting."""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.metrics import GATEWAY_RATE_LIMITED
from app.services.rate_limiter import SlidingWindowRateLimiter

_rate_limiter = SlidingWindowRateLimiter(settings.RATE_LIMIT_RPM, 60)


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if (
            not settings.AUTH_ENABLED
            or request.method == "OPTIONS"
            or request.url.path in settings.AUTH_BYPASS_PATHS
        ):
            return await call_next(request)
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return Response(
                content='{"detail":"Missing API key. Provide X-API-Key header."}',
                status_code=401, media_type="application/json",
            )
        if api_key not in settings.API_KEYS:
            return Response(
                content='{"detail":"Invalid API key."}',
                status_code=403, media_type="application/json",
            )
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if (
            not settings.RATE_LIMIT_ENABLED
            or request.method == "OPTIONS"
            or request.url.path in settings.RATE_LIMIT_BYPASS
        ):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        allowed, remaining, retry_after = _rate_limiter.is_allowed(client_ip)

        if not allowed:
            GATEWAY_RATE_LIMITED.labels(client_ip=client_ip).inc()
            return Response(
                content='{"detail":"Rate limit exceeded. Try again later."}',
                status_code=429, media_type="application/json",
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(settings.RATE_LIMIT_RPM),
                    "X-RateLimit-Remaining": "0",
                },
            )
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(settings.RATE_LIMIT_RPM)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
