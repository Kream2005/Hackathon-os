# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""
Repository: Schedule data access.
Encapsulates all read/write operations on the schedules in-memory store.
NO business rules here — pure CRUD.
"""

from typing import Any, Optional


class ScheduleRepository:
    """In-memory schedule storage."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}

    # ── Read ──

    def get_all(self) -> list[dict[str, Any]]:
        return list(self._store.values())

    def get_by_team(self, team: str) -> Optional[dict[str, Any]]:
        return self._store.get(team)

    def exists(self, team: str) -> bool:
        return team in self._store

    def count(self) -> int:
        return len(self._store)

    # ── Write ──

    def save(self, team: str, schedule: dict[str, Any]) -> None:
        self._store[team] = schedule

    def delete(self, team: str) -> Optional[dict[str, Any]]:
        return self._store.pop(team, None)

    # ── Bulk / internal ──

    def clear(self) -> None:
        self._store.clear()

    @property
    def store(self) -> dict[str, dict[str, Any]]:
        """Direct access for legacy compatibility (tests, seeding)."""
        return self._store
