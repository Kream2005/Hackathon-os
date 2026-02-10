# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""
Pydantic schemas — API request/response contracts.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator

VALID_SEVERITIES = ("critical", "high", "medium", "low")


class AlertIn(BaseModel):
    """Inbound alert payload."""
    service: str = Field(..., min_length=1, max_length=255, examples=["frontend-api"])
    severity: str = Field(..., examples=["high"])
    message: str = Field(..., min_length=1, max_length=2000, examples=["HTTP 5xx rate > 10 %"])
    labels: Dict[str, Any] = Field(default_factory=dict)
    source: str = Field(default="api", max_length=255)
    timestamp: Optional[str] = None

    @field_validator("severity")
    @classmethod
    def normalise_severity(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in VALID_SEVERITIES:
            raise ValueError(f"severity must be one of {VALID_SEVERITIES}")
        return v

    @field_validator("service")
    @classmethod
    def normalise_service(cls, v: str) -> str:
        return v.strip().lower()


class AlertOut(BaseModel):
    """Response after ingesting an alert."""
    alert_id: str
    incident_id: Optional[str] = None
    fingerprint: str
    status: str
    action: str


class AlertDetail(BaseModel):
    id: str
    service: str
    severity: str
    message: str
    source: str
    labels: Dict[str, Any]
    fingerprint: Optional[str]
    timestamp: Optional[str]
    incident_id: Optional[str]
    created_at: str


class PaginatedAlerts(BaseModel):
    total: int
    page: int
    per_page: int
    alerts: List[AlertDetail]


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    request_id: Optional[str] = None
