# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""
On-Call Service v2.1.0 — Microservice de gestion des astreintes
Manages on-call schedules, rotations, escalations, overrides, and audit history.

Endpoints:
    GET  /health                       — Liveness probe
    GET  /health/ready                 — Readiness probe
    GET  /metrics                      — Prometheus metrics
    POST /api/v1/schedules             — Create a schedule
    GET  /api/v1/schedules             — List all schedules
    GET  /api/v1/schedules/{team}      — Get a team schedule
    PATCH /api/v1/schedules/{team}     — Update a team schedule
    DELETE /api/v1/schedules/{team}    — Delete a team schedule
    GET  /api/v1/oncall/current        — Get current on-call for a team
    POST /api/v1/oncall/override       — Set a temporary override
    DELETE /api/v1/oncall/override/{team} — Remove override
    GET  /api/v1/oncall/overrides      — List active overrides
    POST /api/v1/escalate              — Trigger an escalation
    GET  /api/v1/escalations           — List escalation history
    GET  /api/v1/oncall/history        — Audit log
    GET  /api/v1/teams                 — Teams overview
    GET  /api/v1/oncall/stats          — Operational stats
"""

import json
import logging
import os
import sys
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from starlette.responses import Response


# ============================================================
# Configuration (all env-driven, zero hardcode)
# ============================================================
SERVICE_NAME: str = os.getenv("SERVICE_NAME", "oncall-service")
SERVICE_VERSION: str = os.getenv("SERVICE_VERSION", "2.1.0")
SERVICE_PORT: int = int(os.getenv("SERVICE_PORT", "8003"))
NOTIFICATION_SERVICE_URL: str = os.getenv(
    "NOTIFICATION_SERVICE_URL", "http://notification-service:8004"
)
NOTIFICATION_TIMEOUT: float = float(os.getenv("NOTIFICATION_TIMEOUT", "3.0"))
DEFAULT_OVERRIDE_HOURS: int = int(os.getenv("DEFAULT_OVERRIDE_HOURS", "8"))
DEFAULT_ESCALATION_LIMIT: int = int(os.getenv("DEFAULT_ESCALATION_LIMIT", "50"))
DEFAULT_HISTORY_LIMIT: int = int(os.getenv("DEFAULT_HISTORY_LIMIT", "100"))
MAX_HISTORY_SIZE: int = int(os.getenv("MAX_HISTORY_SIZE", "10000"))
MAX_ESCALATION_LOG_SIZE: int = int(os.getenv("MAX_ESCALATION_LOG_SIZE", "5000"))
CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "*").split(",")
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
SEED_DEFAULT_SCHEDULES: bool = (
    os.getenv("SEED_DEFAULT_SCHEDULES", "true").lower() == "true"
)


# ============================================================
# Structured JSON Logging
# ============================================================
class JSONFormatter(logging.Formatter):
    """Emit every log record as a single JSON line for machine parsing."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": SERVICE_NAME,
            "message": record.getMessage(),
        }
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id  # type: ignore[attr-defined]
        if record.exc_info and record.exc_info[1]:
            log_data["error"] = str(record.exc_info[1])
            log_data["error_type"] = type(record.exc_info[1]).__name__
        return json.dumps(log_data)


logger = logging.getLogger(SERVICE_NAME)
logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(JSONFormatter())
logger.handlers = [_handler]
logger.propagate = False


