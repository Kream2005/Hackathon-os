# type: ignore
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
"""
Notification Service
====================
Accepts notification requests from other platform services, logs delivery
(mock channels: mock, webhook, email, slack), stores an in-memory audit log,
and exposes Prometheus metrics.

Port: 8004
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
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

# ── Configuration ──────────────────────────────────────────────────────────
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
MAX_LOG_SIZE = int(os.getenv("MAX_LOG_SIZE", "10000"))

# ── Structured JSON Logger ─────────────────────────────────────────────────
class _JSONFormatter(logging.Formatter):
    """Emit every log record as a single-line JSON object — parseable by
    Loki, Datadog, ELK, or any log aggregator."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": "notification-service",
            "msg": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1]:
            log_obj["exception"] = str(record.exc_info[1])
        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id
        return json.dumps(log_obj)


_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(_JSONFormatter())
logger = logging.getLogger("notification-service")
logger.handlers = [_handler]
logger.setLevel(LOG_LEVEL)

# ── Prometheus Metrics ────────────────────────────────────────────────────
notifications_sent_total = Counter(
    "notifications_sent_total",
    "Total notifications processed",
    ["channel", "status"],
)
notification_processing_seconds = Histogram(
    "notification_processing_seconds",
    "Time to process a notification request end-to-end",
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)
notifications_in_log = Gauge(
    "notifications_in_log",
    "Current number of notifications stored in the in-memory log",
)

# ── Valid channels ────────────────────────────────────────────────────────
VALID_CHANNELS = ("mock", "webhook", "email", "slack")

# ── In-memory notification log ────────────────────────────────────────────
notification_log: List[Dict[str, Any]] = []
notification_index: Dict[str, Dict[str, Any]] = {}  # id → entry (O(1) lookup)


