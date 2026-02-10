# type: ignore
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
"""
Alert Ingestion Service
=======================
Receives alerts from external monitoring systems, validates them, computes a
deduplication fingerprint, correlates into existing or new incidents, and
exposes Prometheus metrics.

Port: 8001
"""
import hashlib
import json
import os
import uuid
import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field, field_validator
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# ── Configuration ──────────────────────────────────────────────────────────
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://hackathon:hackathon2026@alert-db:5432/alert_db",
)
INCIDENT_MANAGEMENT_URL = os.getenv(
    "INCIDENT_MANAGEMENT_URL", "http://incident-management:8002"
)
NOTIFICATION_SERVICE_URL = os.getenv(
    "NOTIFICATION_SERVICE_URL", "http://notification-service:8004"
)
CORRELATION_WINDOW_MINUTES = int(os.getenv("CORRELATION_WINDOW_MINUTES", "5"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# ── Structured JSON Logger ─────────────────────────────────────────────────
class _JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": "alert-ingestion",
            "msg": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1]:
            log_obj["exception"] = str(record.exc_info[1])
        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id
        return json.dumps(log_obj)


_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(_JSONFormatter())
logger = logging.getLogger("alert-ingestion")
logger.handlers = [_handler]
logger.setLevel(LOG_LEVEL)

# ── Database (synchronous — perfectly fine for FastAPI sync endpoints) ─────
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=5,
    pool_recycle=300,
)

# ── Prometheus Metrics ────────────────────────────────────────────────────
alerts_received_total = Counter(
    "alerts_received_total",
    "Total alerts received by severity",
    ["severity"],
)
alerts_correlated_total = Counter(
    "alerts_correlated_total",
    "Alert correlation outcomes",
    ["result"],  # new_incident | existing_incident
)
alert_processing_seconds = Histogram(
    "alert_processing_seconds",
    "Time taken to process a single alert end-to-end",
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
)

# ── Pydantic Models ───────────────────────────────────────────────────────
VALID_SEVERITIES = ("critical", "high", "medium", "low")


class AlertIn(BaseModel):
    """Inbound alert payload."""
    service: str = Field(..., min_length=1, max_length=255, examples=["frontend-api"])
    severity: str = Field(..., examples=["high"])
    message: str = Field(..., min_length=1, max_length=2000, examples=["HTTP 5xx rate > 10 %"])
    labels: Dict[str, Any] = Field(default_factory=dict)
    source: str = Field(default="api", max_length=255)
    timestamp: Optional[str] = None

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


class AlertOut(BaseModel):
    """Response after ingesting an alert."""
    alert_id: str
    incident_id: Optional[str] = None
    fingerprint: str
    status: str
    action: str   # new_incident | existing_incident


class AlertDetail(BaseModel):
    id: str
    service: str
    severity: str
    message: str
    source: str
    labels: Dict[str, Any]
    fingerprint: Optional[str]
    timestamp: Optional[str]
    incident_id: Optional[str]
    created_at: str


class PaginatedAlerts(BaseModel):
    total: int
    page: int
    per_page: int
    alerts: List[AlertDetail]


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    request_id: Optional[str] = None


# ── Lifespan ──────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(application: FastAPI):
    """Verify DB connectivity at startup; dispose pool on shutdown."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection verified")
    except Exception as exc:
        logger.error("Database connection FAILED — service will start but DB calls will fail: %s", exc)
    yield
    engine.dispose()
    logger.info("Database connection pool disposed — shutting down")


# ── FastAPI App ───────────────────────────────────────────────────────────
app = FastAPI(
    title="Alert Ingestion Service",
    description="Receives, deduplicates, and correlates alerts into incidents.",
    version="1.0.0",
    lifespan=lifespan,
    responses={
        422: {"model": ErrorResponse, "description": "Validation error"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Middleware: Request-ID injection ──────────────────────────────────────
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = req_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = req_id
    return response


# ── Global exception handler ─────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    req_id = getattr(request.state, "request_id", None)
    logger.exception("Unhandled exception", extra={"request_id": req_id})
    return JSONResponse(
        status_code=500,
        content={"error": "internal_server_error", "detail": str(exc), "request_id": req_id},
    )


# ── Health & Metrics ──────────────────────────────────────────────────────
@app.get("/health", tags=["ops"])
def health():
    """Shallow health check—confirms the process is alive."""
    return {"status": "ok", "service": "alert-ingestion"}


@app.get("/health/ready", tags=["ops"])
def readiness():
    """Deep health check—confirms DB connectivity."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}")


