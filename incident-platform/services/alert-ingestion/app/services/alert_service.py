# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""
Service: Alert business logic — correlation, deduplication, incident creation.
"""

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.core.logging import get_logger
from app.metrics import ALERTS_RECEIVED, ALERTS_CORRELATED, ALERT_PROCESSING
from app.repositories import AlertRepository
from app.services.incident_client import IncidentClient
from app.services.notification_client import NotificationClient

logger = get_logger(__name__)


class AlertService:
    """All alert business logic — correlation, dedup, metrics."""

    def __init__(
        self,
        alert_repo: AlertRepository,
        incident_client: IncidentClient,
        notification_client: NotificationClient,
    ):
        self._repo = alert_repo
        self._incident_client = incident_client
        self._notification_client = notification_client

    @staticmethod
    def compute_fingerprint(service: str, severity: str, message: str) -> str:
        """SHA-256 fingerprint for deduplication."""
        raw = f"{service}|{severity}|{message[:100]}".lower()
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def process_alert(self, service: str, severity: str, message: str,
                      source: str, labels: Dict[str, Any],
                      timestamp: Optional[str] = None) -> Dict[str, Any]:
        """Receive a new alert, correlate it to an existing or new incident."""
        with ALERT_PROCESSING.time():
            ts = timestamp or datetime.now(timezone.utc).isoformat()
            fingerprint = self.compute_fingerprint(service, severity, message)

            ALERTS_RECEIVED.labels(severity=severity).inc()

            alert_id = str(uuid.uuid4())
            incident_id: Optional[str] = None
            action = "new_incident"

            with self._repo.begin_transaction() as conn:
                # Correlation
                existing = self._repo.find_existing_incident(
                    service, severity, settings.CORRELATION_WINDOW_MINUTES
                )

                if existing:
                    incident_id = existing
                    action = "existing_incident"
                    self._repo.increment_alert_count(conn, incident_id)
                else:
                    incident_id = self._incident_client.create_incident(
                        service, severity, message
                    )
                    if incident_id:
                        self._repo.increment_alert_count(conn, incident_id)
                    else:
                        incident_id = self._repo.create_incident_locally(
                            conn, service, severity, message
                        )
                        self._repo.increment_alert_count(conn, incident_id)

                # Store alert
                self._repo.store_alert(
                    conn, alert_id, service, severity, message,
                    source, labels, fingerprint, ts, incident_id
                )

                # Timeline for correlation
                if existing:
                    self._repo.add_correlation_timeline(
                        conn, incident_id, alert_id, fingerprint
                    )

            ALERTS_CORRELATED.labels(result=action).inc()

            # Notify for correlated alerts
            if action == "existing_incident" and incident_id:
                self._notification_client.notify_alert(
                    incident_id, severity, service, message
                )

            logger.info(
                "Alert processed alert_id=%s incident_id=%s action=%s fingerprint=%s",
                alert_id, incident_id, action, fingerprint,
            )

            return {
                "alert_id": alert_id,
                "incident_id": incident_id,
                "fingerprint": fingerprint,
                "status": "accepted",
                "action": action,
            }

    def get_alert(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """Get a single alert by ID."""
        return self._repo.get_alert_by_id(alert_id)

    def list_alerts(self, service: Optional[str] = None,
                    severity: Optional[str] = None,
                    incident_id: Optional[str] = None,
                    page: int = 1,
                    per_page: int = 50) -> Tuple[int, List[Dict[str, Any]]]:
        """List alerts with filtering and pagination."""
        return self._repo.list_alerts(service, severity, incident_id, page, per_page)