# ── Pydantic Models ───────────────────────────────────────────────────────
class NotifyRequest(BaseModel):
    """Inbound notification payload."""
    incident_id: str = Field(..., min_length=1, max_length=255, examples=["d290f1ee-6c54-4b01-90e6-d701748f0851"])
    channel: str = Field(default="mock", max_length=50, examples=["mock"])
    recipient: str = Field(..., min_length=1, max_length=500, examples=["alice@example.com"])
    message: str = Field(..., min_length=1, max_length=5000, examples=["[CRITICAL] frontend-api: HTTP 5xx rate > 10%"])
    severity: Optional[str] = Field(default=None, max_length=20, examples=["critical"])
    metadata: Optional[Dict[str, Any]] = Field(default=None)

    @field_validator("channel")
    @classmethod
    def normalise_channel(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in VALID_CHANNELS:
            raise ValueError(f"channel must be one of {VALID_CHANNELS}")
        return v

    @field_validator("recipient")
    @classmethod
    def normalise_recipient(cls, v: str) -> str:
        return v.strip()


class NotifyResponse(BaseModel):
    """Response after processing a notification."""
    id: str
    incident_id: str
    channel: str
    recipient: str
    message: str
    severity: Optional[str] = None
    status: str
    created_at: str


class NotificationDetail(NotifyResponse):
    metadata: Optional[Dict[str, Any]] = None


class PaginatedNotifications(BaseModel):
    total: int
    page: int
    per_page: int
    notifications: List[NotificationDetail]


class NotificationStats(BaseModel):
    total: int
    sent: int
    failed: int
    by_channel: Dict[str, int]
    by_severity: Dict[str, int]


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    request_id: Optional[str] = None


# ── Channel delivery handlers ─────────────────────────────────────────────
async def _deliver_mock(payload: NotifyRequest) -> str:
    """Mock channel — just logs the notification."""
    logger.info(
        "[MOCK] Notified %s about incident %s: %s",
        payload.recipient, payload.incident_id, payload.message,
    )
    return "sent"


async def _deliver_email(payload: NotifyRequest) -> str:
    """Mock email channel — logs formatted email output."""
    logger.info(
        "[MOCK EMAIL] To: %s | Subject: Incident %s | Body: %s",
        payload.recipient, payload.incident_id, payload.message,
    )
    return "sent"


async def _deliver_slack(payload: NotifyRequest) -> str:
    """Mock Slack channel — logs to console."""
    logger.info(
        "[MOCK SLACK] Channel/User: %s | Incident: %s | %s",
        payload.recipient, payload.incident_id, payload.message,
    )
    return "sent"


async def _deliver_webhook(payload: NotifyRequest) -> str:
    """Webhook channel — attempts real delivery if WEBHOOK_URL is set."""
    if not WEBHOOK_URL:
        logger.info(
            "[MOCK WEBHOOK] Notified %s about incident %s: %s",
            payload.recipient, payload.incident_id, payload.message,
        )
        return "sent"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(WEBHOOK_URL, json={
                "incident_id": payload.incident_id,
                "message": payload.message,
                "recipient": payload.recipient,
                "severity": payload.severity,
            })
            if resp.status_code < 300:
                logger.info(
                    "Webhook delivered to %s for incident %s (status=%s)",
                    WEBHOOK_URL, payload.incident_id, resp.status_code,
                )
                return "sent"
            else:
                logger.warning(
                    "Webhook returned %s for incident %s",
                    resp.status_code, payload.incident_id,
                )
                return "failed"
    except Exception as exc:
        logger.error("Webhook delivery failed: %s", exc)
        return "failed"


# Channel dispatch map
CHANNEL_HANDLERS = {
    "mock": _deliver_mock,
    "email": _deliver_email,
    "slack": _deliver_slack,
    "webhook": _deliver_webhook,
}


# ── Helpers ───────────────────────────────────────────────────────────────
def _store_notification(entry: Dict[str, Any]) -> None:
    """Append to in-memory log with bounded size (ring buffer behaviour)."""
    notification_log.append(entry)
    notification_index[entry["id"]] = entry
    # Evict oldest entries if we exceed the limit
    while len(notification_log) > MAX_LOG_SIZE:
        evicted = notification_log.pop(0)
        notification_index.pop(evicted["id"], None)
    notifications_in_log.set(len(notification_log))


# ── Lifespan ──────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(application: FastAPI):
    """Log startup and cleanup on shutdown."""
    logger.info("Notification service starting — mock delivery enabled")
    yield
    logger.info("Notification service shutting down — %d notifications in log", len(notification_log))


# ── FastAPI App ───────────────────────────────────────────────────────────
app = FastAPI(
    title="Notification Service",
    description="Accepts notification requests and delivers via mock channels (mock, email, slack, webhook).",
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
async def health():
    """Shallow health check — confirms the process is alive."""
    return {"status": "ok", "service": "notification-service"}


@app.get("/health/ready", tags=["ops"])
async def readiness():
    """Deep readiness check — notification service is stateless, always ready."""
    return {
        "status": "ok",
        "service": "notification-service",
        "notifications_in_log": len(notification_log),
    }


@app.get("/metrics", tags=["ops"])
async def metrics():
    """Prometheus-format metrics."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ── Core Endpoints ────────────────────────────────────────────────────────
@app.post(
    "/api/v1/notify",
    response_model=NotifyResponse,
    status_code=200,
    tags=["notifications"],
    summary="Send a notification",
    responses={200: {"description": "Notification processed"}},
)
async def notify(payload: NotifyRequest, request: Request):
    """
    Process a notification request through the specified channel.

    Supported channels: mock, email, slack, webhook.
    All channels are mocked (log to stdout) except webhook which attempts
    real HTTP delivery when WEBHOOK_URL is configured.
    """
    with notification_processing_seconds.time():
        notification_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        # Dispatch to channel handler
        handler = CHANNEL_HANDLERS.get(payload.channel, _deliver_mock)
        status = await handler(payload)

        # Update Prometheus counter
        notifications_sent_total.labels(
            channel=payload.channel, status=status
        ).inc()

        # Build entry
        entry: Dict[str, Any] = {
            "id": notification_id,
            "incident_id": payload.incident_id,
            "channel": payload.channel,
            "recipient": payload.recipient,
            "message": payload.message,
            "severity": payload.severity,
            "status": status,
            "metadata": payload.metadata,
            "created_at": now,
        }
        _store_notification(entry)

        logger.info(
            "Notification processed id=%s incident=%s channel=%s status=%s recipient=%s",
            notification_id, payload.incident_id, payload.channel, status, payload.recipient,
        )

        return NotifyResponse(
            id=notification_id,
            incident_id=payload.incident_id,
            channel=payload.channel,
            recipient=payload.recipient,
            message=payload.message,
            severity=payload.severity,
            status=status,
            created_at=now,
        )


@app.get(
    "/api/v1/notifications/{notification_id}",
    response_model=NotificationDetail,
    tags=["notifications"],
    summary="Get a single notification by ID",
)
async def get_notification(notification_id: str):
    """Retrieve a specific notification by its UUID."""
    try:
        uuid.UUID(notification_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid notification ID format")

    entry = notification_index.get(notification_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Notification not found")
    return NotificationDetail(**entry)


@app.get(
    "/api/v1/notifications",
    response_model=PaginatedNotifications,
    tags=["notifications"],
    summary="List notifications with pagination and filters",
)
async def list_notifications(
    channel: Optional[str] = None,
    status: Optional[str] = None,
    incident_id: Optional[str] = None,
    recipient: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=200),
):
    """Return notifications with optional filtering and pagination."""
    filtered = notification_log

    if channel:
        filtered = [n for n in filtered if n["channel"] == channel.lower()]
    if status:
        filtered = [n for n in filtered if n["status"] == status.lower()]
    if incident_id:
        filtered = [n for n in filtered if n["incident_id"] == incident_id]
    if recipient:
        filtered = [n for n in filtered if n["recipient"] == recipient]

    total = len(filtered)
    start = (page - 1) * per_page
    end = start + per_page
    page_items = filtered[start:end]

    return PaginatedNotifications(
        total=total,
        page=page,
        per_page=per_page,
        notifications=[NotificationDetail(**n) for n in page_items],
    )


@app.get(
    "/api/v1/notifications/stats/summary",
    response_model=NotificationStats,
    tags=["notifications"],
    summary="Notification statistics",
)
async def get_stats():
    """Aggregate notification statistics — counts by channel and status."""
    total = len(notification_log)
    sent = sum(1 for n in notification_log if n["status"] == "sent")
    failed = sum(1 for n in notification_log if n["status"] == "failed")

    by_channel: Dict[str, int] = {}
    by_severity: Dict[str, int] = {}
    for n in notification_log:
        ch = n["channel"]
        by_channel[ch] = by_channel.get(ch, 0) + 1
        sev = n.get("severity") or "unknown"
        by_severity[sev] = by_severity.get(sev, 0) + 1

    return NotificationStats(
        total=total,
        sent=sent,
        failed=failed,
        by_channel=by_channel,
        by_severity=by_severity,
    )


# ── Entrypoint ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004, log_level="info")
