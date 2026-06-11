from __future__ import annotations

from collections.abc import Iterator
from dataclasses import FrozenInstanceError
from typing import Any

import pytest

from serverless_toolkit.aws.s3 import (
    S3Settings,
    get_s3_client,
    get_s3_settings,
    reset_s3_client_cache,
)
from serverless_toolkit.aws.s3.settings import build_s3_config


class FakeS3Client:
    def __init__(self) -> None:
        self.uploads: list[tuple[str, str, str]] = []
        self.downloads: list[tuple[str, str, str]] = []

    def upload_file(self, filename: str, bucket: str, key: str) -> None:
        self.uploads.append((filename, bucket, key))

    def download_file(self, bucket: str, key: str, filename: str) -> None:
        self.downloads.append((bucket, key, filename))


@pytest.fixture(autouse=True)
def clear_caches() -> Iterator[None]:
    reset_s3_client_cache()
    get_s3_settings.cache_clear()
    yield
    reset_s3_client_cache()
    get_s3_settings.cache_clear()


def test_settings_uses_s3_endpoint_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("S3_ENDPOINT_URL", "http://localhost:4566")
    monkeypatch.delenv("AWS_ENDPOINT_URL_S3", raising=False)

    assert S3Settings().client_kwargs()["endpoint_url"] == "http://localhost:4566"


def test_settings_uses_aws_endpoint_url_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("S3_ENDPOINT_URL", raising=False)
    monkeypatch.setenv("AWS_ENDPOINT_URL_S3", "http://localhost:4566")

    assert S3Settings().client_kwargs()["endpoint_url"] == "http://localhost:4566"


def test_settings_omits_endpoint_url_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("S3_ENDPOINT_URL", raising=False)
    monkeypatch.delenv("AWS_ENDPOINT_URL_S3", raising=False)

    assert "endpoint_url" not in S3Settings().client_kwargs()


def test_settings_applies_max_pool_connections() -> None:
    config = S3Settings(max_pool_connections=25).client_kwargs()["config"]

    assert config.max_pool_connections == 25
    assert build_s3_config(50).max_pool_connections == 50


def test_settings_rejects_non_positive_max_pool_connections() -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        S3Settings(max_pool_connections=0)


def test_settings_are_immutable() -> None:
    settings = S3Settings()

    with pytest.raises(FrozenInstanceError):
        settings.max_pool_connections = 20


def test_get_s3_settings_reuses_instance() -> None:
    assert get_s3_settings() is get_s3_settings()


def test_get_s3_client_reuses_client_for_equal_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, Any]] = []
    client = object()

    def fake_client(service_name: str, **kwargs: Any) -> object:
        calls.append({"service_name": service_name, **kwargs})
        return client

    monkeypatch.setattr("serverless_toolkit.aws.s3.s3.boto3.client", fake_client)

    first_client = get_s3_client(S3Settings(max_pool_connections=20))
    second_client = get_s3_client(S3Settings(max_pool_connections=20))

    assert first_client is client
    assert second_client is client
    assert len(calls) == 1
    assert calls[0]["service_name"] == "s3"


def test_reset_s3_client_cache_recreates_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clients: list[object] = []

    def fake_client(service_name: str, **kwargs: Any) -> object:
        client = object()
        clients.append(client)
        return client

    monkeypatch.setattr("serverless_toolkit.aws.s3.s3.boto3.client", fake_client)
    settings = S3Settings()

    first_client = get_s3_client(settings)
    reset_s3_client_cache()
    second_client = get_s3_client(settings)

    assert first_client is clients[0]
    assert second_client is clients[1]


def test_get_s3_client_exposes_managed_file_transfers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = FakeS3Client()
    monkeypatch.setattr(
        "serverless_toolkit.aws.s3.s3.boto3.client",
        lambda service_name, **kwargs: client,
    )

    s3_client = get_s3_client(S3Settings())
    s3_client.upload_file("/tmp/source.7z", "bucket", "raw/source.7z")
    s3_client.download_file("bucket", "raw/source.7z", "/tmp/target.7z")

    assert client.uploads == [("/tmp/source.7z", "bucket", "raw/source.7z")]
    assert client.downloads == [("bucket", "raw/source.7z", "/tmp/target.7z")]
