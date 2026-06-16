import json
import logging
from collections.abc import Iterator
from dataclasses import FrozenInstanceError

import pytest

from serverless_toolkit.observability.logger import (
    LoggingSettings,
    get_logger,
    get_logging_settings,
)


@pytest.fixture(autouse=True)
def clear_logging_settings_cache() -> Iterator[None]:
    get_logging_settings.cache_clear()
    yield
    get_logging_settings.cache_clear()


def test_get_logger_uses_service_name() -> None:
    logger = get_logger(service="serverless-toolkit-test-service-name")

    assert logger.name == "serverless-toolkit-test-service-name"


def test_get_logger_uses_explicit_level() -> None:
    logger = get_logger(
        service="serverless-toolkit-test-explicit-level",
        level=logging.DEBUG,
    )

    assert logger.level == logging.DEBUG


def test_logging_settings_loads_environment_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    settings = get_logging_settings()

    assert settings.log_level == "DEBUG"


def test_logging_settings_provider_reuses_instance() -> None:
    assert get_logging_settings() is get_logging_settings()


def test_logging_settings_are_immutable() -> None:
    settings = LoggingSettings()

    with pytest.raises(FrozenInstanceError):
        settings.log_level = "DEBUG"


def test_get_logger_uses_injected_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOG_LEVEL", "ERROR")
    settings = LoggingSettings(log_level="DEBUG")

    logger = get_logger(
        service="serverless-toolkit-test-injected-settings",
        settings=settings,
    )

    assert logger.level == logging.DEBUG


def test_get_logger_explicit_level_overrides_settings() -> None:
    settings = LoggingSettings(log_level="INFO")

    logger = get_logger(
        service="serverless-toolkit-test-explicit-override",
        level="DEBUG",
        settings=settings,
    )

    assert logger.level == logging.DEBUG


def test_logging_settings_provider_reloads_environment_after_cache_clear(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    first_settings = get_logging_settings()

    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    cached_settings = get_logging_settings()
    get_logging_settings.cache_clear()
    reloaded_settings = get_logging_settings()

    assert cached_settings is first_settings
    assert cached_settings.log_level == "INFO"
    assert reloaded_settings.log_level == "DEBUG"


def test_get_logger_writes_minimal_json_schema(
    capfd: pytest.CaptureFixture[str],
) -> None:
    logger = get_logger(service="serverless-toolkit-test-json")

    logger.info("Task started")

    captured = capfd.readouterr()
    log_data = json.loads(captured.err)

    assert log_data == {
        "level": "INFO",
        "message": "Task started",
        "logger": "serverless-toolkit-test-json",
    }


def test_get_logger_writes_exception_field(
    capfd: pytest.CaptureFixture[str],
) -> None:
    logger = get_logger(service="serverless-toolkit-test-exception")

    try:
        raise RuntimeError("boom")
    except RuntimeError:
        logger.exception("Task failed")

    captured = capfd.readouterr()
    log_data = json.loads(captured.err)

    assert log_data["level"] == "ERROR"
    assert log_data["message"] == "Task failed"
    assert log_data["logger"] == "serverless-toolkit-test-exception"
    assert "RuntimeError: boom" in log_data["exception"]


def test_get_logger_writes_extra_fields(
    capfd: pytest.CaptureFixture[str],
) -> None:
    logger = get_logger(service="serverless-toolkit-test-extra")

    logger.info(
        "Processed item",
        extra={
            "item_id": "item-123",
            "attempt": 2,
            "is_retry": True,
        },
    )

    captured = capfd.readouterr()
    log_data = json.loads(captured.err)

    assert log_data == {
        "attempt": 2,
        "is_retry": True,
        "item_id": "item-123",
        "level": "INFO",
        "logger": "serverless-toolkit-test-extra",
        "message": "Processed item",
    }


def test_get_logger_extra_fields_do_not_override_core_fields(
    capfd: pytest.CaptureFixture[str],
) -> None:
    logger = get_logger(service="serverless-toolkit-test-reserved-extra")

    logger.info(
        "Processed item",
        extra={
            "level": "FAKE",
            "logger": "fake-logger",
            "request_id": "request-123",
        },
    )

    captured = capfd.readouterr()
    log_data = json.loads(captured.err)

    assert log_data == {
        "level": "INFO",
        "logger": "serverless-toolkit-test-reserved-extra",
        "message": "Processed item",
        "request_id": "request-123",
    }


def test_get_logger_replaces_existing_handlers() -> None:
    logger = logging.getLogger("serverless-toolkit-test-handler-replacement")
    logger.addHandler(logging.NullHandler())

    configured_logger = get_logger(
        service="serverless-toolkit-test-handler-replacement"
    )

    assert configured_logger is logger
    assert len(configured_logger.handlers) == 1
    assert isinstance(configured_logger.handlers[0], logging.StreamHandler)
    assert configured_logger.propagate is False
