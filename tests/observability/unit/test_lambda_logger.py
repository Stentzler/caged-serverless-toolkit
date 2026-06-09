import json
import logging
from collections.abc import Iterator
from dataclasses import FrozenInstanceError
from typing import Any

import pytest
from aws_lambda_powertools import Logger

from serverless_toolkit.observability.lambda_logger import (
    LoggingSettings,
    get_lambda_logger,
    get_logging_settings,
    inject_lambda_context,
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


@pytest.fixture(autouse=True)
def clear_logging_settings_cache() -> Iterator[None]:
    get_logging_settings.cache_clear()
    yield
    get_logging_settings.cache_clear()


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

    settings = get_logging_settings()

    assert settings.service_name == "env-service-name"
    assert settings.log_level == "DEBUG"
    assert settings.log_event is True


def test_logging_settings_provider_reuses_instance() -> None:
    assert get_logging_settings() is get_logging_settings()


def test_logging_settings_are_immutable() -> None:
    settings = LoggingSettings()

    with pytest.raises(FrozenInstanceError):
        settings.service_name = "changed-service"


def test_logging_settings_reject_invalid_boolean(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("POWERTOOLS_LOG_EVENT", "invalid")

    with pytest.raises(ValueError, match="Invalid boolean value"):
        LoggingSettings()


def test_lambda_get_logger_uses_injected_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("POWERTOOLS_SERVICE_NAME", "environment-service")
    settings = LoggingSettings(
        service_name="injected-service",
        log_level="DEBUG",
    )

    logger = get_lambda_logger(settings=settings)

    assert logger.service == "injected-service"
    assert logger.log_level == logging.DEBUG


def test_lambda_get_logger_explicit_values_override_settings() -> None:
    settings = LoggingSettings(
        service_name="settings-service",
        log_level="INFO",
    )

    logger = get_lambda_logger(
        service="explicit-service",
        level="DEBUG",
        settings=settings,
    )

    assert logger.service == "explicit-service"
    assert logger.log_level == logging.DEBUG


def test_logging_settings_provider_reloads_environment_after_cache_clear(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("POWERTOOLS_SERVICE_NAME", "first-service")
    first_settings = get_logging_settings()

    monkeypatch.setenv("POWERTOOLS_SERVICE_NAME", "second-service")
    cached_settings = get_logging_settings()
    get_logging_settings.cache_clear()
    reloaded_settings = get_logging_settings()

    assert cached_settings is first_settings
    assert cached_settings.service_name == "first-service"
    assert reloaded_settings.service_name == "second-service"


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
