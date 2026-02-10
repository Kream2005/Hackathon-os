# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""
Repository: Alert data access layer — pure CRUD, no business rules.
"""

import json
import uuid
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.core.logging import get_logger

logger = get_logger(__name__)


class AlertRepository:
    """Handles all direct database operations for alerts."""

    def __init__(self, engine: Engine):
        self._engine = engine

    def find_existing_incident(self, service: str, severity: str, window_minutes: int) -> Optional[str]:
        """Return the UUID of an open incident matching the correlation window."""
        with self._engine.connect() as conn:
            row = conn.execute(
                text("""
                    SELECT id FROM incidents
                    WHERE service  = :service
                      AND severity = :severity
                      AND status  != 'resolved'
                      AND created_at > NOW() - MAKE_INTERVAL(mins => :window)
                    ORDER BY created_at DESC
                    LIMIT 1
                """),
                {"service": service, "severity": severity, "window": window_minutes},
            ).fetchone()
        return str(row[0]) if row else None

    def create_incident_locally(self, conn, service: str, severity: str, message: str) -> str:
        """Fallback: write the incident row directly when incident-management is down."""
        incident_id = str(uuid.uuid4())
        conn.execute(
            text("""
                INSERT INTO incidents (id, title, service, severity, status, alert_count, created_at)
                VALUES (:id, :title, :service, :severity, 'open', 0, NOW())
            """),
            {
                "id": incident_id,
                "title": f"[{severity.upper()}] {service}: {message[:120]}",
                "service": service,
                "severity": severity,
            },
        )
        conn.execute(
            text("""
                INSERT INTO incident_timeline (id, incident_id, event_type, actor, detail, created_at)
                VALUES (:tid, :iid, 'created', 'alert-ingestion', :detail, NOW())
            """),
            {"tid": str(uuid.uuid4()), "iid": incident_id, "detail": json.dumps({"fallback": True})},
        )
        return incident_id

    def increment_alert_count(self, conn, incident_id: str):
        """Bump the denormalised alert_count on the incident."""
        conn.execute(
            text("UPDATE incidents SET alert_count = alert_count + 1 WHERE id = :id"),
            {"id": incident_id},
        )

    def store_alert(self, conn, alert_id: str, service: str, severity: str,
                    message: str, source: str, labels: Dict[str, Any],
                    fingerprint: str, timestamp: str, incident_id: Optional[str]):
        """Persist an alert record."""
        conn.execute(
            text("""
                INSERT INTO alerts
                    (id, service, severity, message, source, labels, fingerprint,
                     timestamp, incident_id, created_at)
                VALUES
                    (:id, :service, :severity, :message, :source, :labels, :fp,
                     :ts, :incident_id, NOW())
            """),
            {
                "id": alert_id,
                "service": service,
                "severity": severity,
                "message": message,
                "source": source,
                "labels": json.dumps(labels),
                "fp": fingerprint,
                "ts": timestamp,
                "incident_id": incident_id,
            },
        )

    def add_correlation_timeline(self, conn, incident_id: str, alert_id: str, fingerprint: str):
        """Record a timeline entry for alert correlation."""
        conn.execute(
            text("""
                INSERT INTO incident_timeline
                    (id, incident_id, event_type, actor, detail, created_at)
                VALUES (:tid, :iid, 'alert_correlated', 'alert-ingestion', :detail, NOW())
            """),
            {
                "tid": str(uuid.uuid4()),
                "iid": incident_id,
                "detail": json.dumps({"alert_id": alert_id, "fingerprint": fingerprint}),
            },
        )

    def get_alert_by_id(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single alert by UUID."""
        with self._engine.connect() as conn:
            row = conn.execute(
                text("""
                    SELECT id, service, severity, message, source, labels,
                           fingerprint, timestamp, incident_id, created_at
                    FROM alerts WHERE id = :id
                """),
                {"id": alert_id},
            ).fetchone()

        if not row:
            return None

        return {
            "id": str(row[0]),
            "service": row[1],
            "severity": row[2],
            "message": row[3],
            "source": row[4] or "api",
            "labels": row[5] if isinstance(row[5], dict) else json.loads(row[5] or "{}"),
            "fingerprint": row[6],
            "timestamp": row[7].isoformat() if row[7] else None,
            "incident_id": str(row[8]) if row[8] else None,
            "created_at": row[9].isoformat() if row[9] else "",
        }

    def list_alerts(self, service: Optional[str] = None, severity: Optional[str] = None,
                    incident_id: Optional[str] = None, page: int = 1,
                    per_page: int = 50) -> Tuple[int, List[Dict[str, Any]]]:
        """List alerts with filtering and pagination."""
        conditions: List[str] = []
        params: Dict[str, Any] = {}

        if service:
            conditions.append("service = :service")
            params["service"] = service.lower()
        if severity:
            conditions.append("severity = :severity")
            params["severity"] = severity.lower()
        if incident_id:
            conditions.append("incident_id = :incident_id")
            params["incident_id"] = incident_id

        where = (" WHERE " + " AND ".join(conditions)) if conditions else ""

        with self._engine.connect() as conn:
            total = conn.execute(text(f"SELECT COUNT(*) FROM alerts{where}"), params).scalar()
            params["limit"] = per_page
            params["offset"] = (page - 1) * per_page
            rows = conn.execute(
                text(f"""
                    SELECT id, service, severity, message, source, labels,
                           fingerprint, timestamp, incident_id, created_at
                    FROM alerts{where}
                    ORDER BY created_at DESC
                    LIMIT :limit OFFSET :offset
                """),
                params,
            ).fetchall()

        alerts = [
            {
                "id": str(r[0]),
                "service": r[1],
                "severity": r[2],
                "message": r[3],
                "source": r[4] or "api",
                "labels": r[5] if isinstance(r[5], dict) else json.loads(r[5] or "{}"),
                "fingerprint": r[6],
                "timestamp": r[7].isoformat() if r[7] else None,
                "incident_id": str(r[8]) if r[8] else None,
                "created_at": r[9].isoformat() if r[9] else "",
            }
            for r in rows
        ]

        return total, alerts

    def begin_transaction(self):
        """Return a transactional connection context."""
        return self._engine.begin()

    def verify_connection(self):
        """Verify database connectivity."""
        with self._engine.connect() as conn:
            conn.execute(text("SELECT 1"))

    def dispose(self):
        """Dispose the connection pool."""
        self._engine.dispose()
