# type: ignore
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
"""
Incident Management Service
============================
Manages the full incident lifecycle: creation, assignment, acknowledgment,
resolution, timeline tracking, and SRE metrics (MTTA / MTTR).

Enforces a strict status state-machine:
    open ─► acknowledged ─► in_progress ─► resolved
    open ─► in_progress ─► resolved
    open ─► resolved  (fast-track)

Port: 8002
"""
import json
import os
import uuid
import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field, field_validator
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# ── Configuration ──────────────────────────────────────────────────────────
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://hackathon:hackathon2026@incident-db:5432/incident_db",
)
ONCALL_SERVICE_URL = os.getenv("ONCALL_SERVICE_URL", "http://oncall-service:8003")
NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification-service:8004")
ALERT_INGESTION_URL = os.getenv("ALERT_INGESTION_URL", "http://alert-ingestion:8001")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# ── Structured JSON Logger ─────────────────────────────────────────────────
class _JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": "incident-management",
            "msg": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1]:
            log_obj["exception"] = str(record.exc_info[1])
        return json.dumps(log_obj)


_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(_JSONFormatter())
logger = logging.getLogger("incident-management")
logger.handlers = [_handler]
logger.setLevel(LOG_LEVEL)

# ── Database ──────────────────────────────────────────────────────────────
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=5,
    pool_recycle=300,
)

# ── Prometheus Metrics ────────────────────────────────────────────────────
incidents_created_total = Counter(
    "incidents_created_total", "Total incidents created", ["severity"]
)
incidents_total = Gauge(
    "incidents_total", "Current incidents by status", ["status"]
)
incident_mtta_seconds = Histogram(
    "incident_mtta_seconds",
    "Mean Time To Acknowledge (seconds)",
    buckets=[30, 60, 120, 300, 600, 1800, 3600],
)
incident_mttr_seconds = Histogram(
    "incident_mttr_seconds",
    "Mean Time To Resolve (seconds)",
    buckets=[60, 300, 600, 1800, 3600, 7200, 14400],
)

# ── Status state machine ─────────────────────────────────────────────────
VALID_SEVERITIES = ("critical", "high", "medium", "low")
VALID_STATUSES = ("open", "acknowledged", "in_progress", "resolved")

# Allowed transitions: {current_status: set_of_next_statuses}
ALLOWED_TRANSITIONS: Dict[str, set] = {
    "open":         {"acknowledged", "in_progress", "resolved"},
    "acknowledged": {"in_progress", "resolved"},
    "in_progress":  {"resolved"},
    "resolved":     set(),  # terminal state — no further transitions
}


