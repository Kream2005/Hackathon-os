# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""
Repository: Escalation log data access.
Bounded append-only log with configurable max size.
"""

from typing import Any, Optional

from app.core.config import settings


class EscalationRepository:
    """In-memory escalation log (bounded ring buffer)."""

    def __init__(self) -> None:
        self._log: list[dict[str, Any]] = []

    # ── Read ──

    def get_all(
        self,
        team: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        effective_limit = limit or settings.DEFAULT_ESCALATION_LIMIT
        result = (
            [e for e in self._log if e["team"] == team]
            if team
            else list(self._log)
        )
        return result[-effective_limit:]

    def count(self) -> int:
        return len(self._log)

    # ── Write ──

    def append(self, record: dict[str, Any]) -> None:
        self._log.append(record)
        if len(self._log) > settings.MAX_ESCALATION_LOG_SIZE:
            del self._log[: len(self._log) - settings.MAX_ESCALATION_LOG_SIZE]

    # ── Bulk / internal ──

    def clear(self) -> None:
        self._log.clear()

    @property
    def log(self) -> list[dict[str, Any]]:
        """Direct access for legacy compatibility."""
        return self._log
