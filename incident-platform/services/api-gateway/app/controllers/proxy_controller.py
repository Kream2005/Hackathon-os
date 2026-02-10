# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""Controller: Catch-all proxy route and service health aggregation."""
import httpx
from fastapi import APIRouter, Request
from app.core.config import settings

router = APIRouter(tags=["Proxy"])


@router.api_route("/api/v1/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_api(request: Request, path: str):
    from app.core.dependencies import get_proxy_service
    proxy = get_proxy_service()
    full_path = f"/api/v1/{path}"
    base_url, downstream_path = proxy.resolve_service(full_path)
    resource = path.split("/")[0]
    return await proxy.proxy(request, resource, base_url, downstream_path)


@router.get("/api/services/health")
async def all_services_health():
    from app.core.dependencies import get_http_client
    client = get_http_client()
    results = {}
    for name, url in [
        ("alert-ingestion", settings.ALERT_INGESTION_URL),
        ("incident-management", settings.INCIDENT_MANAGEMENT_URL),
        ("oncall-service", settings.ONCALL_SERVICE_URL),
        ("notification-service", settings.NOTIFICATION_SERVICE_URL),
    ]:
        try:
            r = await client.get(f"{url}/health", timeout=3.0)
            results[name] = {"status": "up", "code": r.status_code}
        except httpx.RequestError:
            results[name] = {"status": "down"}
    return results
