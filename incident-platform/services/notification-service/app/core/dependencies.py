# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""FastAPI dependency injection wiring."""
from app.core.database import engine
from app.repositories.notification_repository import NotificationRepository
from app.services.notification_service import NotificationService

_repo = NotificationRepository(engine)
_service = NotificationService(_repo)


def get_notification_repo() -> NotificationRepository:
    return _repo


def get_notification_service() -> NotificationService:
    return _service
