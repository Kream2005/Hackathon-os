"""
Notification Service — STUB
Port: 8004
Simulates notifications via console logging.
"""

import time
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

app = FastAPI(title="Notification Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus Metrics
NOTIFICATIONS_SENT = Counter(
    "notifications_sent_total",
    "Total notifications sent",
    ["channel", "status"],
)
NOTIFICATIONS_LATENCY = Histogram(
    "notifications_duration_seconds",
    "Notification processing latency",
    ["channel"],
)

notification_log = []


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "notification-service",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@app.get("/metrics")
def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/api/v1/notify")
def send_notification(data: dict):
    """
    Simulate sending a notification.
    In production this would send email/SMS/Slack/PagerDuty.
    Here we just log to console.
    """
    start_time = time.time()

    channel = data.get("channel", "console")
    recipient = data.get("recipient", "unknown")
    message = data.get("message", "No message")
    incident_id = data.get("incident_id", "N/A")

    # Simulate notification
    print(f"📧 NOTIFICATION [{channel.upper()}]")
    print(f"   To: {recipient}")
    print(f"   Incident: {incident_id}")
    print(f"   Message: {message}")

    record = {
        "channel": channel,
        "recipient": recipient,
        "message": message,
        "incident_id": incident_id,
        "sent_at": datetime.utcnow().isoformat() + "Z",
        "status": "delivered",
    }
    notification_log.append(record)

    NOTIFICATIONS_SENT.labels(channel=channel, status="delivered").inc()
    NOTIFICATIONS_LATENCY.labels(channel=channel).observe(time.time() - start_time)

    return {
        "status": "sent",
        "channel": channel,
        "recipient": recipient,
        "notification_id": f"notif-{len(notification_log)}",
    }


@app.get("/api/v1/notifications")
def list_notifications(limit: int = 50):
    """List recent notifications."""
    return notification_log[-limit:]
