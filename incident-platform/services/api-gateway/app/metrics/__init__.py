# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""Prometheus metrics for the API gateway."""
from prometheus_client import Counter, Histogram

GATEWAY_REQUESTS = Counter(
    "gateway_requests_total",
    "Total requests proxied through the gateway",
    ["method", "service", "status"],
)
GATEWAY_LATENCY = Histogram(
    "gateway_request_duration_seconds",
    "Latency of proxied requests",
    ["service"],
)
GATEWAY_RATE_LIMITED = Counter(
    "gateway_rate_limited_total",
    "Requests rejected by rate limiting",
    ["client_ip"],
)
GATEWAY_RETRIES = Counter(
    "gateway_retries_total",
    "Retry attempts to upstream services",
    ["service", "attempt"],
)
