# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""
Service: Notification client — inter-service communication.
Handles HTTP calls to the notification-service with timeout & fault tolerance.
"""

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.metrics.prometheus import NOTIFICATIONS_SENT

logger = get_logger(__name__)


class NotificationClient:
    """Fire-and-forget notification sender via notification-service."""

    def send(
        self,
        channel: str,
        recipient: str,
        message: str,
        incident_id: str = "N/A",
    ) -> None:
        """Send a notification. Failures are logged but never raised."""
        try:
            with httpx.Client(timeout=settings.NOTIFICATION_TIMEOUT) as client:
                resp = client.post(
                    f"{settings.NOTIFICATION_SERVICE_URL}/api/v1/notify",
                    json={
                        "channel": channel,
                        "recipient": recipient,
                        "message": message,
                        "incident_id": incident_id,
                    },
                )
            NOTIFICATIONS_SENT.labels(channel=channel).inc()
            logger.info(
                "Notification sent: recipient=%s, channel=%s, status=%d",
                recipient,
                channel,
                resp.status_code,
            )
        except Exception as exc:
            logger.warning("Notification failed: %s", exc)
