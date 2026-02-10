# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""Business logic for notification processing."""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.core.logging import get_logger
from app.metrics import NOTIFICATIONS_SENT, NOTIFICATION_PROCESSING, NOTIFICATIONS_IN_LOG
from app.repositories.notification_repository import NotificationRepository
from app.services.channel_handlers import CHANNEL_HANDLERS, deliver_mock

logger = get_logger(__name__)


class NotificationService:
    def __init__(self, repo: NotificationRepository):
        self._repo = repo

    def seed_gauge(self):
        count = self._repo.count_all()
        NOTIFICATIONS_IN_LOG.set(count)
        logger.info("Notification service started — %d notifications in DB", count)

    async def process_notification(self, incident_id: str, channel: str,
                                   recipient: str, message: str,
                                   severity: Optional[str] = None,
                                   metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        with NOTIFICATION_PROCESSING.time():
            notification_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc).isoformat()

            handler = CHANNEL_HANDLERS.get(channel, deliver_mock)
            status = await handler(
                incident_id=incident_id, recipient=recipient,
                message=message, severity=severity,
            )

            NOTIFICATIONS_SENT.labels(channel=channel, status=status).inc()

            entry = {
                "id": notification_id,
                "incident_id": incident_id,
                "channel": channel,
                "recipient": recipient,
                "message": message,
                "severity": severity,
                "status": status,
                "metadata": metadata,
                "created_at": now,
            }
            self._repo.store_notification(entry)
            NOTIFICATIONS_IN_LOG.inc()

            logger.info(
                "Notification processed id=%s incident=%s channel=%s status=%s recipient=%s",
                notification_id, incident_id, channel, status, recipient,
            )
            return entry

    def get_notification(self, notification_id: str) -> Optional[Dict[str, Any]]:
        return self._repo.get_notification(notification_id)

    def list_notifications(self, channel=None, status=None, incident_id=None,
                           recipient=None, page=1, per_page=50) -> Tuple[int, List[Dict[str, Any]]]:
        return self._repo.list_notifications(channel, status, incident_id, recipient, page, per_page)

    def get_stats(self) -> Dict[str, Any]:
        return self._repo.get_stats()
