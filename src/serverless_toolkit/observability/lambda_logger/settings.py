import os


class LoggingSettings:
    """Logging configuration loaded from the environment."""

    def __init__(self) -> None:
        self.POWERTOOLS_LOG_LEVEL = os.getenv("POWERTOOLS_LOG_LEVEL", "INFO")
        self.POWERTOOLS_SERVICE_NAME = os.getenv(
            "POWERTOOLS_SERVICE_NAME",
            "unknown-service",
        )
        self.POWERTOOLS_LOG_EVENT = os.getenv(
            "POWERTOOLS_LOG_EVENT",
            "false",
        ).lower()


logging_settings = LoggingSettings()
