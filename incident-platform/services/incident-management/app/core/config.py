# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""Centralised settings — read from env vars once."""
import os


class Settings:
    SERVICE_NAME: str = "incident-management"
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "",
    )
    ONCALL_SERVICE_URL: str = os.getenv("ONCALL_SERVICE_URL", "http://oncall-service:8003")
    NOTIFICATION_SERVICE_URL: str = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification-service:8004")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "10"))
    MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "5"))
    POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "300"))


settings = Settings()
