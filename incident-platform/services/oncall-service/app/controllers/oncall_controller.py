# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""
Controller: On-Call current, overrides, history, teams, stats endpoints.
Thin HTTP layer — delegates ALL logic to OnCallService / ScheduleService.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.schemas.oncall import OnCallCurrentResponse, OverrideCreateRequest
from app.services.oncall_service import OnCallService
from app.services.schedule_service import ScheduleService
from app.services.escalation_service import EscalationService
from app.core.dependencies import (
    get_oncall_service,
    get_schedule_service,
    get_escalation_service,
    get_history_repo,
)
from app.repositories.history_repository import HistoryRepository

router = APIRouter(prefix="/api/v1", tags=["On-Call"])


# ── On-Call Current ──

@router.get("/oncall/current", response_model=OnCallCurrentResponse)
def get_current_oncall(
    team: str = Query(..., description="Team name to query"),
    service: OnCallService = Depends(get_oncall_service),
):
    """Get the current on-call engineer for a team."""
    try:
        return service.get_current_oncall(team)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Override Endpoints ──

@router.post("/oncall/override")
def set_override(
    payload: OverrideCreateRequest,
    service: OnCallService = Depends(get_oncall_service),
):
    """Temporarily override the on-call for a team."""
    try:
        return service.set_override(
            team=payload.team,
            user_name=payload.user_name,
            user_email=payload.user_email,
            reason=payload.reason,
            duration_hours=payload.duration_hours,
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/oncall/override/{team}")
def remove_override(
    team: str,
    service: OnCallService = Depends(get_oncall_service),
):
    """Remove an active override for a team."""
    try:
        return service.remove_override(team)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/oncall/overrides")
def list_active_overrides(
    service: OnCallService = Depends(get_oncall_service),
):
    """List all currently active (non-expired) overrides."""
    return service.list_active_overrides()


# ── History ──

@router.get("/oncall/history")
def get_oncall_history(
    team: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = Query(default=None, ge=1, description="Max results"),
    history_repo: HistoryRepository = Depends(get_history_repo),
):
    """Audit log for all on-call events."""
    return history_repo.get_all(team=team, event_type=event_type, limit=limit)


# ── Teams ──

@router.get("/teams")
def list_teams(
    service: ScheduleService = Depends(get_schedule_service),
    oncall_service: OnCallService = Depends(get_oncall_service),
):
    """List all teams with their on-call schedule summaries."""
    oncall_service.cleanup_expired_overrides()
    return service.list_teams()


# ── Stats ──

@router.get("/oncall/stats")
def get_oncall_stats(
    service: ScheduleService = Depends(get_schedule_service),
    oncall_service: OnCallService = Depends(get_oncall_service),
    escalation_service: EscalationService = Depends(get_escalation_service),
):
    """Aggregated operational statistics."""
    oncall_service.cleanup_expired_overrides()
    stats = service.get_stats()
    stats["total_escalations"] = escalation_service.get_escalation_count()
    return stats
