# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""
HTTP client for Notification Service — fire-and-forget.
"""

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class NotificationClient:
    """Sends notifications to the Notification Service. Never propagates failures."""

    def notify_alert(self, incident_id: str, severity: str, service: str, message: str):
        """Send a notification when an alert is correlated to an existing incident."""
        try:
            with httpx.Client(timeout=3.0) as client:
                client.post(
                    f"{settings.NOTIFICATION_SERVICE_URL}/api/v1/notify",
                    json={
                        "incident_id": incident_id,
                        "channel": "mock",
                        "recipient": "ops-team",
                        "message": f"[ALERT CORRELATED] [{severity.upper()}] {service}: {message[:120]}",
                        "severity": severity,
                    },
                )
        except Exception as exc:
            logger.warning("Notification service unreachable: %s", exc)
