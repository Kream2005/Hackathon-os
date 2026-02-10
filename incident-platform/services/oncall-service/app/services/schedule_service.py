# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""
Service: Schedule management — business logic for CRUD operations.
Coordinates repository writes with metrics, history, and validation.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from app.core.logging import get_logger
from app.metrics.prometheus import SCHEDULES_CREATED, ACTIVE_SCHEDULES, OVERRIDES_ACTIVE
from app.repositories.schedule_repository import ScheduleRepository
from app.repositories.override_repository import OverrideRepository
from app.repositories.history_repository import HistoryRepository

logger = get_logger(__name__)


class ScheduleService:
    """Business logic for on-call schedule management."""

    def __init__(
        self,
        schedule_repo: ScheduleRepository,
        override_repo: OverrideRepository,
        history_repo: HistoryRepository,
    ) -> None:
        self._schedules = schedule_repo
        self._overrides = override_repo
        self._history = history_repo

    # ── Commands ──

    def create_schedule(
        self,
        team: str,
        rotation_type: str,
        members: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Create (or replace) a schedule. Raises ValueError on bad input."""
        primary_members = [m for m in members if m["role"] == "primary"]
        if not primary_members:
            raise ValueError("At least one member with role 'primary' is required")

        schedule_id = str(uuid.uuid4())
        schedule_record: dict[str, Any] = {
            "id": schedule_id,
            "team": team,
            "rotation_type": rotation_type,
            "members": members,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": None,
        }
        self._schedules.save(team, schedule_record)

        SCHEDULES_CREATED.inc()
        ACTIVE_SCHEDULES.set(self._schedules.count())
        self._history.record_event(
            "schedule_created",
            team,
            {"members_count": len(members), "rotation_type": rotation_type},
        )
        logger.info("Schedule created: team=%s, members=%d", team, len(members))
        return schedule_record

    def update_schedule(
        self,
        team: str,
        rotation_type: str | None = None,
        add_members: list[dict[str, Any]] | None = None,
        remove_members: list[str] | None = None,
    ) -> dict[str, Any]:
        """Partially update a schedule. Raises KeyError / ValueError."""
        schedule = self._schedules.get_by_team(team)
        if schedule is None:
            raise KeyError(f"No schedule found for team '{team}'")

        changes: dict[str, Any] = {}

        if rotation_type is not None:
            changes["rotation_type"] = {
                "old": schedule["rotation_type"],
                "new": rotation_type,
            }
            schedule["rotation_type"] = rotation_type

        if add_members:
            existing_names = {m["name"] for m in schedule["members"]}
            added: list[str] = []
            for member in add_members:
                if member["name"] not in existing_names:
                    schedule["members"].append(member)
                    added.append(member["name"])
            if added:
                changes["added_members"] = added

        if remove_members:
            before_count = len(schedule["members"])
            schedule["members"] = [
                m for m in schedule["members"] if m["name"] not in remove_members
            ]
            removed = before_count - len(schedule["members"])
            if removed > 0:
                changes["removed_members"] = remove_members[:removed]

        primary_remaining = [m for m in schedule["members"] if m["role"] == "primary"]
        if not primary_remaining:
            raise ValueError(
                "Cannot remove all primary members. At least one primary is required."
            )

        schedule["updated_at"] = datetime.now(timezone.utc).isoformat()
        if changes:
            self._history.record_event("schedule_updated", team, changes)
            logger.info("Schedule updated: team=%s, changes=%s", team, list(changes.keys()))
        return schedule

    def delete_schedule(self, team: str) -> dict[str, str]:
        """Delete a schedule and associated overrides. Raises KeyError."""
        if not self._schedules.exists(team):
            raise KeyError(f"No schedule found for team '{team}'")

        self._schedules.delete(team)
        self._overrides.delete(team)

        ACTIVE_SCHEDULES.set(self._schedules.count())
        OVERRIDES_ACTIVE.set(self._overrides.count())
        self._history.record_event("schedule_deleted", team, {})
        logger.info("Schedule deleted: team=%s", team)
        return {"status": "deleted", "team": team}

    # ── Queries ──

    def list_schedules(self) -> list[dict[str, Any]]:
        return self._schedules.get_all()

    def get_schedule(self, team: str) -> dict[str, Any]:
        schedule = self._schedules.get_by_team(team)
        if schedule is None:
            raise KeyError(f"No schedule found for team '{team}'")
        return schedule

    # ── Seed ──

    def seed_defaults(self) -> None:
        """Create default schedules so the service is usable immediately."""
        default_schedules = [
            {
                "team": "platform-engineering",
                "rotation_type": "weekly",
                "members": [
                    {"name": "Alice Martin", "email": "alice@company.com", "role": "primary"},
                    {"name": "Bob Dupont", "email": "bob@company.com", "role": "primary"},
                    {"name": "Carol Chen", "email": "carol@company.com", "role": "secondary"},
                ],
            },
            {
                "team": "backend",
                "rotation_type": "weekly",
                "members": [
                    {"name": "David Kumar", "email": "david@company.com", "role": "primary"},
                    {"name": "Eve Johnson", "email": "eve@company.com", "role": "secondary"},
                ],
            },
            {
                "team": "frontend",
                "rotation_type": "daily",
                "members": [
                    {"name": "Frank Wilson", "email": "frank@company.com", "role": "primary"},
                    {"name": "Grace Lee", "email": "grace@company.com", "role": "secondary"},
                ],
            },
            {
                "team": "infrastructure",
                "rotation_type": "biweekly",
                "members": [
                    {"name": "Hank Brown", "email": "hank@company.com", "role": "primary"},
                    {"name": "Ivy Davis", "email": "ivy@company.com", "role": "primary"},
                    {"name": "Jack White", "email": "jack@company.com", "role": "secondary"},
                ],
            },
        ]
        for sd in default_schedules:
            schedule_id = str(uuid.uuid4())
            self._schedules.save(
                sd["team"],
                {
                    "id": schedule_id,
                    "team": sd["team"],
                    "rotation_type": sd["rotation_type"],
                    "members": sd["members"],
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": None,
                },
            )
            self._history.record_event(
                "schedule_created",
                sd["team"],
                {
                    "members_count": len(sd["members"]),
                    "rotation_type": sd["rotation_type"],
                    "source": "seed",
                },
            )
        logger.info("Seeded %d default on-call schedules", len(default_schedules))
        ACTIVE_SCHEDULES.set(self._schedules.count())

    # ── Stats helpers ──

    def get_stats(self) -> dict[str, Any]:
        """Aggregated operational statistics."""
        schedules = self._schedules.get_all()
        total_members = sum(len(s["members"]) for s in schedules)
        rotation_types: dict[str, int] = {}
        for s in schedules:
            rt = s["rotation_type"]
            rotation_types[rt] = rotation_types.get(rt, 0) + 1

        return {
            "total_schedules": self._schedules.count(),
            "total_members": total_members,
            "active_overrides": self._overrides.count(),
            "total_escalations": 0,  # filled by controller from escalation repo
            "total_history_events": self._history.count(),
            "rotation_types": rotation_types,
            "event_types": self._history.count_by_type(),
        }

    def list_teams(self) -> list[dict[str, Any]]:
        """List all teams with summary info."""
        return [
            {
                "team": s["team"],
                "members_count": len(s["members"]),
                "rotation_type": s["rotation_type"],
                "has_override": self._overrides.exists(s["team"]),
            }
            for s in self._schedules.get_all()
        ]
