# type: ignore
# pyright: reportMissingImports=false, reportGeneralTypeErrors=false
"""Structured JSON logger factory."""
import json
import logging
import sys
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": "incident-management",
            "msg": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1]:
            log_obj["exception"] = str(record.exc_info[1])
        return json.dumps(log_obj)


def get_logger(name: str = "incident-management") -> logging.Logger:
    from app.core.config import settings
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.handlers = [handler]
        logger.setLevel(settings.LOG_LEVEL)
    return logger
