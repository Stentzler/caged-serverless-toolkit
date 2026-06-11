from __future__ import annotations

from functools import cache
from typing import Protocol

import boto3

from serverless_toolkit.aws.s3.settings import S3Settings, get_s3_settings


class S3ClientProtocol(Protocol):
    """Managed file transfer operations exposed by the S3 client."""

    def upload_file(self, filename: str, bucket: str, key: str) -> None: ...

    def download_file(self, bucket: str, key: str, filename: str) -> None: ...


def get_s3_client(settings: S3Settings | None = None) -> S3ClientProtocol:
    """Return an S3 client cached by its effective settings."""
    return _get_cached_s3_client(settings or get_s3_settings())


@cache
def _get_cached_s3_client(settings: S3Settings) -> S3ClientProtocol:
    """Create and cache an S3 client for immutable settings."""
    return boto3.client("s3", **settings.client_kwargs())


def reset_s3_client_cache() -> None:
    """Clear all cached S3 clients."""
    _get_cached_s3_client.cache_clear()
