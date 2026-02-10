# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""Prometheus metrics for the notification service."""
from prometheus_client import Counter, Histogram, Gauge

NOTIFICATIONS_SENT = Counter(
    "notifications_sent_total",
    "Total notifications processed",
    ["channel", "status"],
)
NOTIFICATION_PROCESSING = Histogram(
    "notification_processing_seconds",
    "Time to process a notification request end-to-end",
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)
NOTIFICATIONS_IN_LOG = Gauge(
    "notifications_in_log",
    "Current number of notifications stored in the in-memory log",
)
REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"]
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds", "HTTP request latency", ["method", "endpoint"]
)
HTTP_ERRORS = Counter(
    "http_errors_total", "Total HTTP errors", ["method", "endpoint", "status"]
)