@app.get("/metrics", tags=["ops"])
def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ── Helpers ───────────────────────────────────────────────────────────────
def _compute_fingerprint(service: str, severity: str, message: str) -> str:
    """SHA-256 fingerprint for deduplication (service + severity + first 100 chars of message)."""
    raw = f"{service}|{severity}|{message[:100]}".lower()
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _find_existing_incident(service: str, severity: str) -> Optional[str]:
    """Ask incident-management for an open incident matching the correlation window (DB-per-service)."""
    try:
        with httpx.Client(timeout=3.0) as client:
            resp = client.get(
                f"{INCIDENT_MANAGEMENT_URL}/api/v1/incidents/find-open",
                params={
                    "service": service,
                    "severity": severity,
                    "window_minutes": CORRELATION_WINDOW_MINUTES,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("incident_id")  # None if no match
    except Exception as exc:
        logger.warning("Incident-management unreachable (find-open): %s", exc)
    return None


def _create_incident_remote(service: str, severity: str, message: str) -> Optional[str]:
    """Ask the Incident Management Service to create the incident."""
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.post(
                f"{INCIDENT_MANAGEMENT_URL}/api/v1/incidents",
                json={
                    "title": f"[{severity.upper()}] {service}: {message[:120]}",
                    "service": service,
                    "severity": severity,
                },
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                return data.get("id") or data.get("incident_id")
            logger.warning("Incident-management returned %s: %s", resp.status_code, resp.text[:200])
    except Exception as exc:
        logger.warning("Incident-management unreachable: %s", exc)
    return None


def _link_alert_to_incident(incident_id: str, alert_id: str, fingerprint: str):
    """Tell incident-management to bump alert_count and add timeline event (DB-per-service)."""
    try:
        with httpx.Client(timeout=3.0) as client:
            client.post(
                f"{INCIDENT_MANAGEMENT_URL}/api/v1/incidents/{incident_id}/link-alert",
                json={"alert_id": alert_id, "fingerprint": fingerprint},
            )
    except Exception as exc:
        logger.warning("Failed to link alert to incident %s: %s", incident_id, exc)


def _notify_alert(incident_id: str, severity: str, service: str, message: str):
    """Send a notification when an alert is correlated to an existing incident."""
    try:
        with httpx.Client(timeout=3.0) as client:
            client.post(
                f"{NOTIFICATION_SERVICE_URL}/api/v1/notify",
                json={
                    "incident_id": incident_id,
                    "channel": "mock",
                    "recipient": "ops-team",
                    "message": f"[ALERT CORRELATED] [{severity.upper()}] {service}: {message[:120]}",
                    "severity": severity,
                },
            )
    except Exception as exc:
        logger.warning("Notification service unreachable: %s", exc)


# ── Endpoints ─────────────────────────────────────────────────────────────
@app.post(
    "/api/v1/alerts",
    response_model=AlertOut,
    status_code=201,
    tags=["alerts"],
    summary="Ingest a new alert",
    responses={201: {"description": "Alert accepted and correlated"}},
)
def create_alert(alert: AlertIn, request: Request):
    """Receive a new alert, correlate it to an existing or new incident.
    
    DB-per-service: alert-ingestion only writes to its own alert_db.
    Incident correlation and linking happens via HTTP to incident-management.
    """
    with alert_processing_seconds.time():
        severity = alert.severity
        service = alert.service
        ts = alert.timestamp or datetime.now(timezone.utc).isoformat()
        fingerprint = _compute_fingerprint(service, severity, alert.message)

        alerts_received_total.labels(severity=severity).inc()

        alert_id = str(uuid.uuid4())
        incident_id: Optional[str] = None
        action = "new_incident"

        # ── Correlation via HTTP (DB-per-service) ──
        existing = _find_existing_incident(service, severity)

        if existing:
            incident_id = existing
            action = "existing_incident"
            _link_alert_to_incident(incident_id, alert_id, fingerprint)
        else:
            incident_id = _create_incident_remote(service, severity, alert.message)
            if incident_id:
                _link_alert_to_incident(incident_id, alert_id, fingerprint)
            else:
                logger.warning("Could not create incident for alert %s — stored without incident link", alert_id)

        # ── Store alert in own database (alert_db) ──
        try:
            with engine.begin() as conn:
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
                        "message": alert.message,
                        "source": alert.source,
                        "labels": json.dumps(alert.labels),
                        "fp": fingerprint,
                        "ts": ts,
                        "incident_id": incident_id,
                    },
                )
        except SQLAlchemyError as exc:
            logger.error("Database error while storing alert: %s", exc)
            raise HTTPException(status_code=500, detail="Database error while processing alert")

        alerts_correlated_total.labels(result=action).inc()

        # Send notification for correlated alerts (new incidents already notify via incident-management)
        if action == "existing_incident" and incident_id:
            _notify_alert(incident_id, severity, service, alert.message)

        logger.info(
            "Alert processed alert_id=%s incident_id=%s action=%s fingerprint=%s",
            alert_id, incident_id, action, fingerprint,
        )

        return AlertOut(
            alert_id=alert_id,
            incident_id=incident_id,
            fingerprint=fingerprint,
            status="accepted",
            action=action,
        )


@app.get(
    "/api/v1/alerts/{alert_id}",
    response_model=AlertDetail,
    tags=["alerts"],
    summary="Get a single alert by ID",
)
def get_alert(alert_id: str):
    try:
        uuid.UUID(alert_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid alert ID format")

    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT id, service, severity, message, source, labels,
                       fingerprint, timestamp, incident_id, created_at
                FROM alerts WHERE id = :id
            """),
            {"id": alert_id},
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Alert not found")

    return AlertDetail(
        id=str(row[0]),
        service=row[1],
        severity=row[2],
        message=row[3],
        source=row[4] or "api",
        labels=row[5] if isinstance(row[5], dict) else json.loads(row[5] or "{}"),
        fingerprint=row[6],
        timestamp=row[7].isoformat() if row[7] else None,
        incident_id=str(row[8]) if row[8] else None,
        created_at=row[9].isoformat() if row[9] else "",
    )


@app.get(
    "/api/v1/alerts",
    response_model=PaginatedAlerts,
    tags=["alerts"],
    summary="List alerts with pagination and filters",
)
def list_alerts(
    service: Optional[str] = None,
    severity: Optional[str] = None,
    incident_id: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
):
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

    with engine.connect() as conn:
        # Total count
        total = conn.execute(text(f"SELECT COUNT(*) FROM alerts{where}"), params).scalar()

        # Page of results
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
        AlertDetail(
            id=str(r[0]),
            service=r[1],
            severity=r[2],
            message=r[3],
            source=r[4] or "api",
            labels=r[5] if isinstance(r[5], dict) else json.loads(r[5] or "{}"),
            fingerprint=r[6],
            timestamp=r[7].isoformat() if r[7] else None,
            incident_id=str(r[8]) if r[8] else None,
            created_at=r[9].isoformat() if r[9] else "",
        )
        for r in rows
    ]

    return PaginatedAlerts(total=total, page=page, per_page=per_page, alerts=alerts)


# ── Entrypoint ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
