# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""
Prometheus metrics — single source of truth for all metric objects.
Imported by services and middleware. Never instantiated in controllers.
"""

from prometheus_client import Counter, Histogram

# ── HTTP Metrics (used by middleware) ──
REQUEST_COUNT = Counter(
    "alertingestion_requests_total",
    "Total HTTP requests to alert-ingestion service",
    ["method", "endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "alertingestion_request_duration_seconds",
    "Request latency in seconds",
    ["method", "endpoint"],
)
HTTP_ERRORS = Counter(
    "alertingestion_http_errors_total",
    "Total HTTP error responses",
    ["method", "endpoint", "status"],
)

# ── Business Metrics (updated by service layer only) ──
ALERTS_RECEIVED = Counter(
    "alerts_received_total",
    "Total alerts received by severity",
    ["severity"],
)
ALERTS_CORRELATED = Counter(
    "alerts_correlated_total",
    "Alert correlation outcomes",
    ["result"],
)
ALERT_PROCESSING = Histogram(
    "alert_processing_seconds",
    "Time taken to process a single alert end-to-end",
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
)
