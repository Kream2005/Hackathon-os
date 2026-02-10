# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""System endpoints — health, metrics."""
from fastapi import APIRouter
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
from app.core.config import settings

router = APIRouter(tags=["System"])


@router.get("/health")
async def health_check():
    return {"status": "ok", "service": settings.SERVICE_NAME}


@router.get("/metrics")
async def prometheus_metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
