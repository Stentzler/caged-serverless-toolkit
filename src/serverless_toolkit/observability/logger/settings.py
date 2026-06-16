import os
from dataclasses import dataclass, field
from functools import cache


@dataclass(frozen=True)
class LoggingSettings:
    """Generic logging configuration loaded from the environment."""

    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))


@cache
def get_logging_settings() -> LoggingSettings:
    """Return the shared environment-derived logging settings."""
    return LoggingSettings()
