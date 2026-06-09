from typing import Any

from aws_lambda_powertools import Logger

from serverless_toolkit.observability.lambda_logger.settings import (
    LoggingSettings,
    get_logging_settings,
)


def get_lambda_logger(
    service: str | None = None,
    level: str | int | None = None,
    *,
    settings: LoggingSettings | None = None,
) -> Logger:
    """Create a standardized AWS Lambda Powertools logger.

    The logger uses AWS Lambda Powertools to generate structured JSON logs.
    If `service` or `level` are not provided explicitly, the values are read
    from the `POWERTOOLS_SERVICE_NAME` and `POWERTOOLS_LOG_LEVEL` environment
    variables.

    Args:
        service: Logical service name to include in every log record.
            Defaults to `POWERTOOLS_SERVICE_NAME` or `"unknown-service"`.
        level: Logging level to use, such as `logging.INFO`, `logging.DEBUG`,
            `"INFO"`, or `"DEBUG"`. Defaults to `POWERTOOLS_LOG_LEVEL` or
            `"INFO"`.
        settings: Optional immutable settings override. Environment-derived
            settings are used when this is not provided.

    Returns:
        Configured AWS Lambda Powertools logger instance.
    """
    resolved_settings = settings
    if service is None or level is None:
        resolved_settings = settings or get_logging_settings()

    return Logger(
        service=(service if service is not None else resolved_settings.service_name),
        level=level if level is not None else resolved_settings.log_level,
    )


def inject_lambda_context(
    logger: Logger,
    *,
    log_event: bool | None = None,
    clear_state: bool = True,
    settings: LoggingSettings | None = None,
) -> Any:
    """Decorate a Lambda handler to enrich logs with Lambda context metadata.

    The decorator adds Lambda execution metadata to structured logs, such as
    function name, memory size, ARN, request ID, and cold start information.

    By default, the incoming Lambda event is not logged to avoid leaking
    sensitive data. Event logging can be enabled explicitly with `log_event=True`
    or through the `POWERTOOLS_LOG_EVENT=true` environment variable.

    Args:
        logger: AWS Lambda Powertools logger instance used by the handler.
        log_event: Whether to log the incoming Lambda event payload. If not
            provided, the value is read from `POWERTOOLS_LOG_EVENT`.
        clear_state: Whether to clear custom logger state between invocations.
        settings: Optional immutable settings override used when `log_event`
            is not provided.

    Returns:
        Decorator returned by `logger.inject_lambda_context`.
    """
    should_log_event = log_event
    if should_log_event is None:
        should_log_event = (settings or get_logging_settings()).log_event

    return logger.inject_lambda_context(
        log_event=should_log_event,
        clear_state=clear_state,
    )
