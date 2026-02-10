# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""Pydantic request/response schemas."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator

VALID_SEVERITIES = ("critical", "high", "medium", "low")
VALID_STATUSES = ("open", "acknowledged", "in_progress", "resolved")

ALLOWED_TRANSITIONS = {
    "open":         {"acknowledged", "in_progress", "resolved"},
    "acknowledged": {"in_progress", "resolved"},
    "in_progress":  {"resolved"},
    "resolved":     set(),
}


class IncidentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    service: str = Field(..., min_length=1, max_length=255)
    severity: str
    assigned_to: Optional[str] = None

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


class IncidentUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = Field(None, max_length=5000)
    assigned_to: Optional[str] = None

    @field_validator("status")
    @classmethod
    def normalise_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.lower().strip()
            if v not in VALID_STATUSES:
                raise ValueError(f"status must be one of {VALID_STATUSES}")
        return v


class IncidentOut(BaseModel):
    id: str
    title: str
    service: str
    severity: str
    status: str
    assigned_to: Optional[str]
    alert_count: int
    created_at: str
    updated_at: str
    acknowledged_at: Optional[str]
    resolved_at: Optional[str]
    mtta_seconds: Optional[float]
    mttr_seconds: Optional[float]


class IncidentDetail(IncidentOut):
    alerts: List[Dict[str, Any]] = []
    notes: List[Dict[str, Any]] = []
    timeline: List[Dict[str, Any]] = []


class PaginatedIncidents(BaseModel):
    total: int
    page: int
    per_page: int
    incidents: List[IncidentOut]


class NoteCreate(BaseModel):
    author: str = "anonymous"
    content: str = Field(..., min_length=1)


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
