# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""
Core configuration — all env-driven, zero hardcode.
Single source of truth for every tunable parameter.
"""

import os


class Settings:
    """Application settings loaded from environment variables."""

    SERVICE_NAME: str = os.getenv("SERVICE_NAME", "alert-ingestion")
    SERVICE_VERSION: str = os.getenv("SERVICE_VERSION", "1.0.0")
    SERVICE_PORT: int = int(os.getenv("SERVICE_PORT", "8001"))

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://hackathon:hackathon2026@database:5432/incident_platform",
    )
    INCIDENT_MANAGEMENT_URL: str = os.getenv(
        "INCIDENT_MANAGEMENT_URL", "http://incident-management:8002"
    )
    NOTIFICATION_SERVICE_URL: str = os.getenv(
        "NOTIFICATION_SERVICE_URL", "http://notification-service:8004"
    )
    CORRELATION_WINDOW_MINUTES: int = int(os.getenv("CORRELATION_WINDOW_MINUTES", "5"))

    CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "*").split(",")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "10"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "5"))
    DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "300"))


settings = Settings()
