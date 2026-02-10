# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""
Controller: System endpoints — health, readiness, metrics.
Pure HTTP layer — no business logic.
"""

from datetime import datetime, timezone

from fastapi import APIRouter
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

from app.core.config import settings
from app.core.dependencies import get_schedule_repo, get_override_repo

router = APIRouter(tags=["System"])


@router.get("/health")
def health_check():
    """Liveness probe for Docker and orchestration."""
    schedule_repo = get_schedule_repo()
    override_repo = get_override_repo()
    return {
        "status": "ok",
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "schedules_count": schedule_repo.count(),
        "active_overrides": override_repo.count(),
    }


@router.get("/health/ready")
def readiness_check():
    """Readiness probe — verifies the service can serve traffic."""
    schedule_repo = get_schedule_repo()
    return {
        "status": "ready",
        "service": settings.SERVICE_NAME,
        "schedules_loaded": schedule_repo.count() > 0,
    }


@router.get("/metrics")
def prometheus_metrics():
    """Expose Prometheus metrics in OpenMetrics format."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
