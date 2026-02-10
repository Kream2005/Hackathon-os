# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""
Repository: Audit history (event log) data access.
Bounded append-only log for all on-call events.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from app.core.config import settings


class HistoryRepository:
    """In-memory event log (bounded ring buffer)."""

    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []

    # ── Read ──

    def get_all(
        self,
        team: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        effective_limit = limit or settings.DEFAULT_HISTORY_LIMIT
        result = list(self._events)
        if team:
            result = [e for e in result if e["team"] == team]
        if event_type:
            result = [e for e in result if e["event_type"] == event_type]
        return result[-effective_limit:]

    def count(self) -> int:
        return len(self._events)

    def count_by_type(self) -> dict[str, int]:
        """Return a dict of event_type -> count."""
        event_types: dict[str, int] = {}
        for e in self._events:
            et = e["event_type"]
            event_types[et] = event_types.get(et, 0) + 1
        return event_types

    # ── Write ──

    def record_event(
        self, event_type: str, team: str, details: dict[str, Any]
    ) -> dict[str, Any]:
        """Append an event to the audit log, trimming oldest if over max."""
        event: dict[str, Any] = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "team": team,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details,
        }
        self._events.append(event)
        if len(self._events) > settings.MAX_HISTORY_SIZE:
            del self._events[: len(self._events) - settings.MAX_HISTORY_SIZE]
        return event

    # ── Bulk / internal ──

    def clear(self) -> None:
        self._events.clear()

    @property
    def events(self) -> list[dict[str, Any]]:
        """Direct access for legacy compatibility."""
        return self._events
