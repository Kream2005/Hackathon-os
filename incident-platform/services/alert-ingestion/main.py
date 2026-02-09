"""
Alert Ingestion Service — STUB
Port: 8001
This is a placeholder. Personne 1 will implement the full logic.
"""

import time
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

app = FastAPI(title="Alert Ingestion Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus Metrics
REQUEST_COUNT = Counter(
    "alerts_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
ALERTS_RECEIVED = Counter(
    "alerts_received_total",
    "Total alerts received",
    ["service", "severity"],
)
ALERTS_CORRELATED = Counter(
    "alerts_correlated_total",
    "Alerts correlated to existing incidents",
)
INCIDENTS_CREATED = Counter(
    "incidents_created_total",
    "Incidents created from alerts",
    ["severity"],
)
REQUEST_LATENCY = Histogram(
    "alerts_request_duration_seconds",
    "Request latency in seconds",
    ["method", "endpoint"],
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "alert-ingestion",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@app.get("/metrics")
def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/api/v1/alerts")
def receive_alert(alert: dict):
    """Stub: receive an alert and return a mock response."""
    start_time = time.time()

    service = alert.get("service", "unknown")
    severity = alert.get("severity", "medium")

    ALERTS_RECEIVED.labels(service=service, severity=severity).inc()
    REQUEST_COUNT.labels(method="POST", endpoint="/api/v1/alerts", status="201").inc()
    REQUEST_LATENCY.labels(method="POST", endpoint="/api/v1/alerts").observe(time.time() - start_time)

    print(f"🔔 Alert received: service={service}, severity={severity}")

    return {
        "status": "received",
        "alert_id": "stub-alert-id",
        "message": f"Alert received for {service} (stub)",
    }


@app.get("/api/v1/alerts")
def list_alerts():
    """Stub: return empty list."""
    return []
