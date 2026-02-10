# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""Business logic for the incident lifecycle."""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.core.logging import get_logger
from app.metrics import INCIDENTS_CREATED, INCIDENTS_TOTAL, INCIDENT_MTTA, INCIDENT_MTTR
from app.repositories.incident_repository import IncidentRepository
from app.schemas import ALLOWED_TRANSITIONS, VALID_STATUSES

logger = get_logger(__name__)


class IncidentService:
    def __init__(self, repo: IncidentRepository, oncall_client, notification_client):
        self._repo = repo
        self._oncall = oncall_client
        self._notification = notification_client

    def seed_gauges(self):
        for status in VALID_STATUSES:
            cnt = self._repo.count_by_status(status)
            INCIDENTS_TOTAL.labels(status=status).set(cnt)
        logger.info("Prometheus gauges loaded from DB")

    def create_incident(self, title: str, service: str, severity: str,
                        assigned_to: Optional[str] = None) -> Dict[str, Any]:
        incident_id = str(uuid.uuid4())
        if not assigned_to:
            oncall_data = self._oncall.get_current(service)
            if oncall_data and oncall_data.get("primary"):
                assigned_to = oncall_data["primary"].get("name")

        result = self._repo.create_incident(incident_id, title, service, severity, assigned_to)

        INCIDENTS_TOTAL.labels(status="open").inc()
        INCIDENTS_CREATED.labels(severity=severity).inc()

        self._notification.notify(incident_id, severity, assigned_to or "", title)
        logger.info("Incident created id=%s service=%s severity=%s assigned=%s",
                     incident_id, service, severity, assigned_to)
        return result

    def get_incident(self, incident_id: str) -> Optional[Dict[str, Any]]:
        return self._repo.get_incident(incident_id)

    def get_incident_detail(self, incident_id: str) -> Optional[Dict[str, Any]]:
        return self._repo.get_incident_detail(incident_id)

    def list_incidents(self, status=None, severity=None, service=None,
                       page=1, per_page=50) -> Tuple[int, List[Dict[str, Any]]]:
        return self._repo.list_incidents(status, severity, service, page, per_page)

    def update_incident(self, incident_id: str, status: Optional[str] = None,
                        notes: Optional[str] = None,
                        assigned_to: Optional[str] = None) -> Dict[str, Any]:
        current = self._repo.get_incident(incident_id)
        if not current:
            raise KeyError(f"Incident {incident_id} not found")

        now = datetime.now(timezone.utc)
        updates: List[str] = []
        params: Dict[str, Any] = {"id": incident_id}
        timeline_events: List[dict] = []

        if assigned_to is not None and assigned_to != current["assigned_to"]:
            updates.append("assigned_to = :assigned_to")
            params["assigned_to"] = assigned_to
            timeline_events.append({"type": "assigned", "detail": {
                "previous": current["assigned_to"], "new": assigned_to,
            }})

        if status and status != current["status"]:
            old_status = current["status"]
            allowed = ALLOWED_TRANSITIONS.get(old_status, set())
            if status not in allowed:
                raise ValueError(
                    f"Cannot transition from '{old_status}' to '{status}'. "
                    f"Allowed: {sorted(allowed) if allowed else 'none (terminal state)'}"
                )
            updates.append("status = :status")
            params["status"] = status
            INCIDENTS_TOTAL.labels(status=old_status).dec()
            INCIDENTS_TOTAL.labels(status=status).inc()

            if status in ("acknowledged", "in_progress") and current["acknowledged_at"] is None:
                updates.append("acknowledged_at = :ack_at")
                params["ack_at"] = now
                created = datetime.fromisoformat(current["created_at"])
                mtta = (now - created).total_seconds()
                updates.append("mtta_seconds = :mtta")
                params["mtta"] = mtta
                INCIDENT_MTTA.observe(mtta)
                logger.info("MTTA recorded incident=%s seconds=%.1f", incident_id, mtta)

            if status == "resolved" and current["resolved_at"] is None:
                updates.append("resolved_at = :res_at")
                params["res_at"] = now
                created = datetime.fromisoformat(current["created_at"])
                mttr = (now - created).total_seconds()
                updates.append("mttr_seconds = :mttr")
                params["mttr"] = mttr
                INCIDENT_MTTR.observe(mttr)
                logger.info("MTTR recorded incident=%s seconds=%.1f", incident_id, mttr)
                if current["acknowledged_at"] is None and "acknowledged_at = :ack_at" not in " ".join(updates):
                    updates.append("acknowledged_at = :ack_at2")
                    params["ack_at2"] = now
                    updates.append("mtta_seconds = :mtta2")
                    params["mtta2"] = mttr
                    INCIDENT_MTTA.observe(mttr)

            timeline_events.append({"type": status, "detail": {
                "from": old_status, "to": status,
            }})

        if notes:
            author = assigned_to or current.get("assigned_to") or "system"
            note_id = str(uuid.uuid4())
            # Note is added inside update_incident transaction
            params["note_id"] = note_id
            params["note_author"] = author
            params["note_content"] = notes
            params["note_ts"] = now
            timeline_events.append({"type": "note_added", "actor": author,
                                    "detail": {"note_id": note_id, "preview": notes[:100]}})

        return self._repo.update_incident(incident_id, updates, params, timeline_events)

    def get_incident_metrics(self, incident_id: str) -> Optional[Dict[str, Any]]:
        return self._repo.get_incident_metrics(incident_id)

    def get_timeline(self, incident_id: str) -> Dict[str, Any]:
        timeline = self._repo.get_timeline(incident_id)
        return {"incident_id": incident_id, "total": len(timeline), "timeline": timeline}

    def get_summary_stats(self) -> Dict[str, Any]:
        return self._repo.get_summary_stats()

    def add_note(self, incident_id: str, author: str, content: str) -> Dict[str, Any]:
        return self._repo.add_note(incident_id, author, content)
