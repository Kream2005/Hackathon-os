# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""Controller: Notification endpoints — send, get, list, stats."""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.schemas import (
    NotifyRequest, NotifyResponse, NotificationDetail,
    PaginatedNotifications, NotificationStats,
)
from app.services.notification_service import NotificationService
from app.core.dependencies import get_notification_service

router = APIRouter(prefix="/api/v1", tags=["Notifications"])


@router.post("/notify", response_model=NotifyResponse, status_code=200)
async def notify(payload: NotifyRequest, request: Request,
                 service: NotificationService = Depends(get_notification_service)):
    result = await service.process_notification(
        incident_id=payload.incident_id, channel=payload.channel,
        recipient=payload.recipient, message=payload.message,
        severity=payload.severity, metadata=payload.metadata,
    )
    return NotifyResponse(
        id=result["id"], incident_id=result["incident_id"],
        channel=result["channel"], recipient=result["recipient"],
        message=result["message"], severity=result["severity"],
        status=result["status"], created_at=result["created_at"],
    )


@router.get("/notifications/stats/summary", response_model=NotificationStats)
async def get_stats(service: NotificationService = Depends(get_notification_service)):
    return service.get_stats()


@router.get("/notifications/{notification_id}", response_model=NotificationDetail)
async def get_notification(notification_id: str,
                           service: NotificationService = Depends(get_notification_service)):
    try:
        uuid.UUID(notification_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid notification ID format")
    result = service.get_notification(notification_id)
    if not result:
        raise HTTPException(status_code=404, detail="Notification not found")
    return NotificationDetail(**result)


@router.get("/notifications", response_model=PaginatedNotifications)
async def list_notifications(
    channel: Optional[str] = None,
    status: Optional[str] = None,
    incident_id: Optional[str] = None,
    recipient: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
    service: NotificationService = Depends(get_notification_service),
):
    total, notifications = service.list_notifications(
        channel, status, incident_id, recipient, page, per_page,
    )
    return PaginatedNotifications(
        total=total, page=page, per_page=per_page,
        notifications=[NotificationDetail(**n) for n in notifications],
    )
