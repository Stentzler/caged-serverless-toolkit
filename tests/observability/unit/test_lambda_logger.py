import json
import logging
from typing import Any

import pytest
from aws_lambda_powertools import Logger

from serverless_toolkit.observability.lambda_logger import (
    get_lambda_logger,
    inject_lambda_context,
)
from serverless_toolkit.observability.lambda_logger.settings import (
    LoggingSettings,
    logging_settings,
)


class FakeLambdaContext:
    function_name = "test-function"
    function_version = "$LATEST"
    invoked_function_arn = (
        "arn:aws:lambda:us-east-1:123456789012:function:test-function"
    )
    memory_limit_in_mb = 128
    aws_request_id = "test-request-id"
    log_group_name = "/aws/lambda/test-function"
    log_stream_name = "2026/01/01/[$LATEST]abcdef"


def test_lambda_get_logger_returns_powertools_logger() -> None:
    logger = get_lambda_logger(service="serverless-toolkit-test-return-type")

    assert isinstance(logger, Logger)


def test_lambda_get_logger_uses_service_name() -> None:
    logger = get_lambda_logger(service="serverless-toolkit-test-service-name")

    assert logger.service == "serverless-toolkit-test-service-name"


def test_lambda_get_logger_uses_explicit_level() -> None:
    logger = get_lambda_logger(
        service="serverless-toolkit-test-explicit-level",
        level=logging.DEBUG,
    )

    assert logger.log_level == logging.DEBUG


def test_lambda_settings_loads_environment_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("POWERTOOLS_SERVICE_NAME", "env-service-name")
    monkeypatch.setenv("POWERTOOLS_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("POWERTOOLS_LOG_EVENT", "TRUE")

    settings = LoggingSettings()

    assert settings.POWERTOOLS_SERVICE_NAME == "env-service-name"
    assert settings.POWERTOOLS_LOG_LEVEL == "DEBUG"
    assert settings.POWERTOOLS_LOG_EVENT == "true"


def test_lambda_get_logger_uses_configured_service_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        logging_settings,
        "POWERTOOLS_SERVICE_NAME",
        "env-service-name",
    )

    logger = get_lambda_logger()

    assert logger.service == "env-service-name"


def test_lambda_get_logger_uses_configured_log_level(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(logging_settings, "POWERTOOLS_LOG_LEVEL", "DEBUG")

    logger = get_lambda_logger(service="serverless-toolkit-test-env-log-level")

    assert logger.log_level == logging.DEBUG


def test_inject_lambda_context_adds_lambda_metadata(
    capfd: pytest.CaptureFixture[str],
) -> None:
    logger = get_lambda_logger(service="serverless-toolkit-test-context-metadata")

    @inject_lambda_context(logger)
    def handler(event: dict[str, Any], context: FakeLambdaContext) -> dict[str, Any]:
        logger.info("Handler executed")
        return {"ok": True}

    response = handler({}, FakeLambdaContext())

    assert response == {"ok": True}

    captured = capfd.readouterr()

    logs = [json.loads(line) for line in captured.out.splitlines() if line.strip()]

    log_data = next(log for log in logs if log.get("message") == "Handler executed")

    assert log_data["service"] == "serverless-toolkit-test-context-metadata"
    assert log_data["function_name"] == "test-function"
    assert log_data["function_request_id"] == "test-request-id"


def test_inject_lambda_context_does_not_log_event_by_default(
    caplog: pytest.LogCaptureFixture,
) -> None:
    logger = get_lambda_logger(service="serverless-toolkit-test-no-event")

    @inject_lambda_context(logger)
    def handler(event: dict[str, Any], context: FakeLambdaContext) -> None:
        logger.info("Handler executed")

    with caplog.at_level(logging.INFO):
        handler({"sensitive": "value"}, FakeLambdaContext())

    serialized_logs = "\n".join(record.message for record in caplog.records)

    assert "Handler executed" in serialized_logs
    assert "sensitive" not in serialized_logs
    assert "value" not in serialized_logs


def test_inject_lambda_context_can_log_event_when_enabled(
    caplog: pytest.LogCaptureFixture,
) -> None:
    logger = get_lambda_logger(service="serverless-toolkit-test-log-event")

    @inject_lambda_context(logger, log_event=True)
    def handler(event: dict[str, Any], context: FakeLambdaContext) -> None:
        logger.info("Handler executed")

    with caplog.at_level(logging.INFO):
        handler({"test_key": "test_value"}, FakeLambdaContext())

    serialized_logs = "\n".join(record.message for record in caplog.records)

    assert "test_key" in serialized_logs
    assert "test_value" in serialized_logs
    assert "Handler executed" in serialized_logs
