# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""HTTP client to dispatch notifications."""
import httpx
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class NotificationClient:
    def notify(self, incident_id: str, severity: str, assigned_to: str, title: str):
        recipients = []
        if assigned_to:
            recipients.append({"recipient": assigned_to, "channel": "mock"})
        recipients.append({"recipient": "ops-team", "channel": "slack"})

        for target in recipients:
            try:
                with httpx.Client(timeout=3.0) as client:
                    client.post(
                        f"{settings.NOTIFICATION_SERVICE_URL}/api/v1/notify",
                        json={
                            "incident_id": incident_id,
                            "channel": target["channel"],
                            "recipient": target["recipient"],
                            "message": title if title.startswith("[") else f"[{severity.upper()}] {title}",
                            "severity": severity,
                        },
                    )
            except Exception as exc:
                logger.warning("Notification service unreachable: %s", exc)
