# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""Centralised settings — read from env vars once."""
import os


class Settings:
    SERVICE_NAME: str = "notification-service"
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "",
    )
    WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    MAX_LOG_SIZE: int = int(os.getenv("MAX_LOG_SIZE", "10000"))
    POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "10"))
    MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "5"))
    POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "300"))


settings = Settings()
