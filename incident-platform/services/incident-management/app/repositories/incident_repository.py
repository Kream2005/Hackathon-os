# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""Data-access layer for incidents, notes, and timeline."""
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.core.logging import get_logger

logger = get_logger(__name__)

INCIDENT_COLS = (
    "id, title, service, severity, status, assigned_to, alert_count, "
    "created_at, updated_at, acknowledged_at, resolved_at, mtta_seconds, mttr_seconds"
)


def _row_to_dict(row) -> Dict[str, Any]:
    return {
        "id": str(row[0]),
        "title": row[1],
        "service": row[2],
        "severity": row[3],
        "status": row[4],
        "assigned_to": row[5],
        "alert_count": row[6] or 0,
        "created_at": row[7].isoformat() if row[7] else "",
        "updated_at": row[8].isoformat() if row[8] else "",
        "acknowledged_at": row[9].isoformat() if row[9] else None,
        "resolved_at": row[10].isoformat() if row[10] else None,
        "mtta_seconds": row[11],
        "mttr_seconds": row[12],
    }


class IncidentRepository:
    def __init__(self, engine: Engine):
        self._engine = engine

    # ── Write ──────────────────────────────────────────────────────────

    def create_incident(self, incident_id: str, title: str, service: str,
                        severity: str, assigned_to: Optional[str]) -> Dict[str, Any]:
        with self._engine.begin() as conn:
            conn.execute(
                text(f"""
                    INSERT INTO incidents
                        (id, title, service, severity, status, assigned_to, alert_count, created_at, updated_at)
                    VALUES
                        (:id, :title, :service, :severity, 'open', :assigned_to, 0, NOW(), NOW())
                """),
                {"id": incident_id, "title": title, "service": service,
                 "severity": severity, "assigned_to": assigned_to},
            )
            self._add_timeline_event(conn, incident_id, "created", detail={
                "title": title, "severity": severity, "assigned_to": assigned_to,
            })
            if assigned_to:
                self._add_timeline_event(conn, incident_id, "assigned",
                                         detail={"assigned_to": assigned_to})
        now_iso = datetime.now(timezone.utc).isoformat()
        return {
            "id": incident_id, "title": title, "service": service,
            "severity": severity, "status": "open", "assigned_to": assigned_to,
            "alert_count": 0, "created_at": now_iso, "updated_at": now_iso,
            "acknowledged_at": None, "resolved_at": None,
            "mtta_seconds": None, "mttr_seconds": None,
        }

    def update_incident(self, incident_id: str, updates: List[str],
                        params: Dict[str, Any], timeline_events: List[dict]) -> Dict[str, Any]:
        with self._engine.begin() as conn:
            for evt in timeline_events:
                self._add_timeline_event(conn, incident_id, evt["type"],
                                         actor=evt.get("actor", "system"),
                                         detail=evt.get("detail"))
            if updates:
                conn.execute(
                    text(f"UPDATE incidents SET {', '.join(updates)} WHERE id = :id"),
                    params,
                )
            row = conn.execute(
                text(f"SELECT {INCIDENT_COLS} FROM incidents WHERE id = :id"),
                {"id": incident_id},
            ).fetchone()
        return _row_to_dict(row)

    def add_note(self, incident_id: str, author: str, content: str) -> Dict[str, Any]:
        note_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        with self._engine.begin() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM incidents WHERE id = :id"), {"id": incident_id}
            ).fetchone()
            if not exists:
                raise KeyError(f"Incident {incident_id} not found")
            conn.execute(
                text("""
                    INSERT INTO incident_notes (id, incident_id, author, content, created_at)
                    VALUES (:id, :iid, :author, :content, :ts)
                """),
                {"id": note_id, "iid": incident_id, "author": author,
                 "content": content, "ts": now},
            )
            self._add_timeline_event(conn, incident_id, "note_added", actor=author,
                                     detail={"note_id": note_id, "preview": content[:100]})
        return {"id": note_id, "incident_id": incident_id,
                "author": author, "content": content}

    # ── Read ───────────────────────────────────────────────────────────

    def get_incident(self, incident_id: str) -> Optional[Dict[str, Any]]:
        with self._engine.connect() as conn:
            row = conn.execute(
                text(f"SELECT {INCIDENT_COLS} FROM incidents WHERE id = :id"),
                {"id": incident_id},
            ).fetchone()
        return _row_to_dict(row) if row else None

    def get_incident_detail(self, incident_id: str) -> Optional[Dict[str, Any]]:
        with self._engine.connect() as conn:
            row = conn.execute(
                text(f"SELECT {INCIDENT_COLS} FROM incidents WHERE id = :id"),
                {"id": incident_id},
            ).fetchone()
            if not row:
                return None
            incident = _row_to_dict(row)

            alert_rows = conn.execute(
                text("""
                    SELECT id, service, severity, message, source, fingerprint, timestamp, created_at
                    FROM alerts WHERE incident_id = :iid ORDER BY created_at
                """), {"iid": incident_id},
            ).fetchall()
            incident["alerts"] = [
                {"id": str(a[0]), "service": a[1], "severity": a[2], "message": a[3],
                 "source": a[4], "fingerprint": a[5],
                 "timestamp": a[6].isoformat() if a[6] else None,
                 "created_at": a[7].isoformat() if a[7] else None}
                for a in alert_rows
            ]

            note_rows = conn.execute(
                text("SELECT id, author, content, created_at FROM incident_notes WHERE incident_id = :iid ORDER BY created_at"),
                {"iid": incident_id},
            ).fetchall()
            incident["notes"] = [
                {"id": str(n[0]), "author": n[1], "content": n[2],
                 "created_at": n[3].isoformat() if n[3] else None}
                for n in note_rows
            ]

            tl_rows = conn.execute(
                text("SELECT id, event_type, actor, detail, created_at FROM incident_timeline WHERE incident_id = :iid ORDER BY created_at"),
                {"iid": incident_id},
            ).fetchall()
            incident["timeline"] = [
                {"id": str(t[0]), "event_type": t[1], "actor": t[2],
                 "detail": t[3] if isinstance(t[3], dict) else json.loads(t[3] or "{}"),
                 "created_at": t[4].isoformat() if t[4] else None}
                for t in tl_rows
            ]
        return incident

    def list_incidents(self, status: Optional[str] = None, severity: Optional[str] = None,
                       service: Optional[str] = None, page: int = 1,
                       per_page: int = 50) -> Tuple[int, List[Dict[str, Any]]]:
        conditions = []
        params: Dict[str, Any] = {}
        if status:
            conditions.append("status = :status")
            params["status"] = status.lower()
        if severity:
            conditions.append("severity = :severity")
            params["severity"] = severity.lower()
        if service:
            conditions.append("service = :service")
            params["service"] = service.lower()
        where = (" WHERE " + " AND ".join(conditions)) if conditions else ""

        with self._engine.connect() as conn:
            total = conn.execute(text(f"SELECT COUNT(*) FROM incidents{where}"), params).scalar()
            params["limit"] = per_page
            params["offset"] = (page - 1) * per_page
            rows = conn.execute(
                text(f"SELECT {INCIDENT_COLS} FROM incidents{where} ORDER BY created_at DESC LIMIT :limit OFFSET :offset"),
                params,
            ).fetchall()
        return total, [_row_to_dict(r) for r in rows]

    def get_incident_metrics(self, incident_id: str) -> Optional[Dict[str, Any]]:
        with self._engine.connect() as conn:
            row = conn.execute(
                text("SELECT mtta_seconds, mttr_seconds, status, created_at, acknowledged_at, resolved_at FROM incidents WHERE id = :id"),
                {"id": incident_id},
            ).fetchone()
        if not row:
            return None
        return {
            "incident_id": incident_id,
            "mtta_seconds": row[0], "mttr_seconds": row[1], "status": row[2],
            "created_at": row[3].isoformat() if row[3] else None,
            "acknowledged_at": row[4].isoformat() if row[4] else None,
            "resolved_at": row[5].isoformat() if row[5] else None,
        }

    def get_timeline(self, incident_id: str) -> List[Dict[str, Any]]:
        with self._engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM incidents WHERE id = :id"), {"id": incident_id}
            ).fetchone()
            if not exists:
                raise KeyError(f"Incident {incident_id} not found")
            rows = conn.execute(
                text("SELECT id, event_type, actor, detail, created_at FROM incident_timeline WHERE incident_id = :iid ORDER BY created_at"),
                {"iid": incident_id},
            ).fetchall()
        return [
            {"id": str(r[0]), "event_type": r[1], "actor": r[2],
             "detail": r[3] if isinstance(r[3], dict) else json.loads(r[3]) if r[3] else {},
             "created_at": r[4].isoformat() if r[4] else None}
            for r in rows
        ]

    def get_summary_stats(self) -> Dict[str, Any]:
        with self._engine.connect() as conn:
            row = conn.execute(text("""
                SELECT
                    COUNT(*) FILTER (WHERE status = 'open')         AS open_count,
                    COUNT(*) FILTER (WHERE status = 'acknowledged') AS ack_count,
                    COUNT(*) FILTER (WHERE status = 'in_progress')  AS prog_count,
                    COUNT(*) FILTER (WHERE status = 'resolved')     AS resolved_count,
                    ROUND(AVG(mtta_seconds)::numeric, 1)            AS avg_mtta,
                    ROUND(AVG(mttr_seconds)::numeric, 1)            AS avg_mttr
                FROM incidents
            """)).fetchone()
        return {
            "open": row[0] or 0, "acknowledged": row[1] or 0,
            "in_progress": row[2] or 0, "resolved": row[3] or 0,
            "avg_mtta_seconds": float(row[4]) if row[4] else None,
            "avg_mttr_seconds": float(row[5]) if row[5] else None,
        }

    def count_by_status(self, status: str) -> int:
        with self._engine.connect() as conn:
            return conn.execute(
                text("SELECT COUNT(*) FROM incidents WHERE status = :s"), {"s": status}
            ).scalar() or 0

    def verify_connection(self):
        with self._engine.connect() as conn:
            conn.execute(text("SELECT 1"))

    def dispose(self):
        self._engine.dispose()

    # ── Private ────────────────────────────────────────────────────────

    def _add_timeline_event(self, conn, incident_id: str, event_type: str,
                            actor: str = "system", detail: Dict = None):
        conn.execute(
            text("""
                INSERT INTO incident_timeline (id, incident_id, event_type, actor, detail, created_at)
                VALUES (:id, :iid, :etype, :actor, :detail, NOW())
            """),
            {"id": str(uuid.uuid4()), "iid": incident_id, "etype": event_type,
             "actor": actor, "detail": json.dumps(detail or {})},
        )
