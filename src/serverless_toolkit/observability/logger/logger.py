import json
import logging
from typing import Any

from serverless_toolkit.observability.logger.settings import (
    LoggingSettings,
    get_logging_settings,
)

_RESERVED_LOG_FIELDS = set(logging.makeLogRecord({}).__dict__) | {
    "asctime",
    "message",
}

_OUTPUT_LOG_FIELDS = {
    "exception",
    "level",
    "logger",
    "message",
}


class JsonFormatter(logging.Formatter):
    """Format standard Python logs as compact JSON records."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        payload.update(_extra_fields(record))
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def _extra_fields(record: logging.LogRecord) -> dict[str, Any]:
    """Return caller-provided extra fields without overriding core fields."""
    return {
        field: value
        for field, value in record.__dict__.items()
        if field not in _RESERVED_LOG_FIELDS
        and field not in _OUTPUT_LOG_FIELDS
        and not field.startswith("_")
    }


def get_logger(
    service: str,
    level: str | int | None = None,
    *,
    settings: LoggingSettings | None = None,
) -> logging.Logger:
    """Create a standardized JSON logger for containerized applications."""
    resolved_settings = settings
    if level is None:
        resolved_settings = settings or get_logging_settings()

    logger = logging.getLogger(service)
    logger.handlers.clear()
    logger.setLevel(level if level is not None else resolved_settings.log_level)

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.propagate = False

    return logger
