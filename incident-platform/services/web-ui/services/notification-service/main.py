"""
Notification Service — FastAPI (port 8004)
Accepts notification requests and logs them (mock delivery).
Exposes /health and /metrics for Prometheus.
"""

import os
import uuid
import logging
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("notification-service")

# ---------------------------------------------------------------------------
# Prometheus metrics
# ---------------------------------------------------------------------------
NOTIFICATIONS_SENT = Counter(
    "notifications_sent_total",
    "Total notifications sent",
    ["channel", "status"],
)

# ---------------------------------------------------------------------------
# In-memory log (for demo purposes — no external DB needed)
# ---------------------------------------------------------------------------
notification_log: list[dict] = []

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class NotifyRequest(BaseModel):
    incident_id: str
    channel: str = "mock"       # "mock", "webhook", "email", "slack"
    recipient: str
    message: str


class NotifyResponse(BaseModel):
    id: str
    incident_id: str
    channel: str
    recipient: str
    message: str
    status: str
    created_at: str


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Incident Platform — Notification Service",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "ok", "service": "notification-service"}


@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/api/v1/notify", response_model=NotifyResponse)
async def notify(payload: NotifyRequest):
    """
    Send a notification. For the hackathon this just logs to stdout.
    Supports 'mock', 'webhook', 'email', and 'slack' channels — all mocked.
    """
    notification_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    status = "sent"

    # --- Mock channel delivery ---
    if payload.channel == "webhook":
        webhook_url = os.getenv("WEBHOOK_URL")
        if webhook_url:
            try:
                import httpx
                async with httpx.AsyncClient(timeout=5.0) as client:
                    await client.post(webhook_url, json={
                        "incident_id": payload.incident_id,
                        "message": payload.message,
                        "recipient": payload.recipient,
                    })
                logger.info(
                    "Webhook delivered to %s for incident %s",
                    webhook_url, payload.incident_id,
                )
            except Exception as exc:
                logger.error("Webhook delivery failed: %s", exc)
                status = "failed"
        else:
            logger.info(
                "[MOCK WEBHOOK] Notified %s about incident %s: %s",
                payload.recipient, payload.incident_id, payload.message,
            )
    elif payload.channel == "email":
        logger.info(
            "[MOCK EMAIL] To: %s | Subject: Incident %s | Body: %s",
            payload.recipient, payload.incident_id, payload.message,
        )
    elif payload.channel == "slack":
        logger.info(
            "[MOCK SLACK] Channel/User: %s | Incident: %s | %s",
            payload.recipient, payload.incident_id, payload.message,
        )
    else:
        logger.info(
            "[MOCK] Notified %s about incident %s: %s",
            payload.recipient, payload.incident_id, payload.message,
        )

    NOTIFICATIONS_SENT.labels(channel=payload.channel, status=status).inc()

    entry = {
        "id": notification_id,
        "incident_id": payload.incident_id,
        "channel": payload.channel,
        "recipient": payload.recipient,
        "message": payload.message,
        "status": status,
        "created_at": now,
    }
    notification_log.append(entry)

    return entry


@app.get("/api/v1/notifications")
async def list_notifications(limit: int = 50):
    """Return the latest notification log entries."""
    return notification_log[-limit:]
