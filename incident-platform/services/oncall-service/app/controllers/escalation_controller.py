# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""
Controller: Escalation endpoints.
Thin HTTP layer — delegates ALL logic to EscalationService.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.schemas.oncall import EscalationCreateRequest, EscalationResponse
from app.services.escalation_service import EscalationService
from app.core.dependencies import get_escalation_service

router = APIRouter(prefix="/api/v1", tags=["Escalation"])


@router.post("/escalate", response_model=EscalationResponse)
def escalate(
    payload: EscalationCreateRequest,
    service: EscalationService = Depends(get_escalation_service),
):
    """Trigger an escalation — notifies the secondary on-call if available."""
    return service.escalate(
        team=payload.team,
        incident_id=payload.incident_id,
        reason=payload.reason,
    )


@router.get("/escalations")
def list_escalations(
    team: Optional[str] = None,
    limit: int = Query(default=None, ge=1, description="Max results"),
    service: EscalationService = Depends(get_escalation_service),
):
    """List escalation history, optionally filtered by team."""
    return service.list_escalations(team=team, limit=limit)
