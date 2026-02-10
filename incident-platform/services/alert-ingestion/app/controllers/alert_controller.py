# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""
Controller: Alert endpoints — ingest, get, list.
Thin HTTP layer — delegates ALL logic to AlertService.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from typing import Optional

from app.schemas import AlertIn, AlertOut, AlertDetail, PaginatedAlerts
from app.services.alert_service import AlertService
from app.core.dependencies import get_alert_service

router = APIRouter(prefix="/api/v1", tags=["Alerts"])


@router.post("/alerts", response_model=AlertOut, status_code=201,
             summary="Ingest a new alert",
             responses={201: {"description": "Alert accepted and correlated"}})
def create_alert(
    alert: AlertIn,
    request: Request,
    service: AlertService = Depends(get_alert_service),
):
    """Receive a new alert, correlate it to an existing or new incident."""
    try:
        result = service.process_alert(
            service_name=alert.service,
            severity=alert.severity,
            message=alert.message,
            source=alert.source,
            labels=alert.labels,
            timestamp=alert.timestamp,
        )
        return AlertOut(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database error while processing alert: {exc}")


@router.get("/alerts/{alert_id}", response_model=AlertDetail,
            summary="Get a single alert by ID")
def get_alert(
    alert_id: str,
    service: AlertService = Depends(get_alert_service),
):
    """Retrieve a specific alert by its UUID."""
    try:
        uuid.UUID(alert_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid alert ID format")

    result = service.get_alert(alert_id)
    if not result:
        raise HTTPException(status_code=404, detail="Alert not found")
    return AlertDetail(**result)


@router.get("/alerts", response_model=PaginatedAlerts,
            summary="List alerts with pagination and filters")
def list_alerts(
    service_filter: Optional[str] = Query(default=None, alias="service"),
    severity: Optional[str] = None,
    incident_id: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
    service: AlertService = Depends(get_alert_service),
):
    """Return alerts with optional filtering and pagination."""
    total, alerts = service.list_alerts(
        service=service_filter,
        severity=severity,
        incident_id=incident_id,
        page=page,
        per_page=per_page,
    )
    return PaginatedAlerts(
        total=total, page=page, per_page=per_page,
        alerts=[AlertDetail(**a) for a in alerts],
    )
