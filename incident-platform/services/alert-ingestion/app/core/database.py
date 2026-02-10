# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""
Database engine — single source of truth for DB connectivity.
"""

from sqlalchemy import create_engine
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_recycle=settings.DB_POOL_RECYCLE,
)
