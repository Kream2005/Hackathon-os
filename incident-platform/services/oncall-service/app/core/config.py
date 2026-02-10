# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""
Core configuration — all env-driven, zero hardcode.
Single source of truth for every tunable parameter.
"""

import os


class Settings:
    """Application settings loaded from environment variables."""

    SERVICE_NAME: str = os.getenv("SERVICE_NAME", "oncall-service")
    SERVICE_VERSION: str = os.getenv("SERVICE_VERSION", "2.1.0")
    SERVICE_PORT: int = int(os.getenv("SERVICE_PORT", "8003"))

    NOTIFICATION_SERVICE_URL: str = os.getenv(
        "NOTIFICATION_SERVICE_URL", "http://notification-service:8004"
    )
    NOTIFICATION_TIMEOUT: float = float(os.getenv("NOTIFICATION_TIMEOUT", "3.0"))

    DEFAULT_OVERRIDE_HOURS: int = int(os.getenv("DEFAULT_OVERRIDE_HOURS", "8"))
    DEFAULT_ESCALATION_LIMIT: int = int(os.getenv("DEFAULT_ESCALATION_LIMIT", "50"))
    DEFAULT_HISTORY_LIMIT: int = int(os.getenv("DEFAULT_HISTORY_LIMIT", "100"))
    MAX_HISTORY_SIZE: int = int(os.getenv("MAX_HISTORY_SIZE", "10000"))
    MAX_ESCALATION_LOG_SIZE: int = int(os.getenv("MAX_ESCALATION_LOG_SIZE", "5000"))

    CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "*").split(",")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    SEED_DEFAULT_SCHEDULES: bool = (
        os.getenv("SEED_DEFAULT_SCHEDULES", "true").lower() == "true"
    )


settings = Settings()
