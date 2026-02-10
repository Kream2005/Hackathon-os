# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""System endpoints — health, readiness, metrics."""
from fastapi import APIRouter, HTTPException
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
from app.core.config import settings
from app.core.dependencies import get_incident_repo

router = APIRouter(tags=["System"])


@router.get("/health")
def health_check():
    return {"status": "ok", "service": settings.SERVICE_NAME}


@router.get("/health/ready")
def readiness_check():
    try:
        get_incident_repo().verify_connection()
        return {"status": "ok", "database": "connected"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}")


@router.get("/metrics")
def prometheus_metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
