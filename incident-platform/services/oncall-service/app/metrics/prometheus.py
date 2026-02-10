# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""
Prometheus metrics — single source of truth for all metric objects.
Imported by services and middleware. Never instantiated in controllers.
"""

from prometheus_client import Counter, Gauge, Histogram

# ── HTTP Metrics (used by middleware) ──
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
HTTP_ERRORS = Counter(
    "oncall_http_errors_total",
    "Total HTTP error responses",
    ["method", "endpoint", "status"],
)

# ── Business Metrics (updated by service layer only) ──
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
