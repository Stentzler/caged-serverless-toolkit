from __future__ import annotations

from collections.abc import Iterator
from dataclasses import FrozenInstanceError, dataclass
from typing import Any

import pytest

from serverless_toolkit.aws.dynamodb import (
    DynamoDBSettings,
    get_dynamodb_resource,
    get_dynamodb_settings,
    get_dynamodb_table,
    reset_dynamodb_resource_cache,
)
from serverless_toolkit.aws.dynamodb.settings import build_dynamodb_config


@dataclass
class FakeDynamoDBResource:
    table_names: list[str]

    def Table(self, name: str) -> dict[str, str]:
        self.table_names.append(name)
        return {"table_name": name}


@pytest.fixture(autouse=True)
def clear_caches() -> Iterator[None]:
    reset_dynamodb_resource_cache()
    get_dynamodb_settings.cache_clear()
    yield
    reset_dynamodb_resource_cache()
    get_dynamodb_settings.cache_clear()


def test_settings_uses_dynamodb_endpoint_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DYNAMODB_ENDPOINT_URL", "http://localhost:8000")
    monkeypatch.delenv("AWS_ENDPOINT_URL_DYNAMODB", raising=False)

    settings = DynamoDBSettings()

    assert settings.resource_kwargs()["endpoint_url"] == "http://localhost:8000"


def test_settings_uses_aws_endpoint_url_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DYNAMODB_ENDPOINT_URL", raising=False)
    monkeypatch.setenv("AWS_ENDPOINT_URL_DYNAMODB", "http://localhost:8000")

    settings = DynamoDBSettings()

    assert settings.resource_kwargs()["endpoint_url"] == "http://localhost:8000"


def test_settings_omits_endpoint_url_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DYNAMODB_ENDPOINT_URL", raising=False)
    monkeypatch.delenv("AWS_ENDPOINT_URL_DYNAMODB", raising=False)

    settings = DynamoDBSettings()

    assert "endpoint_url" not in settings.resource_kwargs()


def test_settings_applies_region_name() -> None:
    settings = DynamoDBSettings(region_name="us-east-1")

    assert settings.resource_kwargs()["region_name"] == "us-east-1"


def test_settings_applies_max_pool_connections(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DYNAMODB_MAX_POOL_CONNECTIONS", "25")

    settings = DynamoDBSettings()
    config = settings.resource_kwargs()["config"]

    assert config.max_pool_connections == 25


def test_build_dynamodb_config_sets_max_pool_connections() -> None:
    config = build_dynamodb_config(50)

    assert config.max_pool_connections == 50


def test_dynamodb_settings_provider_reuses_instance() -> None:
    assert get_dynamodb_settings() is get_dynamodb_settings()


def test_dynamodb_settings_are_immutable() -> None:
    settings = DynamoDBSettings()

    with pytest.raises(FrozenInstanceError):
        settings.max_pool_connections = 20


def test_dynamodb_settings_provider_reloads_environment_after_cache_clear(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DYNAMODB_MAX_POOL_CONNECTIONS", "15")
    first_settings = get_dynamodb_settings()

    monkeypatch.setenv("DYNAMODB_MAX_POOL_CONNECTIONS", "30")
    cached_settings = get_dynamodb_settings()
    get_dynamodb_settings.cache_clear()
    reloaded_settings = get_dynamodb_settings()

    assert cached_settings is first_settings
    assert cached_settings.max_pool_connections == 15
    assert reloaded_settings.max_pool_connections == 30


def test_settings_rejects_non_positive_max_pool_connections() -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        DynamoDBSettings(max_pool_connections=0)


def test_get_dynamodb_resource_reuses_cached_resource(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, Any]] = []
    fake_resource = FakeDynamoDBResource(table_names=[])

    def fake_boto3_resource(service_name: str, **kwargs: Any) -> FakeDynamoDBResource:
        calls.append({"service_name": service_name, **kwargs})
        return fake_resource

    monkeypatch.setattr(
        "serverless_toolkit.aws.dynamodb.dynamodb.boto3.resource",
        fake_boto3_resource,
    )

    settings = DynamoDBSettings(max_pool_connections=20)

    first_resource = get_dynamodb_resource(settings)
    second_resource = get_dynamodb_resource(DynamoDBSettings(max_pool_connections=20))

    assert first_resource is fake_resource
    assert second_resource is fake_resource
    assert len(calls) == 1
    assert calls[0]["service_name"] == "dynamodb"


def test_get_dynamodb_resource_caches_distinct_settings_separately(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resources: list[FakeDynamoDBResource] = []

    def fake_boto3_resource(
        service_name: str,
        **kwargs: Any,
    ) -> FakeDynamoDBResource:
        resource = FakeDynamoDBResource(table_names=[])
        resources.append(resource)
        return resource

    monkeypatch.setattr(
        "serverless_toolkit.aws.dynamodb.dynamodb.boto3.resource",
        fake_boto3_resource,
    )

    first_resource = get_dynamodb_resource(DynamoDBSettings(max_pool_connections=10))
    second_resource = get_dynamodb_resource(DynamoDBSettings(max_pool_connections=20))

    assert first_resource is resources[0]
    assert second_resource is resources[1]
    assert first_resource is not second_resource


def test_reset_dynamodb_resource_cache_recreates_resource(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resources: list[FakeDynamoDBResource] = []

    def fake_boto3_resource(
        service_name: str,
        **kwargs: Any,
    ) -> FakeDynamoDBResource:
        resource = FakeDynamoDBResource(table_names=[])
        resources.append(resource)
        return resource

    monkeypatch.setattr(
        "serverless_toolkit.aws.dynamodb.dynamodb.boto3.resource",
        fake_boto3_resource,
    )

    settings = DynamoDBSettings()
    first_resource = get_dynamodb_resource(settings)
    reset_dynamodb_resource_cache()
    second_resource = get_dynamodb_resource(settings)

    assert first_resource is resources[0]
    assert second_resource is resources[1]


def test_get_dynamodb_table_returns_table_from_resource(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_resource = FakeDynamoDBResource(table_names=[])

    def fake_boto3_resource(service_name: str, **kwargs: Any) -> FakeDynamoDBResource:
        return fake_resource

    monkeypatch.setattr(
        "serverless_toolkit.aws.dynamodb.dynamodb.boto3.resource",
        fake_boto3_resource,
    )

    table = get_dynamodb_table("downloaded_files_registry", DynamoDBSettings())

    assert table == {"table_name": "downloaded_files_registry"}
    assert fake_resource.table_names == ["downloaded_files_registry"]