# ── Pydantic Models ───────────────────────────────────────────────────────
class IncidentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    service: str = Field(..., min_length=1, max_length=255)
    severity: str
    assigned_to: Optional[str] = None

    @field_validator("severity")
    @classmethod
    def normalise_severity(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in VALID_SEVERITIES:
            raise ValueError(f"severity must be one of {VALID_SEVERITIES}")
        return v

    @field_validator("service")
    @classmethod
    def normalise_service(cls, v: str) -> str:
        return v.strip().lower()


class IncidentUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = Field(None, max_length=5000)
    assigned_to: Optional[str] = None

    @field_validator("status")
    @classmethod
    def normalise_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.lower().strip()
            if v not in VALID_STATUSES:
                raise ValueError(f"status must be one of {VALID_STATUSES}")
        return v


class IncidentOut(BaseModel):
    id: str
    title: str
    service: str
    severity: str
    status: str
    assigned_to: Optional[str]
    alert_count: int
    created_at: str
    updated_at: str
    acknowledged_at: Optional[str]
    resolved_at: Optional[str]
    mtta_seconds: Optional[float]
    mttr_seconds: Optional[float]


class IncidentDetail(IncidentOut):
    alerts: List[Dict[str, Any]] = []
    notes: List[Dict[str, Any]] = []
    timeline: List[Dict[str, Any]] = []


class PaginatedIncidents(BaseModel):
    total: int
    page: int
    per_page: int
    incidents: List[IncidentOut]


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────
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


def _get_oncall(team: str) -> Optional[Dict]:
    try:
        with httpx.Client(timeout=3.0) as client:
            resp = client.get(
                f"{ONCALL_SERVICE_URL}/api/v1/oncall/current", params={"team": team}
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as exc:
        logger.warning("On-call service unreachable: %s", exc)
    return None


def _notify(incident_id: str, severity: str, assigned_to: str, title: str):
    """Send notification to the assigned person and also to the ops-team channel."""
    recipients = []
    if assigned_to:
        recipients.append({"recipient": assigned_to, "channel": "mock"})
    # Always notify the ops-team channel so notifications always appear
    recipients.append({"recipient": "ops-team", "channel": "slack"})

    for target in recipients:
        try:
            with httpx.Client(timeout=3.0) as client:
                client.post(
                    f"{NOTIFICATION_SERVICE_URL}/api/v1/notify",
                    json={
                        "incident_id": incident_id,
                        "channel": target["channel"],
                        "recipient": target["recipient"],
                        "message": title if title.startswith("[") else f"[{severity.upper()}] {title}",
                        "severity": severity,
                    },
                )
        except Exception as exc:
            logger.warning("Notification service unreachable: %s", exc)


def _add_timeline_event(conn, incident_id: str, event_type: str, actor: str = "system", detail: Dict = None):
    conn.execute(
        text("""
            INSERT INTO incident_timeline (id, incident_id, event_type, actor, detail, created_at)
            VALUES (:id, :iid, :etype, :actor, :detail, NOW())
        """),
        {
            "id": str(uuid.uuid4()),
            "iid": incident_id,
            "etype": event_type,
            "actor": actor,
            "detail": json.dumps(detail or {}),
        },
    )


def _fetch_linked_alerts(incident_id: str) -> List[Dict[str, Any]]:
    """Retrieve alerts linked to an incident from the alert-ingestion service (DB-per-service)."""
    try:
        with httpx.Client(timeout=3.0) as client:
            resp = client.get(
                f"{ALERT_INGESTION_URL}/api/v1/alerts",
                params={"incident_id": incident_id, "per_page": 200},
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("alerts", [])
    except Exception as exc:
        logger.warning("Alert-ingestion service unreachable: %s", exc)
    return []


# ── Lifespan ──────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(application: FastAPI):
    # Seed gauges from DB
    try:
        with engine.connect() as conn:
            for status in VALID_STATUSES:
                cnt = conn.execute(
                    text("SELECT COUNT(*) FROM incidents WHERE status = :s"), {"s": status}
                ).scalar()
                incidents_total.labels(status=status).set(cnt or 0)
        logger.info("Prometheus gauges loaded from DB")
    except Exception:
        logger.warning("Could not seed gauges — DB may not be ready yet")
    yield
    engine.dispose()
    logger.info("Shutting down — connection pool disposed")


# ── FastAPI App ───────────────────────────────────────────────────────────
app = FastAPI(
    title="Incident Management Service",
    description="Manages the full incident lifecycle from creation to resolution.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = req_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = req_id
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception")
    return JSONResponse(status_code=500, content={"error": "internal_server_error", "detail": str(exc)})


# ── Health & Metrics ──────────────────────────────────────────────────────
@app.get("/health", tags=["ops"])
def health():
    return {"status": "ok", "service": "incident-management"}


@app.get("/health/ready", tags=["ops"])
def readiness():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}")


@app.get("/metrics", tags=["ops"])
def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ── Endpoints ─────────────────────────────────────────────────────────────
@app.post("/api/v1/incidents", status_code=201, response_model=IncidentOut, tags=["incidents"])
def create_incident(body: IncidentCreate):
    """Create a new incident, look up the on-call engineer, and send notification."""
    incident_id = str(uuid.uuid4())
    assigned_to = body.assigned_to

    # Try on-call lookup
    if not assigned_to:
        oncall_data = _get_oncall(body.service)
        if oncall_data and oncall_data.get("primary"):
            assigned_to = oncall_data["primary"].get("name")

    try:
        with engine.begin() as conn:
            conn.execute(
                text(f"""
                    INSERT INTO incidents
                        (id, title, service, severity, status, assigned_to, alert_count, created_at, updated_at)
                    VALUES
                        (:id, :title, :service, :severity, 'open', :assigned_to, 0, NOW(), NOW())
                """),
                {
                    "id": incident_id,
                    "title": body.title,
                    "service": body.service,
                    "severity": body.severity,
                    "assigned_to": assigned_to,
                },
            )
            _add_timeline_event(conn, incident_id, "created", detail={
                "title": body.title, "severity": body.severity, "assigned_to": assigned_to,
            })
            if assigned_to:
                _add_timeline_event(conn, incident_id, "assigned", detail={"assigned_to": assigned_to})
    except SQLAlchemyError as exc:
        logger.error("Failed to create incident: %s", exc)
        raise HTTPException(status_code=500, detail="Database error")

    incidents_total.labels(status="open").inc()
    incidents_created_total.labels(severity=body.severity).inc()

    # Always notify — even without an assigned person, ops-team gets notified
    _notify(incident_id, body.severity, assigned_to or "", body.title)

    logger.info("Incident created id=%s service=%s severity=%s assigned=%s", incident_id, body.service, body.severity, assigned_to)

    now_iso = datetime.now(timezone.utc).isoformat()
    return IncidentOut(
        id=incident_id, title=body.title, service=body.service, severity=body.severity,
        status="open", assigned_to=assigned_to, alert_count=0,
        created_at=now_iso, updated_at=now_iso,
        acknowledged_at=None, resolved_at=None, mtta_seconds=None, mttr_seconds=None,
    )


@app.get("/api/v1/incidents", response_model=PaginatedIncidents, tags=["incidents"])
def list_incidents(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    service: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
):
    """List incidents with pagination and optional filters."""
    conditions: List[str] = []
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

    with engine.connect() as conn:
        total = conn.execute(text(f"SELECT COUNT(*) FROM incidents{where}"), params).scalar()

        params["limit"] = per_page
        params["offset"] = (page - 1) * per_page
        rows = conn.execute(
            text(f"SELECT {INCIDENT_COLS} FROM incidents{where} ORDER BY created_at DESC LIMIT :limit OFFSET :offset"),
            params,
        ).fetchall()

    return PaginatedIncidents(
        total=total, page=page, per_page=per_page,
        incidents=[IncidentOut(**_row_to_dict(r)) for r in rows],
    )


# ── Correlation Endpoints (DB-per-service support) ────────────────────────
@app.get("/api/v1/incidents/find-open", tags=["incidents"])
def find_open_incident(
    service: str = Query(...),
    severity: str = Query(...),
    window_minutes: int = Query(default=5, ge=1),
):
    """Find an open incident matching service/severity within the correlation window.
    Used by alert-ingestion to avoid direct cross-DB queries (DB-per-service pattern)."""
    with engine.connect() as conn:
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
            {"service": service.lower(), "severity": severity.lower(), "window": window_minutes},
        ).fetchone()

    if not row:
        return {"incident_id": None}
    return {"incident_id": str(row[0])}


@app.post("/api/v1/incidents/{incident_id}/link-alert", status_code=200, tags=["incidents"])
def link_alert_to_incident(incident_id: str, body: dict):
    """Increment alert_count and add a timeline event. Called by alert-ingestion
    when correlating an alert to an existing incident (DB-per-service pattern)."""
    try:
        uuid.UUID(incident_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid incident ID format")

    alert_id = body.get("alert_id", "unknown")
    fingerprint = body.get("fingerprint", "")

    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT 1 FROM incidents WHERE id = :id"), {"id": incident_id}
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Incident not found")

        conn.execute(
            text("UPDATE incidents SET alert_count = alert_count + 1 WHERE id = :id"),
            {"id": incident_id},
        )
        _add_timeline_event(conn, incident_id, "alert_correlated", actor="alert-ingestion", detail={
            "alert_id": alert_id, "fingerprint": fingerprint,
        })

    logger.info("Alert %s linked to incident %s", alert_id, incident_id)
    return {"status": "linked", "incident_id": incident_id, "alert_id": alert_id}


# ── Detail & Lifecycle Endpoints ──────────────────────────────────────────
@app.get("/api/v1/incidents/{incident_id}", response_model=IncidentDetail, tags=["incidents"])
def get_incident(incident_id: str):
    """Get incident detail with linked alerts, notes, and full timeline."""
    try:
        uuid.UUID(incident_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid incident ID format")

    with engine.connect() as conn:
        row = conn.execute(
            text(f"SELECT {INCIDENT_COLS} FROM incidents WHERE id = :id"), {"id": incident_id}
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Incident not found")

        incident = _row_to_dict(row)

        # Linked alerts — fetched from alert-ingestion service (DB-per-service)
        incident["alerts"] = _fetch_linked_alerts(incident_id)

        # Notes
        note_rows = conn.execute(
            text("SELECT id, author, content, created_at FROM incident_notes WHERE incident_id = :iid ORDER BY created_at"),
            {"iid": incident_id},
        ).fetchall()
        incident["notes"] = [
            {"id": str(n[0]), "author": n[1], "content": n[2], "created_at": n[3].isoformat() if n[3] else None}
            for n in note_rows
        ]

        # Timeline
        tl_rows = conn.execute(
            text("SELECT id, event_type, actor, detail, created_at FROM incident_timeline WHERE incident_id = :iid ORDER BY created_at"),
            {"iid": incident_id},
        ).fetchall()
        incident["timeline"] = [
            {
                "id": str(t[0]), "event_type": t[1], "actor": t[2],
                "detail": t[3] if isinstance(t[3], dict) else json.loads(t[3] or "{}"),
                "created_at": t[4].isoformat() if t[4] else None,
            }
            for t in tl_rows
        ]

    return IncidentDetail(**incident)


@app.patch("/api/v1/incidents/{incident_id}", response_model=IncidentOut, tags=["incidents"])
def update_incident(incident_id: str, body: IncidentUpdate):
    """
    Update an incident's status or add notes.
    Enforces the status state machine and auto-computes MTTA / MTTR.
    """
    try:
        uuid.UUID(incident_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid incident ID format")

    with engine.begin() as conn:
        row = conn.execute(
            text(f"SELECT {INCIDENT_COLS} FROM incidents WHERE id = :id"), {"id": incident_id}
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Incident not found")

        current = _row_to_dict(row)
        now = datetime.now(timezone.utc)
        updates: List[str] = []
        params: Dict[str, Any] = {"id": incident_id}

        # ── Reassignment ──
        if body.assigned_to is not None and body.assigned_to != current["assigned_to"]:
            updates.append("assigned_to = :assigned_to")
            params["assigned_to"] = body.assigned_to
            _add_timeline_event(conn, incident_id, "assigned", detail={
                "previous": current["assigned_to"], "new": body.assigned_to,
            })

        # ── Status transition ──
        if body.status and body.status != current["status"]:
            old_status = current["status"]
            new_status = body.status

            # Enforce state machine
            allowed = ALLOWED_TRANSITIONS.get(old_status, set())
            if new_status not in allowed:
                raise HTTPException(
                    status_code=409,
                    detail=f"Cannot transition from '{old_status}' to '{new_status}'. "
                           f"Allowed: {sorted(allowed) if allowed else 'none (terminal state)'}",
                )

            updates.append("status = :status")
            params["status"] = new_status

            # Gauge bookkeeping
            incidents_total.labels(status=old_status).dec()
            incidents_total.labels(status=new_status).inc()

            # MTTA: first time entering acknowledged or in_progress
            if new_status in ("acknowledged", "in_progress") and current["acknowledged_at"] is None:
                updates.append("acknowledged_at = :ack_at")
                params["ack_at"] = now
                created = datetime.fromisoformat(current["created_at"])
                mtta = (now - created).total_seconds()
                updates.append("mtta_seconds = :mtta")
                params["mtta"] = mtta
                incident_mtta_seconds.observe(mtta)
                logger.info("MTTA recorded incident=%s seconds=%.1f", incident_id, mtta)

            # MTTR: resolved
            if new_status == "resolved" and current["resolved_at"] is None:
                updates.append("resolved_at = :res_at")
                params["res_at"] = now
                created = datetime.fromisoformat(current["created_at"])
                mttr = (now - created).total_seconds()
                updates.append("mttr_seconds = :mttr")
                params["mttr"] = mttr
                incident_mttr_seconds.observe(mttr)
                logger.info("MTTR recorded incident=%s seconds=%.1f", incident_id, mttr)

                # If never acknowledged, set MTTA = MTTR (auto-ack on resolve)
                if current["acknowledged_at"] is None and "acknowledged_at = :ack_at" not in " ".join(updates):
                    updates.append("acknowledged_at = :ack_at2")
                    params["ack_at2"] = now
                    updates.append("mtta_seconds = :mtta2")
                    params["mtta2"] = mttr
                    incident_mtta_seconds.observe(mttr)

            _add_timeline_event(conn, incident_id, new_status, detail={
                "from": old_status, "to": new_status,
            })

        # ── Add note ──
        if body.notes:
            note_id = str(uuid.uuid4())
            author = body.assigned_to or current.get("assigned_to") or "system"
            conn.execute(
                text("""
                    INSERT INTO incident_notes (id, incident_id, author, content, created_at)
                    VALUES (:nid, :iid, :author, :content, :ts)
                """),
                {"nid": note_id, "iid": incident_id, "author": author, "content": body.notes, "ts": now},
            )
            _add_timeline_event(conn, incident_id, "note_added", actor=author, detail={
                "note_id": note_id, "preview": body.notes[:100],
            })

        if updates:
            conn.execute(text(f"UPDATE incidents SET {', '.join(updates)} WHERE id = :id"), params)

        # Fetch updated row within same transaction
        updated_row = conn.execute(
            text(f"SELECT {INCIDENT_COLS} FROM incidents WHERE id = :id"), {"id": incident_id}
        ).fetchone()

    return IncidentOut(**_row_to_dict(updated_row))


@app.get("/api/v1/incidents/{incident_id}/metrics", tags=["incidents"])
def get_incident_metrics(incident_id: str):
    """Get the SRE metrics (MTTA / MTTR) for a specific incident."""
    try:
        uuid.UUID(incident_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid incident ID format")
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT mtta_seconds, mttr_seconds, status, created_at, acknowledged_at, resolved_at FROM incidents WHERE id = :id"),
            {"id": incident_id},
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {
        "incident_id": incident_id,
        "mtta_seconds": row[0],
        "mttr_seconds": row[1],
        "status": row[2],
        "created_at": row[3].isoformat() if row[3] else None,
        "acknowledged_at": row[4].isoformat() if row[4] else None,
        "resolved_at": row[5].isoformat() if row[5] else None,
    }


@app.post("/api/v1/incidents/{incident_id}/notes", status_code=201, tags=["incidents"])
def add_incident_note(incident_id: str, body: dict):
    """Add a note/comment to an existing incident."""
    try:
        uuid.UUID(incident_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid incident ID format")

    author = body.get("author", "anonymous")
    content = body.get("content", "")
    if not content or not content.strip():
        raise HTTPException(status_code=422, detail="Note content cannot be empty")

    note_id = str(uuid.uuid4())
    with engine.begin() as conn:
        # Verify incident exists
        exists = conn.execute(
            text("SELECT 1 FROM incidents WHERE id = :id"), {"id": incident_id}
        ).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="Incident not found")

        conn.execute(
            text("""
                INSERT INTO incident_notes (id, incident_id, author, content, created_at)
                VALUES (:id, :iid, :author, :content, NOW())
            """),
            {"id": note_id, "iid": incident_id, "author": author, "content": content.strip()},
        )
        _add_timeline_event(conn, incident_id, "note_added", actor=author, detail={
            "note_id": note_id, "preview": content[:100],
        })

    logger.info("Note %s added to incident %s by %s", note_id, incident_id, author)
    return {"id": note_id, "incident_id": incident_id, "author": author, "content": content.strip()}


@app.get("/api/v1/incidents/{incident_id}/timeline", tags=["incidents"])
def get_incident_timeline(incident_id: str):
    """Get the full audit timeline for an incident."""
    try:
        uuid.UUID(incident_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid incident ID format")

    with engine.connect() as conn:
        # Verify incident exists
        exists = conn.execute(
            text("SELECT 1 FROM incidents WHERE id = :id"), {"id": incident_id}
        ).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="Incident not found")

        rows = conn.execute(
            text("SELECT id, event_type, actor, detail, created_at FROM incident_timeline WHERE incident_id = :iid ORDER BY created_at"),
            {"iid": incident_id},
        ).fetchall()

    timeline = [
        {
            "id": str(r[0]),
            "event_type": r[1],
            "actor": r[2],
            "detail": r[3] if isinstance(r[3], dict) else json.loads(r[3]) if r[3] else {},
            "created_at": r[4].isoformat() if r[4] else None,
        }
        for r in rows
    ]
    return {"incident_id": incident_id, "total": len(timeline), "timeline": timeline}


@app.get("/api/v1/incidents/stats/summary", tags=["incidents"])
def get_summary_stats():
    """Aggregated dashboard stats — counts, avg MTTA, avg MTTR."""
    with engine.connect() as conn:
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
        "open": row[0] or 0,
        "acknowledged": row[1] or 0,
        "in_progress": row[2] or 0,
        "resolved": row[3] or 0,
        "avg_mtta_seconds": float(row[4]) if row[4] else None,
        "avg_mttr_seconds": float(row[5]) if row[5] else None,
    }


# ── Entrypoint ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002, log_level="info")
