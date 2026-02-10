# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""
Repository: Override data access.
Manages the in-memory store of on-call overrides.
"""

from typing import Any, Optional


class OverrideRepository:
    """In-memory override storage."""

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}

    # ── Read ──

    def get_by_team(self, team: str) -> Optional[dict[str, Any]]:
        return self._store.get(team)

    def get_all(self) -> dict[str, dict[str, Any]]:
        return dict(self._store)

    def exists(self, team: str) -> bool:
        return team in self._store

    def count(self) -> int:
        return len(self._store)

    # ── Write ──

    def save(self, team: str, override: dict[str, Any]) -> None:
        self._store[team] = override

    def delete(self, team: str) -> Optional[dict[str, Any]]:
        return self._store.pop(team, None)

    # ── Bulk / internal ──

    def clear(self) -> None:
        self._store.clear()

    @property
    def store(self) -> dict[str, dict[str, Any]]:
        """Direct access for legacy compatibility."""
        return self._store
