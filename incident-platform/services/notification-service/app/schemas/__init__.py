# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""Pydantic request/response schemas."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator

VALID_CHANNELS = ("mock", "webhook", "email", "slack")


class NotifyRequest(BaseModel):
    incident_id: str = Field(..., min_length=1, max_length=255)
    channel: str = Field(default="mock", max_length=50)
    recipient: str = Field(..., min_length=1, max_length=500)
    message: str = Field(..., min_length=1, max_length=5000)
    severity: Optional[str] = Field(default=None, max_length=20)
    metadata: Optional[Dict[str, Any]] = Field(default=None)

    @field_validator("channel")
    @classmethod
    def normalise_channel(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in VALID_CHANNELS:
            raise ValueError(f"channel must be one of {VALID_CHANNELS}")
        return v

    @field_validator("recipient")
    @classmethod
    def normalise_recipient(cls, v: str) -> str:
        return v.strip()


class NotifyResponse(BaseModel):
    id: str
    incident_id: str
    channel: str
    recipient: str
    message: str
    severity: Optional[str] = None
    status: str
    created_at: str


class NotificationDetail(NotifyResponse):
    metadata: Optional[Dict[str, Any]] = None


class PaginatedNotifications(BaseModel):
    total: int
    page: int
    per_page: int
    notifications: List[NotificationDetail]


class NotificationStats(BaseModel):
    total: int
    sent: int
    failed: int
    by_channel: Dict[str, int]
    by_severity: Dict[str, int]


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    request_id: Optional[str] = None
