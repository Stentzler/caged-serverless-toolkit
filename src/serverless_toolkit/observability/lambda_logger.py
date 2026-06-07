import os
from typing import Any

from aws_lambda_powertools import Logger


def get_lambda_logger(
    service: str | None = None,
    level: str | int | None = None,
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

    Returns:
        Configured AWS Lambda Powertools logger instance.
    """
    return Logger(
        service=service or os.getenv("POWERTOOLS_SERVICE_NAME", "unknown-service"),
        level=level or os.getenv("POWERTOOLS_LOG_LEVEL", "INFO"),
    )


def inject_lambda_context(
    logger: Logger,
    *,
    log_event: bool | None = None,
    clear_state: bool = True,
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

    Returns:
        Decorator returned by `logger.inject_lambda_context`.
    """
    return logger.inject_lambda_context(
        log_event=(
            log_event
            if log_event is not None
            else os.getenv("POWERTOOLS_LOG_EVENT", "false").lower() == "true"
        ),
        clear_state=clear_state,
    )