# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""
Controller: Schedule CRUD endpoints.
Thin HTTP layer — delegates ALL logic to ScheduleService.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.oncall import (
    ScheduleCreateRequest,
    ScheduleUpdateRequest,
    ScheduleResponse,
)
from app.services.schedule_service import ScheduleService
from app.core.dependencies import get_schedule_service

router = APIRouter(prefix="/api/v1", tags=["Schedules"])


@router.post("/schedules", status_code=201, response_model=ScheduleResponse)
def create_schedule(
    payload: ScheduleCreateRequest,
    service: ScheduleService = Depends(get_schedule_service),
):
    """Create (or replace) an on-call schedule for a team."""
    try:
        return service.create_schedule(
            team=payload.team,
            rotation_type=payload.rotation_type,
            members=[m.model_dump() for m in payload.members],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/schedules")
def list_schedules(
    service: ScheduleService = Depends(get_schedule_service),
):
    """List all on-call schedules."""
    return service.list_schedules()


@router.get("/schedules/{team}", response_model=ScheduleResponse)
def get_schedule(
    team: str,
    service: ScheduleService = Depends(get_schedule_service),
):
    """Get a specific team's on-call schedule."""
    try:
        return service.get_schedule(team)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/schedules/{team}", response_model=ScheduleResponse)
def update_schedule(
    team: str,
    payload: ScheduleUpdateRequest,
    service: ScheduleService = Depends(get_schedule_service),
):
    """Partially update a team's schedule."""
    try:
        add_members = (
            [m.model_dump() for m in payload.add_members]
            if payload.add_members
            else None
        )
        return service.update_schedule(
            team=team,
            rotation_type=payload.rotation_type,
            add_members=add_members,
            remove_members=payload.remove_members,
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/schedules/{team}")
def delete_schedule(
    team: str,
    service: ScheduleService = Depends(get_schedule_service),
):
    """Delete a team's on-call schedule."""
    try:
        return service.delete_schedule(team)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
