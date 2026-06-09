import os
from dataclasses import dataclass, field
from functools import cache


@dataclass(frozen=True)
class LoggingSettings:
    """Logging configuration loaded from the environment."""

    service_name: str = field(
        default_factory=lambda: os.getenv(
            "POWERTOOLS_SERVICE_NAME",
            "unknown-service",
        )
    )
    log_level: str = field(
        default_factory=lambda: os.getenv("POWERTOOLS_LOG_LEVEL", "INFO")
    )
    log_event: bool = field(
        default_factory=lambda: _parse_boolean(
            os.getenv("POWERTOOLS_LOG_EVENT", "false")
        )
    )


@cache
def get_logging_settings() -> LoggingSettings:
    """Return the shared environment-derived logging settings."""
    return LoggingSettings()


def _parse_boolean(value: str) -> bool:
    """Parse a conventional environment boolean value."""
    normalized_value = value.strip().lower()

    if normalized_value in {"1", "true", "yes", "on"}:
        return True
    if normalized_value in {"0", "false", "no", "off"}:
        return False

    msg = f"Invalid boolean value: {value!r}"
    raise ValueError(msg)
