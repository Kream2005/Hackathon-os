# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""
FastAPI dependency injection — wire repositories and services.
"""

from app.repositories.schedule_repository import ScheduleRepository
from app.repositories.override_repository import OverrideRepository
from app.repositories.escalation_repository import EscalationRepository
from app.repositories.history_repository import HistoryRepository
from app.services.schedule_service import ScheduleService
from app.services.oncall_service import OnCallService
from app.services.escalation_service import EscalationService
from app.services.notification_client import NotificationClient

# ── Singleton repository instances (in-memory stores) ──
_schedule_repo = ScheduleRepository()
_override_repo = OverrideRepository()
_escalation_repo = EscalationRepository()
_history_repo = HistoryRepository()
_notification_client = NotificationClient()

# ── Service instances (with injected dependencies) ──
_schedule_service = ScheduleService(
    schedule_repo=_schedule_repo,
    override_repo=_override_repo,
    history_repo=_history_repo,
)
_oncall_service = OnCallService(
    schedule_repo=_schedule_repo,
    override_repo=_override_repo,
    history_repo=_history_repo,
    notification_client=_notification_client,
)
_escalation_service = EscalationService(
    schedule_repo=_schedule_repo,
    escalation_repo=_escalation_repo,
    history_repo=_history_repo,
    notification_client=_notification_client,
)


# ── FastAPI dependency functions ──
def get_schedule_service() -> ScheduleService:
    return _schedule_service


def get_oncall_service() -> OnCallService:
    return _oncall_service


def get_escalation_service() -> EscalationService:
    return _escalation_service


def get_schedule_repo() -> ScheduleRepository:
    return _schedule_repo


def get_override_repo() -> OverrideRepository:
    return _override_repo


def get_escalation_repo() -> EscalationRepository:
    return _escalation_repo


def get_history_repo() -> HistoryRepository:
    return _history_repo
