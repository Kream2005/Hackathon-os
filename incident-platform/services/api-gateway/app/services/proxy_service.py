# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""Proxy service — forwards requests to upstream microservices with retry."""
import asyncio
import time

import httpx
from fastapi import HTTPException, Request, Response

from app.core.config import settings
from app.metrics import GATEWAY_REQUESTS, GATEWAY_LATENCY, GATEWAY_RETRIES


class ProxyService:
    def __init__(self, http_client: httpx.AsyncClient):
        self._client = http_client

    def resolve_service(self, path: str) -> tuple[str, str]:
        parts = path.strip("/").split("/")
        if len(parts) < 3:
            raise HTTPException(status_code=404, detail="Unknown route")
        resource = parts[2]
        base_url = settings.SERVICE_MAP.get(resource)
        if not base_url:
            raise HTTPException(status_code=404, detail=f"No service registered for '{resource}'")
        return base_url, path

    async def proxy(self, request: Request, service_label: str,
                    base_url: str, downstream_path: str) -> Response:
        url = f"{base_url}{downstream_path}"
        body = await request.body()
        headers = dict(request.headers)
        for h in ("host", "content-length", "transfer-encoding"):
            headers.pop(h, None)

        is_retryable = request.method in settings.RETRY_SAFE_METHODS
        max_attempts = (1 + settings.RETRY_MAX_ATTEMPTS) if is_retryable else 1
        last_exc = None

        for attempt in range(1, max_attempts + 1):
            start = time.monotonic()
            try:
                resp = await self._client.request(
                    method=request.method, url=url,
                    content=body if body else None,
                    headers=headers, params=dict(request.query_params),
                )
                duration = time.monotonic() - start
                GATEWAY_REQUESTS.labels(method=request.method, service=service_label, status=resp.status_code).inc()
                GATEWAY_LATENCY.labels(service=service_label).observe(duration)

                if resp.status_code in (502, 503, 504) and attempt < max_attempts:
                    GATEWAY_RETRIES.labels(service=service_label, attempt=str(attempt)).inc()
                    await asyncio.sleep(settings.RETRY_BACKOFF_BASE * (2 ** (attempt - 1)))
                    continue

                return Response(
                    content=resp.content, status_code=resp.status_code,
                    headers=dict(resp.headers),
                    media_type=resp.headers.get("content-type"),
                )
            except httpx.RequestError as exc:
                last_exc = exc
                if attempt < max_attempts:
                    GATEWAY_RETRIES.labels(service=service_label, attempt=str(attempt)).inc()
                    await asyncio.sleep(settings.RETRY_BACKOFF_BASE * (2 ** (attempt - 1)))
                    continue

        GATEWAY_REQUESTS.labels(method=request.method, service=service_label, status=502).inc()
        raise HTTPException(status_code=502, detail=f"Upstream service unreachable after {max_attempts} attempts: {last_exc}")
