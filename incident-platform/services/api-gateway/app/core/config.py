# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""Centralised settings — read from env vars once."""
import os


class Settings:
    SERVICE_NAME: str = "api-gateway"
    ALERT_INGESTION_URL: str = os.getenv("ALERT_INGESTION_URL", "http://alert-ingestion:8001")
    INCIDENT_MANAGEMENT_URL: str = os.getenv("INCIDENT_MANAGEMENT_URL", "http://incident-management:8002")
    ONCALL_SERVICE_URL: str = os.getenv("ONCALL_SERVICE_URL", "http://oncall-service:8003")
    NOTIFICATION_SERVICE_URL: str = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification-service:8004")

    # Auth
    _raw_keys: str = os.getenv("API_KEYS", "")
    API_KEYS: set = {k.strip() for k in _raw_keys.split(",") if k.strip()}
    AUTH_ENABLED: bool = len(API_KEYS) > 0

    _raw_users: str = os.getenv("AUTH_USERS", "")
    USER_CREDENTIALS: dict = {}
    for pair in _raw_users.split(","):
        pair = pair.strip()
        if ":" in pair:
            u, p = pair.split(":", 1)
            USER_CREDENTIALS[u.strip()] = p.strip()

    LOGIN_API_KEY: str = os.getenv("LOGIN_API_KEY", list(API_KEYS)[0] if API_KEYS else "")

    AUTH_BYPASS_PATHS: set = {"/health", "/metrics", "/api/services/health", "/api/v1/auth/login"}

    # Rate Limiting
    RATE_LIMIT_RPM: int = int(os.getenv("RATE_LIMIT_RPM", "120"))
    RATE_LIMIT_ENABLED: bool = RATE_LIMIT_RPM > 0
    RATE_LIMIT_BYPASS: set = {"/health", "/metrics", "/api/services/health"}

    # Retry
    RETRY_MAX_ATTEMPTS: int = int(os.getenv("RETRY_MAX_ATTEMPTS", "2"))
    RETRY_BACKOFF_BASE: float = float(os.getenv("RETRY_BACKOFF_BASE", "0.3"))
    RETRY_SAFE_METHODS: set = {"GET", "HEAD", "OPTIONS"}

    # Service map
    SERVICE_MAP: dict = {}

    def __init__(self):
        self.SERVICE_MAP = {
            "alerts": self.ALERT_INGESTION_URL,
            "incidents": self.INCIDENT_MANAGEMENT_URL,
            "oncall": self.ONCALL_SERVICE_URL,
            "schedules": self.ONCALL_SERVICE_URL,
            "escalate": self.ONCALL_SERVICE_URL,
            "escalations": self.ONCALL_SERVICE_URL,
            "notify": self.NOTIFICATION_SERVICE_URL,
            "notifications": self.NOTIFICATION_SERVICE_URL,
        }


settings = Settings()
