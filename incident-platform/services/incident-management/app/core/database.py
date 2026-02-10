# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""SQLAlchemy engine singleton."""
from sqlalchemy import create_engine
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=settings.POOL_SIZE,
    max_overflow=settings.MAX_OVERFLOW,
    pool_recycle=settings.POOL_RECYCLE,
)
