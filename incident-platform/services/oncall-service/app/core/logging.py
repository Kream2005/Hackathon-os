# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""
Structured JSON logging — machine-parseable, one JSON line per record.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings


class JSONFormatter(logging.Formatter):
    """Emit every log record as a single JSON line for machine parsing."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": settings.SERVICE_NAME,
            "message": record.getMessage(),
        }
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id  # type: ignore[attr-defined]
        if record.exc_info and record.exc_info[1]:
            log_data["error"] = str(record.exc_info[1])
            log_data["error_type"] = type(record.exc_info[1]).__name__
        return json.dumps(log_data)


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a configured logger instance."""
    logger_name = name or settings.SERVICE_NAME
    logger = logging.getLogger(logger_name)
    if not logger.handlers:
        logger.setLevel(getattr(logging, settings.LOG_LEVEL, logging.INFO))
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        logger.propagate = False
    return logger
