# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""
Controller: System endpoints — health, readiness, metrics.
Pure HTTP layer — no business logic.
"""

from fastapi import APIRouter, HTTPException
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

from app.core.config import settings
from app.core.dependencies import get_alert_repo

router = APIRouter(tags=["System"])


@router.get("/health")
def health_check():
    """Shallow health check — confirms the process is alive."""
    return {"status": "ok", "service": settings.SERVICE_NAME}


@router.get("/health/ready")
def readiness_check():
    """Deep health check — confirms DB connectivity."""
    try:
        get_alert_repo().verify_connection()
        return {"status": "ok", "database": "connected"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}")


@router.get("/metrics")
def prometheus_metrics():
    """Expose Prometheus metrics in OpenMetrics format."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
