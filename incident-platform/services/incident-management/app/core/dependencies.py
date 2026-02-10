# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""FastAPI dependency injection wiring."""
from app.core.database import engine
from app.repositories.incident_repository import IncidentRepository
from app.services.incident_service import IncidentService
from app.services.oncall_client import OncallClient
from app.services.notification_client import NotificationClient

_repo = IncidentRepository(engine)
_oncall_client = OncallClient()
_notification_client = NotificationClient()
_service = IncidentService(_repo, _oncall_client, _notification_client)


def get_incident_repo() -> IncidentRepository:
    return _repo


def get_incident_service() -> IncidentService:
    return _service
