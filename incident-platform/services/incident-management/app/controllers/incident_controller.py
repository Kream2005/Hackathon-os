# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""Controller: Incident CRUD, status transitions, notes, timeline, metrics, stats."""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.schemas import (
    IncidentCreate, IncidentUpdate, IncidentOut, IncidentDetail,
    PaginatedIncidents,
)
from app.services.incident_service import IncidentService
from app.core.dependencies import get_incident_service

router = APIRouter(prefix="/api/v1", tags=["Incidents"])


@router.post("/incidents", status_code=201, response_model=IncidentOut)
def create_incident(body: IncidentCreate,
                    service: IncidentService = Depends(get_incident_service)):
    try:
        result = service.create_incident(
            title=body.title, service=body.service,
            severity=body.severity, assigned_to=body.assigned_to,
        )
        return IncidentOut(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}")


@router.get("/incidents/stats/summary")
def get_summary_stats(service: IncidentService = Depends(get_incident_service)):
    return service.get_summary_stats()


@router.get("/incidents", response_model=PaginatedIncidents)
def list_incidents(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    service_filter: Optional[str] = Query(default=None, alias="service"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
    service: IncidentService = Depends(get_incident_service),
):
    total, incidents = service.list_incidents(status, severity, service_filter, page, per_page)
    return PaginatedIncidents(
        total=total, page=page, per_page=per_page,
        incidents=[IncidentOut(**i) for i in incidents],
    )


@router.get("/incidents/{incident_id}", response_model=IncidentDetail)
def get_incident(incident_id: str,
                 service: IncidentService = Depends(get_incident_service)):
    try:
        uuid.UUID(incident_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid incident ID format")
    result = service.get_incident_detail(incident_id)
    if not result:
        raise HTTPException(status_code=404, detail="Incident not found")
    return IncidentDetail(**result)


@router.patch("/incidents/{incident_id}", response_model=IncidentOut)
def update_incident(incident_id: str, body: IncidentUpdate,
                    service: IncidentService = Depends(get_incident_service)):
    try:
        uuid.UUID(incident_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid incident ID format")
    try:
        result = service.update_incident(
            incident_id, status=body.status,
            notes=body.notes, assigned_to=body.assigned_to,
        )
        return IncidentOut(**result)
    except KeyError:
        raise HTTPException(status_code=404, detail="Incident not found")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.get("/incidents/{incident_id}/metrics")
def get_incident_metrics(incident_id: str,
                         service: IncidentService = Depends(get_incident_service)):
    try:
        uuid.UUID(incident_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid incident ID format")
    result = service.get_incident_metrics(incident_id)
    if not result:
        raise HTTPException(status_code=404, detail="Incident not found")
    return result


@router.post("/incidents/{incident_id}/notes", status_code=201)
def add_incident_note(incident_id: str, body: dict,
                      service: IncidentService = Depends(get_incident_service)):
    try:
        uuid.UUID(incident_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid incident ID format")
    author = body.get("author", "anonymous")
    content = body.get("content", "")
    if not content or not content.strip():
        raise HTTPException(status_code=422, detail="Note content cannot be empty")
    try:
        return service.add_note(incident_id, author, content.strip())
    except KeyError:
        raise HTTPException(status_code=404, detail="Incident not found")


@router.get("/incidents/{incident_id}/timeline")
def get_incident_timeline(incident_id: str,
                          service: IncidentService = Depends(get_incident_service)):
    try:
        uuid.UUID(incident_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid incident ID format")
    try:
        return service.get_timeline(incident_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Incident not found")
