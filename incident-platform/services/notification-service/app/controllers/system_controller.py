# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""System endpoints — health, readiness, metrics."""
from fastapi import APIRouter
from fastapi.responses import JSONResponse, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from app.core.config import settings
from app.core.dependencies import get_notification_repo

router = APIRouter(tags=["System"])


@router.get("/health")
async def health_check():
    return {"status": "ok", "service": settings.SERVICE_NAME}


@router.get("/health/ready")
async def readiness_check():
    try:
        count = get_notification_repo().verify_connection()
        return {"status": "ok", "service": settings.SERVICE_NAME, "notifications_in_db": count}
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "service": settings.SERVICE_NAME, "detail": str(exc)},
        )


@router.get("/metrics")
async def prometheus_metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
