# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""Prometheus metrics for the incident-management service."""
from prometheus_client import Counter, Gauge, Histogram

INCIDENTS_CREATED = Counter(
    "incidents_created_total", "Total incidents created", ["severity"]
)
INCIDENTS_TOTAL = Gauge(
    "incidents_total", "Current incidents by status", ["status"]
)
INCIDENT_MTTA = Histogram(
    "incident_mtta_seconds",
    "Mean Time To Acknowledge (seconds)",
    buckets=[30, 60, 120, 300, 600, 1800, 3600],
)
INCIDENT_MTTR = Histogram(
    "incident_mttr_seconds",
    "Mean Time To Resolve (seconds)",
    buckets=[60, 300, 600, 1800, 3600, 7200, 14400],
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