# ============================================================
# Prometheus Metrics
# ============================================================
REQUEST_COUNT = Counter(
    "oncall_requests_total",
    "Total HTTP requests to on-call service",
    ["method", "endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "oncall_request_duration_seconds",
    "Request latency in seconds",
    ["method", "endpoint"],
)
NOTIFICATIONS_SENT = Counter(
    "oncall_notifications_sent_total",
    "Total notifications sent",
    ["channel"],
)
ESCALATIONS_TOTAL = Counter(
    "oncall_escalations_total",
    "Total escalations triggered",
    ["team"],
)
SCHEDULES_CREATED = Counter(
    "oncall_schedules_created_total",
    "Total schedules created",
)
ONCALL_LOOKUPS = Counter(
    "oncall_lookups_total",
    "Total on-call lookups performed",
    ["team"],
)
HTTP_ERRORS = Counter(
    "oncall_http_errors_total",
    "Total HTTP error responses",
    ["method", "endpoint", "status"],
)
ACTIVE_SCHEDULES = Gauge(
    "oncall_active_schedules",
    "Number of active on-call schedules",
)
OVERRIDES_ACTIVE = Gauge(
    "oncall_overrides_active",
    "Number of currently active overrides",
)
ROTATION_CHANGES = Counter(
    "oncall_rotation_changes_total",
    "Total rotation changes detected",
    ["team"],
)


# ============================================================
# Data Models (Pydantic v2)
# ============================================================
class Member(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Member name")
    email: str = Field(..., min_length=1, max_length=255, description="Member email")
    role: str = Field(
        ..., pattern="^(primary|secondary)$", description="Role: primary or secondary"
    )


class ScheduleCreate(BaseModel):
    team: str = Field(..., min_length=1, max_length=255, description="Team name")
    rotation_type: str = Field(
        default="weekly",
        pattern="^(weekly|daily|biweekly)$",
        description="Rotation type",
    )
    members: list[Member] = Field(
        ..., min_length=1, description="List of on-call members"
    )


class ScheduleUpdate(BaseModel):
    """Partial update model for PATCH /api/v1/schedules/{team}."""

    rotation_type: Optional[str] = Field(
        default=None,
        pattern="^(weekly|daily|biweekly)$",
        description="New rotation type",
    )
    add_members: Optional[list[Member]] = Field(
        default=None, description="Members to add"
    )
    remove_members: Optional[list[str]] = Field(
        default=None, description="Member names to remove"
    )


class ScheduleResponse(BaseModel):
    id: str
    team: str
    rotation_type: str
    members: list[dict]
    created_at: str
    updated_at: Optional[str] = None


class OnCallCurrent(BaseModel):
    team: str
    primary: dict
    secondary: Optional[dict] = None
    schedule_id: str
    rotation_type: str


class EscalationRequest(BaseModel):
    team: str = Field(..., min_length=1)
    incident_id: str = Field(..., min_length=1)
    reason: Optional[str] = "No acknowledgment within SLA"


class EscalationResponse(BaseModel):
    status: str
    escalation_id: str
    team: str
    incident_id: str
    escalated_to: Optional[dict] = None
    message: str
    timestamp: str


class OverrideRequest(BaseModel):
    team: str = Field(..., min_length=1)
    user_name: str = Field(..., min_length=1)
    user_email: str = Field(..., min_length=1)
    reason: Optional[str] = "Manual override"
    duration_hours: Optional[int] = Field(
        default=None,
        ge=1,
        le=168,
        description="Override duration in hours (1-168)",
    )


# ============================================================
# In-Memory Storage
# ============================================================
schedules_db: dict[str, dict[str, Any]] = {}
overrides_db: dict[str, dict[str, Any]] = {}
escalation_log: list[dict[str, Any]] = []
oncall_history: list[dict[str, Any]] = []
last_known_oncall: dict[str, str] = {}


# ============================================================
# Helper: Record History Event (bounded ring buffer)
# ============================================================
def record_event(
    event_type: str, team: str, details: dict[str, Any]
) -> dict[str, Any]:
    """Append an event to the on-call audit log, trimming oldest if over max."""
    event: dict[str, Any] = {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "team": team,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "details": details,
    }
    oncall_history.append(event)
    if len(oncall_history) > MAX_HISTORY_SIZE:
        del oncall_history[: len(oncall_history) - MAX_HISTORY_SIZE]
    return event


# ============================================================
# Helper: Cleanup Expired Overrides
# ============================================================
def cleanup_expired_overrides() -> None:
    """Remove all expired overrides and log them."""
    now = datetime.now(timezone.utc)
    expired_teams = [
        team
        for team, ov in overrides_db.items()
        if "expires_at" in ov and datetime.fromisoformat(ov["expires_at"]) <= now
    ]
    for team in expired_teams:
        override = overrides_db.pop(team)
        record_event(
            "override_expired",
            team,
            {
                "user_name": override["user_name"],
                "expired_at": override["expires_at"],
            },
        )
        logger.info(
            "Override expired: team=%s, user=%s", team, override["user_name"]
        )
    if expired_teams:
        OVERRIDES_ACTIVE.set(len(overrides_db))


# ============================================================
# Helper: Compute Rotation (weekly / daily / biweekly)
# ============================================================
def compute_rotation(
    schedule: dict[str, Any],
) -> tuple[dict[str, str] | None, dict[str, str] | None]:
    """Return (current_primary, current_secondary) based on rotation logic."""
    members = schedule["members"]
    primary_members = [m for m in members if m["role"] == "primary"]
    secondary_members = [m for m in members if m["role"] == "secondary"]

    if not primary_members:
        return None, None

    now = datetime.now(timezone.utc)
    if schedule["rotation_type"] == "daily":
        rotation_index = now.timetuple().tm_yday
    elif schedule["rotation_type"] == "biweekly":
        rotation_index = now.isocalendar()[1] // 2
    else:  # weekly (default)
        rotation_index = now.isocalendar()[1]

    current_primary = primary_members[rotation_index % len(primary_members)]
    current_secondary = None
    if secondary_members:
        current_secondary = secondary_members[rotation_index % len(secondary_members)]

    return current_primary, current_secondary


# ============================================================
# Inter-Service: Notification (sync, fire & forget)
# ============================================================
def notify_service(
    channel: str, recipient: str, message: str, incident_id: str = "N/A"
) -> None:
    """Send a notification via the notification-service."""
    try:
        with httpx.Client(timeout=NOTIFICATION_TIMEOUT) as client:
            resp = client.post(
                f"{NOTIFICATION_SERVICE_URL}/api/v1/notify",
                json={
                    "channel": channel,
                    "recipient": recipient,
                    "message": message,
                    "incident_id": incident_id,
                },
            )
        NOTIFICATIONS_SENT.labels(channel=channel).inc()
        logger.info(
            "Notification sent: recipient=%s, channel=%s, status=%d",
            recipient,
            channel,
            resp.status_code,
        )
    except Exception as exc:
        logger.warning("Notification failed: %s", exc)


# ============================================================
# Startup: Seed Default Schedules
# ============================================================
async def seed_default_schedules() -> None:
    """Create default schedules so the service is usable immediately."""
    default_schedules = [
        {
            "team": "platform-engineering",
            "rotation_type": "weekly",
            "members": [
                {
                    "name": "Alice Martin",
                    "email": "alice@company.com",
                    "role": "primary",
                },
                {
                    "name": "Bob Dupont",
                    "email": "bob@company.com",
                    "role": "primary",
                },
                {
                    "name": "Carol Chen",
                    "email": "carol@company.com",
                    "role": "secondary",
                },
            ],
        },
        {
            "team": "backend",
            "rotation_type": "weekly",
            "members": [
                {
                    "name": "David Kumar",
                    "email": "david@company.com",
                    "role": "primary",
                },
                {
                    "name": "Eve Johnson",
                    "email": "eve@company.com",
                    "role": "secondary",
                },
            ],
        },
        {
            "team": "frontend",
            "rotation_type": "daily",
            "members": [
                {
                    "name": "Frank Wilson",
                    "email": "frank@company.com",
                    "role": "primary",
                },
                {
                    "name": "Grace Lee",
                    "email": "grace@company.com",
                    "role": "secondary",
                },
            ],
        },
        {
            "team": "infrastructure",
            "rotation_type": "biweekly",
            "members": [
                {
                    "name": "Hank Brown",
                    "email": "hank@company.com",
                    "role": "primary",
                },
                {
                    "name": "Ivy Davis",
                    "email": "ivy@company.com",
                    "role": "primary",
                },
                {
                    "name": "Jack White",
                    "email": "jack@company.com",
                    "role": "secondary",
                },
            ],
        },
    ]

    for sd in default_schedules:
        schedule_id = str(uuid.uuid4())
        schedules_db[sd["team"]] = {
            "id": schedule_id,
            "team": sd["team"],
            "rotation_type": sd["rotation_type"],
            "members": sd["members"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": None,
        }
        record_event(
            "schedule_created",
            sd["team"],
            {
                "members_count": len(sd["members"]),
                "rotation_type": sd["rotation_type"],
                "source": "seed",
            },
        )

    logger.info("Seeded %d default on-call schedules", len(default_schedules))
    ACTIVE_SCHEDULES.set(len(schedules_db))


# ============================================================
# Lifespan
# ============================================================
@asynccontextmanager
async def lifespan(application: FastAPI):
    """Seed defaults on startup, clean up on shutdown."""
    if SEED_DEFAULT_SCHEDULES:
        await seed_default_schedules()
    yield


# ============================================================
# Application
# ============================================================
app = FastAPI(
    title="On-Call Service",
    description=(
        "Manages on-call schedules, rotations, escalations, "
        "overrides, and audit history."
    ),
    version=SERVICE_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------ Global Exception Handler ------
@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Catch-all for unhandled exceptions — returns a clean 500."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "request_id": request_id},
    )


# ------ HTTP Metrics Middleware ------
KNOWN_SEGMENTS: set[str] = {
    "api", "v1", "schedules", "oncall", "current", "override",
    "overrides", "escalate", "escalations", "teams", "health",
    "metrics", "history", "stats", "ready",
}


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Track request count, latency, and error rate via Prometheus."""
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start

    path = request.url.path
    parts = path.strip("/").split("/")
    normalized = (
        "/" + "/".join(p if p in KNOWN_SEGMENTS else "{param}" for p in parts)
        if parts != [""]
        else path
    )

    skip = ("/health", "/health/ready", "/metrics", "/openapi.json", "/docs", "/redoc")
    if path not in skip:
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=normalized,
            status=str(response.status_code),
        ).inc()
        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=normalized,
        ).observe(duration)
        if response.status_code >= 400:
            HTTP_ERRORS.labels(
                method=request.method,
                endpoint=normalized,
                status=str(response.status_code),
            ).inc()

    return response


# ------ Request-ID Middleware ------
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Propagate or generate X-Request-ID for distributed tracing."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ============================================================
# Health & System Endpoints
# ============================================================
@app.get("/health", tags=["System"])
def health_check():
    """Liveness probe for Docker and orchestration."""
    cleanup_expired_overrides()
    return {
        "status": "ok",
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "schedules_count": len(schedules_db),
        "active_overrides": len(overrides_db),
    }


@app.get("/health/ready", tags=["System"])
def readiness_check():
    """Readiness probe — verifies the service can serve traffic."""
    return {
        "status": "ready",
        "service": SERVICE_NAME,
        "schedules_loaded": len(schedules_db) > 0,
    }


@app.get("/metrics", tags=["System"])
def prometheus_metrics():
    """Expose Prometheus metrics in OpenMetrics format."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ============================================================
# Schedule CRUD
# ============================================================
@app.post(
    "/api/v1/schedules",
    status_code=201,
    response_model=ScheduleResponse,
    tags=["Schedules"],
)
def create_schedule(schedule: ScheduleCreate):
    """Create (or replace) an on-call schedule for a team."""
    primary_members = [m for m in schedule.members if m.role == "primary"]
    if not primary_members:
        raise HTTPException(
            status_code=400,
            detail="At least one member with role 'primary' is required",
        )

    schedule_id = str(uuid.uuid4())
    schedule_record: dict[str, Any] = {
        "id": schedule_id,
        "team": schedule.team,
        "rotation_type": schedule.rotation_type,
        "members": [m.model_dump() for m in schedule.members],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": None,
    }
    schedules_db[schedule.team] = schedule_record

    SCHEDULES_CREATED.inc()
    ACTIVE_SCHEDULES.set(len(schedules_db))
    record_event(
        "schedule_created",
        schedule.team,
        {
            "members_count": len(schedule.members),
            "rotation_type": schedule.rotation_type,
        },
    )
    logger.info(
        "Schedule created: team=%s, members=%d",
        schedule.team,
        len(schedule.members),
    )
    return schedule_record


@app.get("/api/v1/schedules", tags=["Schedules"])
def list_schedules():
    """List all on-call schedules."""
    return list(schedules_db.values())


@app.get(
    "/api/v1/schedules/{team}",
    response_model=ScheduleResponse,
    tags=["Schedules"],
)
def get_schedule(team: str):
    """Get a specific team's on-call schedule."""
    if team not in schedules_db:
        raise HTTPException(
            status_code=404, detail=f"No schedule found for team '{team}'"
        )
    return schedules_db[team]


@app.patch(
    "/api/v1/schedules/{team}",
    response_model=ScheduleResponse,
    tags=["Schedules"],
)
def update_schedule(team: str, update: ScheduleUpdate):
    """Partially update a team's schedule (rotation type, add/remove members)."""
    if team not in schedules_db:
        raise HTTPException(
            status_code=404, detail=f"No schedule found for team '{team}'"
        )

    schedule = schedules_db[team]
    changes: dict[str, Any] = {}

    # Update rotation type
    if update.rotation_type is not None:
        changes["rotation_type"] = {
            "old": schedule["rotation_type"],
            "new": update.rotation_type,
        }
        schedule["rotation_type"] = update.rotation_type

    # Add members (skip duplicates by name)
    if update.add_members:
        existing_names = {m["name"] for m in schedule["members"]}
        added: list[str] = []
        for member in update.add_members:
            if member.name not in existing_names:
                schedule["members"].append(member.model_dump())
                added.append(member.name)
        if added:
            changes["added_members"] = added

    # Remove members
    if update.remove_members:
        before_count = len(schedule["members"])
        schedule["members"] = [
            m
            for m in schedule["members"]
            if m["name"] not in update.remove_members
        ]
        removed = before_count - len(schedule["members"])
        if removed > 0:
            changes["removed_members"] = update.remove_members[:removed]

    # Validate at least one primary remains
    primary_remaining = [
        m for m in schedule["members"] if m["role"] == "primary"
    ]
    if not primary_remaining:
        raise HTTPException(
            status_code=400,
            detail="Cannot remove all primary members. At least one primary is required.",
        )

    schedule["updated_at"] = datetime.now(timezone.utc).isoformat()
    if changes:
        record_event("schedule_updated", team, changes)
        logger.info(
            "Schedule updated: team=%s, changes=%s", team, list(changes.keys())
        )
    return schedule


@app.delete("/api/v1/schedules/{team}", tags=["Schedules"])
def delete_schedule(team: str):
    """Delete a team's on-call schedule."""
    if team not in schedules_db:
        raise HTTPException(
            status_code=404, detail=f"No schedule found for team '{team}'"
        )

    del schedules_db[team]
    overrides_db.pop(team, None)
    last_known_oncall.pop(team, None)
    ACTIVE_SCHEDULES.set(len(schedules_db))
    OVERRIDES_ACTIVE.set(len(overrides_db))
    record_event("schedule_deleted", team, {})
    logger.info("Schedule deleted: team=%s", team)
    return {"status": "deleted", "team": team}


# ============================================================
# On-Call Current
# ============================================================
@app.get(
    "/api/v1/oncall/current",
    response_model=OnCallCurrent,
    tags=["On-Call"],
)
def get_current_oncall(
    team: str = Query(..., description="Team name to query"),
):
    """
    Get the current on-call engineer for a team.
    Rotation: week-of-year (or day-of-year) modulo len(primary_members).
    Active overrides take precedence.  Expired overrides are auto-cleaned.
    """
    if team not in schedules_db:
        raise HTTPException(
            status_code=404, detail=f"No schedule found for team '{team}'"
        )

    ONCALL_LOOKUPS.labels(team=team).inc()
    cleanup_expired_overrides()

    # Override takes precedence
    if team in overrides_db:
        override = overrides_db[team]
        schedule = schedules_db[team]
        return {
            "team": team,
            "primary": {
                "name": override["user_name"],
                "email": override["user_email"],
                "override": True,
                "reason": override.get("reason", "Manual override"),
                "expires_at": override.get("expires_at"),
            },
            "schedule_id": schedule["id"],
            "rotation_type": schedule["rotation_type"],
        }

    schedule = schedules_db[team]
    current_primary, current_secondary = compute_rotation(schedule)

    if not current_primary:
        raise HTTPException(
            status_code=500,
            detail=f"No primary on-call members configured for team '{team}'",
        )

    # Detect rotation change -> notify new on-call
    previous_primary = last_known_oncall.get(team)
    if previous_primary and previous_primary != current_primary["name"]:
        ROTATION_CHANGES.labels(team=team).inc()
        record_event(
            "rotation_change",
            team,
            {
                "old_primary": previous_primary,
                "new_primary": current_primary["name"],
            },
        )
        notify_service(
            channel="console",
            recipient=current_primary["email"],
            message=f"You are now on-call for team '{team}'",
        )
    last_known_oncall[team] = current_primary["name"]

    result: dict[str, Any] = {
        "team": team,
        "primary": {
            "name": current_primary["name"],
            "email": current_primary["email"],
        },
        "schedule_id": schedule["id"],
        "rotation_type": schedule["rotation_type"],
    }
    if current_secondary:
        result["secondary"] = {
            "name": current_secondary["name"],
            "email": current_secondary["email"],
        }
    return result


# ============================================================
# Override Endpoints
# ============================================================
@app.post("/api/v1/oncall/override", tags=["On-Call"])
def set_override(override: OverrideRequest):
    """Temporarily override the on-call for a team (with auto-expiry)."""
    if override.team not in schedules_db:
        raise HTTPException(
            status_code=404,
            detail=f"No schedule found for team '{override.team}'",
        )

    duration = override.duration_hours or DEFAULT_OVERRIDE_HOURS
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=duration)

    overrides_db[override.team] = {
        "user_name": override.user_name,
        "user_email": override.user_email,
        "reason": override.reason,
        "duration_hours": duration,
        "created_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
    }
    OVERRIDES_ACTIVE.set(len(overrides_db))
    record_event(
        "override_start",
        override.team,
        {
            "user_name": override.user_name,
            "reason": override.reason,
            "duration_hours": duration,
            "expires_at": expires_at.isoformat(),
        },
    )
    logger.info(
        "Override set: team=%s, user=%s, expires=%s",
        override.team,
        override.user_name,
        expires_at.isoformat(),
    )
    return {
        "status": "override_set",
        "team": override.team,
        "overridden_to": override.user_name,
        "duration_hours": duration,
        "expires_at": expires_at.isoformat(),
    }


@app.delete("/api/v1/oncall/override/{team}", tags=["On-Call"])
def remove_override(team: str):
    """Remove an active override for a team."""
    if team not in overrides_db:
        raise HTTPException(
            status_code=404,
            detail=f"No active override for team '{team}'",
        )
    override = overrides_db.pop(team)
    OVERRIDES_ACTIVE.set(len(overrides_db))
    record_event(
        "override_end",
        team,
        {"user_name": override["user_name"], "removed_manually": True},
    )
    logger.info("Override removed: team=%s", team)
    return {"status": "override_removed", "team": team}


@app.get("/api/v1/oncall/overrides", tags=["On-Call"])
def list_active_overrides():
    """List all currently active (non-expired) overrides."""
    cleanup_expired_overrides()
    return [
        {
            "team": team,
            "user_name": ov["user_name"],
            "user_email": ov["user_email"],
            "reason": ov.get("reason"),
            "created_at": ov["created_at"],
            "expires_at": ov.get("expires_at"),
            "duration_hours": ov.get("duration_hours"),
        }
        for team, ov in overrides_db.items()
    ]


# ============================================================
# Escalation Endpoints
# ============================================================
@app.post(
    "/api/v1/escalate",
    response_model=EscalationResponse,
    tags=["Escalation"],
)
def escalate(data: EscalationRequest):
    """Trigger an escalation — notifies the secondary on-call if available."""
    ESCALATIONS_TOTAL.labels(team=data.team).inc()
    NOTIFICATIONS_SENT.labels(channel="console").inc()

    escalation_id = str(uuid.uuid4())

    # Resolve secondary for escalation target
    escalated_to: dict[str, str] | None = None
    if data.team in schedules_db:
        _, secondary = compute_rotation(schedules_db[data.team])
        if secondary:
            escalated_to = {
                "name": secondary["name"],
                "email": secondary["email"],
            }

    record: dict[str, Any] = {
        "escalation_id": escalation_id,
        "team": data.team,
        "incident_id": data.incident_id,
        "reason": data.reason,
        "escalated_to": escalated_to,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    escalation_log.append(record)
    # Bound the log
    if len(escalation_log) > MAX_ESCALATION_LOG_SIZE:
        del escalation_log[: len(escalation_log) - MAX_ESCALATION_LOG_SIZE]

    record_event(
        "escalation",
        data.team,
        {
            "incident_id": data.incident_id,
            "reason": data.reason,
            "escalated_to": escalated_to,
        },
    )
    logger.info(
        "Escalation: team=%s, incident=%s, reason=%s",
        data.team,
        data.incident_id,
        data.reason,
    )

    if escalated_to:
        logger.info(
            "Escalated to: %s (%s)",
            escalated_to["name"],
            escalated_to["email"],
        )
        notify_service(
            channel="email",
            recipient=escalated_to["email"],
            message=f"Escalation for incident {data.incident_id}: {data.reason}",
            incident_id=data.incident_id,
        )

    return {
        "status": "escalated",
        "escalation_id": escalation_id,
        "team": data.team,
        "incident_id": data.incident_id,
        "escalated_to": escalated_to,
        "message": (
            f"Escalation triggered for team '{data.team}' "
            f"\u2014 incident {data.incident_id}"
        ),
        "timestamp": record["timestamp"],
    }


@app.get("/api/v1/escalations", tags=["Escalation"])
def list_escalations(
    team: Optional[str] = None,
    limit: int = Query(default=None, ge=1, description="Max results"),
):
    """List escalation history, optionally filtered by team."""
    effective_limit = limit or DEFAULT_ESCALATION_LIMIT
    result = (
        [e for e in escalation_log if e["team"] == team]
        if team
        else escalation_log
    )
    return result[-effective_limit:]


# ============================================================
# On-Call History / Audit Log
# ============================================================
@app.get("/api/v1/oncall/history", tags=["History"])
def get_oncall_history(
    team: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = Query(default=None, ge=1, description="Max results"),
):
    """
    Audit log for all schedule, override, escalation, and rotation events.
    Supports filtering by team, event_type, and pagination via limit.
    """
    effective_limit = limit or DEFAULT_HISTORY_LIMIT
    result = oncall_history
    if team:
        result = [e for e in result if e["team"] == team]
    if event_type:
        result = [e for e in result if e["event_type"] == event_type]
    return result[-effective_limit:]


# ============================================================
# Teams Overview
# ============================================================
@app.get("/api/v1/teams", tags=["Teams"])
def list_teams():
    """List all teams with their on-call schedule summaries."""
    cleanup_expired_overrides()
    return [
        {
            "team": team,
            "members_count": len(schedule["members"]),
            "rotation_type": schedule["rotation_type"],
            "has_override": team in overrides_db,
        }
        for team, schedule in schedules_db.items()
    ]


# ============================================================
# Operational Stats
# ============================================================
@app.get("/api/v1/oncall/stats", tags=["Stats"])
def get_oncall_stats():
    """Aggregated operational statistics for the on-call service."""
    cleanup_expired_overrides()
    total_members = sum(len(s["members"]) for s in schedules_db.values())

    rotation_types: dict[str, int] = {}
    for s in schedules_db.values():
        rt = s["rotation_type"]
        rotation_types[rt] = rotation_types.get(rt, 0) + 1

    event_types: dict[str, int] = {}
    for e in oncall_history:
        et = e["event_type"]
        event_types[et] = event_types.get(et, 0) + 1

    return {
        "total_schedules": len(schedules_db),
        "total_members": total_members,
        "active_overrides": len(overrides_db),
        "total_escalations": len(escalation_log),
        "total_history_events": len(oncall_history),
        "rotation_types": rotation_types,
        "event_types": event_types,
    }


# ============================================================
# Entrypoint
# ============================================================
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=SERVICE_PORT,
        log_level=LOG_LEVEL.lower(),
    )
