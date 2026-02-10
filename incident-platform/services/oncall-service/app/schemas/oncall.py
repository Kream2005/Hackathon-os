# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""
Request / Response schemas — API contract definitions.
These are Pydantic models used ONLY at the controller (HTTP) boundary.
"""

from pydantic import BaseModel, Field
from typing import Optional
from app.models.domain import Member


# ── Schedule Schemas ──

class ScheduleCreateRequest(BaseModel):
    team: str = Field(..., min_length=1, max_length=255, description="Team name")
    rotation_type: str = Field(
        default="weekly",
        pattern="^(weekly|daily|biweekly)$",
        description="Rotation type",
    )
    members: list[Member] = Field(
        ..., min_length=1, description="List of on-call members"
    )


class ScheduleUpdateRequest(BaseModel):
    """Partial update model for PATCH /api/v1/schedules/{team}."""
    rotation_type: Optional[str] = Field(
        default=None,
        pattern="^(weekly|daily|biweekly)$",
        description="New rotation type",
    )
    add_members: Optional[list[Member]] = Field(
        default=None, description="Members to add"
    )
    remove_members: Optional[list[str]] = Field(
        default=None, description="Member names to remove"
    )


class ScheduleResponse(BaseModel):
    id: str
    team: str
    rotation_type: str
    members: list[dict]
    created_at: str
    updated_at: Optional[str] = None


# ── On-Call Schemas ──

class OnCallCurrentResponse(BaseModel):
    team: str
    primary: dict
    secondary: Optional[dict] = None
    schedule_id: str
    rotation_type: str


# ── Override Schemas ──

class OverrideCreateRequest(BaseModel):
    team: str = Field(..., min_length=1)
    user_name: str = Field(..., min_length=1)
    user_email: str = Field(..., min_length=1)
    reason: Optional[str] = "Manual override"
    duration_hours: Optional[int] = Field(
        default=None,
        ge=1,
        le=168,
        description="Override duration in hours (1-168)",
    )


# ── Escalation Schemas ──

class EscalationCreateRequest(BaseModel):
    team: str = Field(..., min_length=1)
    incident_id: str = Field(..., min_length=1)
    reason: Optional[str] = "No acknowledgment within SLA"


class EscalationResponse(BaseModel):
    status: str
    escalation_id: str
    team: str
    incident_id: str
    escalated_to: Optional[dict] = None
    message: str
    timestamp: str
