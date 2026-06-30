from __future__ import annotations

from collections.abc import Iterator
from dataclasses import FrozenInstanceError
from typing import Any

import pytest

from serverless_toolkit.aws.secretsmanager import (
    SecretsManagerSettings,
    get_secretsmanager_client,
    get_secretsmanager_settings,
    reset_secretsmanager_client_cache,
)
from serverless_toolkit.aws.secretsmanager.settings import (
    build_secretsmanager_config,
)


class FakeSecretsManagerClient:
    def __init__(self) -> None:
        self.secret_requests: list[dict[str, Any]] = []

    def get_secret_value(self, **kwargs: Any) -> dict[str, Any]:
        self.secret_requests.append(kwargs)
        return {"SecretString": '{"token":"secret"}'}


@pytest.fixture(autouse=True)
def clear_caches() -> Iterator[None]:
    reset_secretsmanager_client_cache()
    get_secretsmanager_settings.cache_clear()
    yield
    reset_secretsmanager_client_cache()
    get_secretsmanager_settings.cache_clear()


def test_settings_uses_secrets_manager_endpoint_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SECRETS_MANAGER_ENDPOINT_URL", "http://localhost:4566")
    monkeypatch.delenv("AWS_ENDPOINT_URL_SECRETS_MANAGER", raising=False)

    assert SecretsManagerSettings().client_kwargs()["endpoint_url"] == (
        "http://localhost:4566"
    )


def test_settings_uses_aws_endpoint_url_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SECRETS_MANAGER_ENDPOINT_URL", raising=False)
    monkeypatch.setenv("AWS_ENDPOINT_URL_SECRETS_MANAGER", "http://localhost:4566")

    assert SecretsManagerSettings().client_kwargs()["endpoint_url"] == (
        "http://localhost:4566"
    )


def test_settings_omits_endpoint_url_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SECRETS_MANAGER_ENDPOINT_URL", raising=False)
    monkeypatch.delenv("AWS_ENDPOINT_URL_SECRETS_MANAGER", raising=False)

    assert "endpoint_url" not in SecretsManagerSettings().client_kwargs()


def test_settings_applies_region_name() -> None:
    assert (
        SecretsManagerSettings(region_name="us-east-1").client_kwargs()["region_name"]
        == "us-east-1"
    )


def test_settings_applies_max_pool_connections() -> None:
    config = SecretsManagerSettings(max_pool_connections=25).client_kwargs()["config"]

    assert config.max_pool_connections == 25
    assert build_secretsmanager_config(50).max_pool_connections == 50


def test_settings_rejects_non_positive_max_pool_connections() -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        SecretsManagerSettings(max_pool_connections=0)


def test_settings_are_immutable() -> None:
    settings = SecretsManagerSettings()

    with pytest.raises(FrozenInstanceError):
        settings.max_pool_connections = 20


def test_get_secretsmanager_settings_reuses_instance() -> None:
    assert get_secretsmanager_settings() is get_secretsmanager_settings()


def test_get_secretsmanager_client_reuses_client_for_equal_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, Any]] = []
    client = object()

    def fake_client(service_name: str, **kwargs: Any) -> object:
        calls.append({"service_name": service_name, **kwargs})
        return client

    monkeypatch.setattr(
        "serverless_toolkit.aws.secretsmanager.secretsmanager.boto3.client",
        fake_client,
    )

    first_client = get_secretsmanager_client(
        SecretsManagerSettings(max_pool_connections=20)
    )
    second_client = get_secretsmanager_client(
        SecretsManagerSettings(max_pool_connections=20)
    )

    assert first_client is client
    assert second_client is client
    assert len(calls) == 1
    assert calls[0]["service_name"] == "secretsmanager"


def test_reset_secretsmanager_client_cache_recreates_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clients: list[object] = []

    def fake_client(service_name: str, **kwargs: Any) -> object:
        client = object()
        clients.append(client)
        return client

    monkeypatch.setattr(
        "serverless_toolkit.aws.secretsmanager.secretsmanager.boto3.client",
        fake_client,
    )
    settings = SecretsManagerSettings()

    first_client = get_secretsmanager_client(settings)
    reset_secretsmanager_client_cache()
    second_client = get_secretsmanager_client(settings)

    assert first_client is clients[0]
    assert second_client is clients[1]


def test_get_secretsmanager_client_exposes_get_secret_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = FakeSecretsManagerClient()
    monkeypatch.setattr(
        "serverless_toolkit.aws.secretsmanager.secretsmanager.boto3.client",
        lambda service_name, **kwargs: client,
    )

    secrets_client = get_secretsmanager_client(SecretsManagerSettings())
    response = secrets_client.get_secret_value(SecretId="slack-token")

    assert response == {"SecretString": '{"token":"secret"}'}
    assert client.secret_requests == [{"SecretId": "slack-token"}]
