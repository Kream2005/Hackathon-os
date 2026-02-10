# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""
FastAPI dependency injection — wire repositories and services.
"""

from app.core.database import engine
from app.repositories.alert_repository import AlertRepository
from app.services.alert_service import AlertService
from app.services.incident_client import IncidentClient
from app.services.notification_client import NotificationClient

# ── Singleton instances ──
_alert_repo = AlertRepository(engine)
_incident_client = IncidentClient()
_notification_client = NotificationClient()

_alert_service = AlertService(
    alert_repo=_alert_repo,
    incident_client=_incident_client,
    notification_client=_notification_client,
)


# ── FastAPI dependency functions ──
def get_alert_service() -> AlertService:
    return _alert_service


def get_alert_repo() -> AlertRepository:
    return _alert_repo
