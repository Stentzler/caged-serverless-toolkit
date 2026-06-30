from __future__ import annotations

from collections.abc import Iterator
from dataclasses import FrozenInstanceError
from typing import Any

import pytest

from serverless_toolkit.aws.ses import (
    SESSettings,
    get_ses_client,
    get_ses_settings,
    reset_ses_client_cache,
)
from serverless_toolkit.aws.ses.settings import build_ses_config


class FakeSESClient:
    def __init__(self) -> None:
        self.email_requests: list[dict[str, Any]] = []

    def send_email(self, **kwargs: Any) -> dict[str, Any]:
        self.email_requests.append(kwargs)
        return {"MessageId": "message-id"}


@pytest.fixture(autouse=True)
def clear_caches() -> Iterator[None]:
    reset_ses_client_cache()
    get_ses_settings.cache_clear()
    yield
    reset_ses_client_cache()
    get_ses_settings.cache_clear()


def test_settings_uses_ses_endpoint_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SES_ENDPOINT_URL", "http://localhost:4566")
    monkeypatch.delenv("AWS_ENDPOINT_URL_SES", raising=False)

    assert SESSettings().client_kwargs()["endpoint_url"] == "http://localhost:4566"


def test_settings_uses_aws_endpoint_url_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SES_ENDPOINT_URL", raising=False)
    monkeypatch.setenv("AWS_ENDPOINT_URL_SES", "http://localhost:4566")

    assert SESSettings().client_kwargs()["endpoint_url"] == "http://localhost:4566"


def test_settings_omits_endpoint_url_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SES_ENDPOINT_URL", raising=False)
    monkeypatch.delenv("AWS_ENDPOINT_URL_SES", raising=False)

    assert "endpoint_url" not in SESSettings().client_kwargs()


def test_settings_applies_region_name() -> None:
    assert SESSettings(region_name="us-east-1").client_kwargs()["region_name"] == (
        "us-east-1"
    )


def test_settings_applies_max_pool_connections() -> None:
    config = SESSettings(max_pool_connections=25).client_kwargs()["config"]

    assert config.max_pool_connections == 25
    assert build_ses_config(50).max_pool_connections == 50


def test_settings_rejects_non_positive_max_pool_connections() -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        SESSettings(max_pool_connections=0)


def test_settings_are_immutable() -> None:
    settings = SESSettings()

    with pytest.raises(FrozenInstanceError):
        settings.max_pool_connections = 20


def test_get_ses_settings_reuses_instance() -> None:
    assert get_ses_settings() is get_ses_settings()


def test_get_ses_client_reuses_client_for_equal_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, Any]] = []
    client = object()

    def fake_client(service_name: str, **kwargs: Any) -> object:
        calls.append({"service_name": service_name, **kwargs})
        return client

    monkeypatch.setattr("serverless_toolkit.aws.ses.ses.boto3.client", fake_client)

    first_client = get_ses_client(SESSettings(max_pool_connections=20))
    second_client = get_ses_client(SESSettings(max_pool_connections=20))

    assert first_client is client
    assert second_client is client
    assert len(calls) == 1
    assert calls[0]["service_name"] == "sesv2"


def test_reset_ses_client_cache_recreates_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clients: list[object] = []

    def fake_client(service_name: str, **kwargs: Any) -> object:
        client = object()
        clients.append(client)
        return client

    monkeypatch.setattr("serverless_toolkit.aws.ses.ses.boto3.client", fake_client)
    settings = SESSettings()

    first_client = get_ses_client(settings)
    reset_ses_client_cache()
    second_client = get_ses_client(settings)

    assert first_client is clients[0]
    assert second_client is clients[1]


def test_get_ses_client_exposes_send_email(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = FakeSESClient()
    monkeypatch.setattr(
        "serverless_toolkit.aws.ses.ses.boto3.client",
        lambda service_name, **kwargs: client,
    )

    ses_client = get_ses_client(SESSettings())
    response = ses_client.send_email(
        FromEmailAddress="sender@example.com",
        Destination={"ToAddresses": ["receiver@example.com"]},
    )

    assert response == {"MessageId": "message-id"}
    assert client.email_requests == [
        {
            "FromEmailAddress": "sender@example.com",
            "Destination": {"ToAddresses": ["receiver@example.com"]},
        }
    ]
