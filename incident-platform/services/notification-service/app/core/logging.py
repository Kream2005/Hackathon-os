# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""Structured JSON logger factory."""
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": "notification-service",
            "msg": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1]:
            log_obj["exception"] = str(record.exc_info[1])
        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id
        return json.dumps(log_obj)


def get_logger(name: str = "notification-service") -> logging.Logger:
    from app.core.config import settings
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.handlers = [handler]
        logger.setLevel(settings.LOG_LEVEL)
    return logger
