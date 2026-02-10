# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""Data-access layer for notifications."""
import json
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from app.core.logging import get_logger

logger = get_logger(__name__)


class NotificationRepository:
    def __init__(self, engine: Engine):
        self._engine = engine

    def store_notification(self, entry: Dict[str, Any]) -> None:
        try:
            with self._engine.begin() as conn:
                conn.execute(
                    text("""
                        INSERT INTO notifications
                            (id, incident_id, channel, recipient, message, severity, status, metadata, created_at)
                        VALUES
                            (:id, :incident_id, :channel, :recipient, :message, :severity, :status, :metadata, :created_at)
                    """),
                    {
                        "id": entry["id"],
                        "incident_id": entry["incident_id"],
                        "channel": entry["channel"],
                        "recipient": entry["recipient"],
                        "message": entry["message"],
                        "severity": entry.get("severity"),
                        "status": entry["status"],
                        "metadata": json.dumps(entry.get("metadata") or {}),
                        "created_at": entry["created_at"],
                    },
                )
        except SQLAlchemyError as exc:
            logger.error("Failed to persist notification %s: %s", entry["id"], exc)

    def get_notification(self, notification_id: str) -> Optional[Dict[str, Any]]:
        with self._engine.connect() as conn:
            row = conn.execute(
                text("SELECT id, incident_id, channel, recipient, message, severity, status, metadata, created_at FROM notifications WHERE id = :id"),
                {"id": notification_id},
            ).mappings().first()
        if not row:
            return None
        return {
            "id": str(row["id"]),
            "incident_id": row["incident_id"],
            "channel": row["channel"],
            "recipient": row["recipient"],
            "message": row["message"],
            "severity": row["severity"],
            "status": row["status"],
            "metadata": row["metadata"],
            "created_at": row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else str(row["created_at"]),
        }

    def list_notifications(self, channel: Optional[str] = None, status: Optional[str] = None,
                           incident_id: Optional[str] = None, recipient: Optional[str] = None,
                           page: int = 1, per_page: int = 50) -> Tuple[int, List[Dict[str, Any]]]:
        conditions: list[str] = []
        params: Dict[str, Any] = {}
        if channel:
            conditions.append("channel = :channel")
            params["channel"] = channel.lower()
        if status:
            conditions.append("status = :status")
            params["status"] = status.lower()
        if incident_id:
            conditions.append("incident_id = :incident_id")
            params["incident_id"] = incident_id
        if recipient:
            conditions.append("recipient = :recipient")
            params["recipient"] = recipient
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        with self._engine.connect() as conn:
            total = conn.execute(text(f"SELECT COUNT(*) FROM notifications {where}"), params).scalar() or 0
            params["limit"] = per_page
            params["offset"] = (page - 1) * per_page
            rows = conn.execute(
                text(f"""
                    SELECT id, incident_id, channel, recipient, message, severity, status, metadata, created_at
                    FROM notifications {where}
                    ORDER BY created_at DESC
                    LIMIT :limit OFFSET :offset
                """),
                params,
            ).mappings().all()

        notifications = [
            {
                "id": str(r["id"]),
                "incident_id": r["incident_id"],
                "channel": r["channel"],
                "recipient": r["recipient"],
                "message": r["message"],
                "severity": r["severity"],
                "status": r["status"],
                "metadata": r["metadata"],
                "created_at": r["created_at"].isoformat() if hasattr(r["created_at"], "isoformat") else str(r["created_at"]),
            }
            for r in rows
        ]
        return total, notifications

    def get_stats(self) -> Dict[str, Any]:
        with self._engine.connect() as conn:
            row = conn.execute(text("""
                SELECT
                    COUNT(*)                                  AS total,
                    COUNT(*) FILTER (WHERE status = 'sent')   AS sent,
                    COUNT(*) FILTER (WHERE status = 'failed') AS failed
                FROM notifications
            """)).mappings().first()
            channel_rows = conn.execute(text(
                "SELECT channel, COUNT(*) AS cnt FROM notifications GROUP BY channel"
            )).mappings().all()
            severity_rows = conn.execute(text(
                "SELECT COALESCE(severity, 'unknown') AS sev, COUNT(*) AS cnt FROM notifications GROUP BY severity"
            )).mappings().all()
        by_channel = {r["channel"]: r["cnt"] for r in channel_rows}
        by_severity = {r["sev"]: r["cnt"] for r in severity_rows}
        return {
            "total": row["total"], "sent": row["sent"], "failed": row["failed"],
            "by_channel": by_channel, "by_severity": by_severity,
        }

    def count_all(self) -> int:
        with self._engine.connect() as conn:
            return conn.execute(text("SELECT COUNT(*) FROM notifications")).scalar() or 0

    def verify_connection(self) -> int:
        with self._engine.connect() as conn:
            return conn.execute(text("SELECT COUNT(*) FROM notifications")).scalar() or 0

    def dispose(self):
        self._engine.dispose()
