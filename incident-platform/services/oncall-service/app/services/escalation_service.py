# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""
Service: Escalation orchestration.
Handles escalation triggering, secondary lookup, notification, and logging.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from app.core.logging import get_logger
from app.metrics.prometheus import ESCALATIONS_TOTAL, NOTIFICATIONS_SENT
from app.repositories.schedule_repository import ScheduleRepository
from app.repositories.escalation_repository import EscalationRepository
from app.repositories.history_repository import HistoryRepository
from app.services.notification_client import NotificationClient
from app.services.rotation import compute_rotation

logger = get_logger(__name__)


class EscalationService:
    """Business logic for incident escalation."""

    def __init__(
        self,
        schedule_repo: ScheduleRepository,
        escalation_repo: EscalationRepository,
        history_repo: HistoryRepository,
        notification_client: NotificationClient,
    ) -> None:
        self._schedules = schedule_repo
        self._escalations = escalation_repo
        self._history = history_repo
        self._notifications = notification_client

    def escalate(
        self,
        team: str,
        incident_id: str,
        reason: str | None = "No acknowledgment within SLA",
    ) -> dict[str, Any]:
        """Trigger an escalation — notifies the secondary on-call if available."""
        ESCALATIONS_TOTAL.labels(team=team).inc()
        NOTIFICATIONS_SENT.labels(channel="console").inc()

        escalation_id = str(uuid.uuid4())

        # Resolve secondary for escalation target
        escalated_to: dict[str, str] | None = None
        schedule = self._schedules.get_by_team(team)
        if schedule is not None:
            _, secondary = compute_rotation(schedule)
            if secondary:
                escalated_to = {
                    "name": secondary["name"],
                    "email": secondary["email"],
                }

        record: dict[str, Any] = {
            "escalation_id": escalation_id,
            "team": team,
            "incident_id": incident_id,
            "reason": reason,
            "escalated_to": escalated_to,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._escalations.append(record)

        self._history.record_event(
            "escalation",
            team,
            {
                "incident_id": incident_id,
                "reason": reason,
                "escalated_to": escalated_to,
            },
        )
        logger.info(
            "Escalation: team=%s, incident=%s, reason=%s",
            team, incident_id, reason,
        )

        if escalated_to:
            logger.info(
                "Escalated to: %s (%s)",
                escalated_to["name"], escalated_to["email"],
            )
            self._notifications.send(
                channel="email",
                recipient=escalated_to["email"],
                message=f"Escalation for incident {incident_id}: {reason}",
                incident_id=incident_id,
            )

        return {
            "status": "escalated",
            "escalation_id": escalation_id,
            "team": team,
            "incident_id": incident_id,
            "escalated_to": escalated_to,
            "message": (
                f"Escalation triggered for team '{team}' "
                f"\u2014 incident {incident_id}"
            ),
            "timestamp": record["timestamp"],
        }

    def list_escalations(
        self,
        team: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        return self._escalations.get_all(team=team, limit=limit)

    def get_escalation_count(self) -> int:
        return self._escalations.count()
