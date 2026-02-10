# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""
Service: On-Call lookups, overrides, and rotation tracking.
Business logic for determining who is currently on-call.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger
from app.metrics.prometheus import (
    ONCALL_LOOKUPS,
    OVERRIDES_ACTIVE,
    ROTATION_CHANGES,
)
from app.repositories.schedule_repository import ScheduleRepository
from app.repositories.override_repository import OverrideRepository
from app.repositories.history_repository import HistoryRepository
from app.services.notification_client import NotificationClient
from app.services.rotation import compute_rotation

logger = get_logger(__name__)


class OnCallService:
    """Business logic for on-call lookups and overrides."""

    def __init__(
        self,
        schedule_repo: ScheduleRepository,
        override_repo: OverrideRepository,
        history_repo: HistoryRepository,
        notification_client: NotificationClient,
    ) -> None:
        self._schedules = schedule_repo
        self._overrides = override_repo
        self._history = history_repo
        self._notifications = notification_client
        self._last_known_oncall: dict[str, str] = {}

    @property
    def last_known_oncall(self) -> dict[str, str]:
        """Expose for legacy test compatibility."""
        return self._last_known_oncall

    # ── On-Call Current ──

    def get_current_oncall(self, team: str) -> dict[str, Any]:
        """
        Determine the current on-call engineer for a team.
        Override takes precedence over rotation.
        Raises KeyError if team not found, RuntimeError if no primary.
        """
        if not self._schedules.exists(team):
            raise KeyError(f"No schedule found for team '{team}'")

        ONCALL_LOOKUPS.labels(team=team).inc()
        self.cleanup_expired_overrides()

        # Override takes precedence
        override = self._overrides.get_by_team(team)
        if override is not None:
            schedule = self._schedules.get_by_team(team)
            return {
                "team": team,
                "primary": {
                    "name": override["user_name"],
                    "email": override["user_email"],
                    "override": True,
                    "reason": override.get("reason", "Manual override"),
                    "expires_at": override.get("expires_at"),
                },
                "schedule_id": schedule["id"],
                "rotation_type": schedule["rotation_type"],
            }

        schedule = self._schedules.get_by_team(team)
        current_primary, current_secondary = compute_rotation(schedule)

        if not current_primary:
            raise RuntimeError(
                f"No primary on-call members configured for team '{team}'"
            )

        # Detect rotation change -> notify new on-call
        previous_primary = self._last_known_oncall.get(team)
        if previous_primary and previous_primary != current_primary["name"]:
            ROTATION_CHANGES.labels(team=team).inc()
            self._history.record_event(
                "rotation_change",
                team,
                {
                    "old_primary": previous_primary,
                    "new_primary": current_primary["name"],
                },
            )
            self._notifications.send(
                channel="console",
                recipient=current_primary["email"],
                message=f"You are now on-call for team '{team}'",
            )
        self._last_known_oncall[team] = current_primary["name"]

        result: dict[str, Any] = {
            "team": team,
            "primary": {
                "name": current_primary["name"],
                "email": current_primary["email"],
            },
            "schedule_id": schedule["id"],
            "rotation_type": schedule["rotation_type"],
        }
        if current_secondary:
            result["secondary"] = {
                "name": current_secondary["name"],
                "email": current_secondary["email"],
            }
        return result

    # ── Overrides ──

    def set_override(
        self,
        team: str,
        user_name: str,
        user_email: str,
        reason: str | None = "Manual override",
        duration_hours: int | None = None,
    ) -> dict[str, Any]:
        """Set a temporary override. Raises KeyError if team not found."""
        if not self._schedules.exists(team):
            raise KeyError(f"No schedule found for team '{team}'")

        duration = duration_hours or settings.DEFAULT_OVERRIDE_HOURS
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=duration)

        self._overrides.save(team, {
            "user_name": user_name,
            "user_email": user_email,
            "reason": reason,
            "duration_hours": duration,
            "created_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
        })
        OVERRIDES_ACTIVE.set(self._overrides.count())
        self._history.record_event(
            "override_start",
            team,
            {
                "user_name": user_name,
                "reason": reason,
                "duration_hours": duration,
                "expires_at": expires_at.isoformat(),
            },
        )
        logger.info(
            "Override set: team=%s, user=%s, expires=%s",
            team, user_name, expires_at.isoformat(),
        )
        return {
            "status": "override_set",
            "team": team,
            "overridden_to": user_name,
            "duration_hours": duration,
            "expires_at": expires_at.isoformat(),
        }

    def remove_override(self, team: str) -> dict[str, str]:
        """Remove an active override. Raises KeyError if not found."""
        if not self._overrides.exists(team):
            raise KeyError(f"No active override for team '{team}'")

        override = self._overrides.delete(team)
        OVERRIDES_ACTIVE.set(self._overrides.count())
        self._history.record_event(
            "override_end",
            team,
            {"user_name": override["user_name"], "removed_manually": True},
        )
        logger.info("Override removed: team=%s", team)
        return {"status": "override_removed", "team": team}

    def list_active_overrides(self) -> list[dict[str, Any]]:
        """List all currently active (non-expired) overrides."""
        self.cleanup_expired_overrides()
        return [
            {
                "team": team,
                "user_name": ov["user_name"],
                "user_email": ov["user_email"],
                "reason": ov.get("reason"),
                "created_at": ov["created_at"],
                "expires_at": ov.get("expires_at"),
                "duration_hours": ov.get("duration_hours"),
            }
            for team, ov in self._overrides.get_all().items()
        ]

    # ── Internal ──

    def cleanup_expired_overrides(self) -> None:
        """Remove all expired overrides and log them."""
        now = datetime.now(timezone.utc)
        all_overrides = self._overrides.get_all()
        expired_teams = [
            team
            for team, ov in all_overrides.items()
            if "expires_at" in ov
            and datetime.fromisoformat(ov["expires_at"]) <= now
        ]
        for team in expired_teams:
            override = self._overrides.delete(team)
            self._history.record_event(
                "override_expired",
                team,
                {
                    "user_name": override["user_name"],
                    "expired_at": override["expires_at"],
                },
            )
            logger.info("Override expired: team=%s, user=%s", team, override["user_name"])
        if expired_teams:
            OVERRIDES_ACTIVE.set(self._overrides.count())
