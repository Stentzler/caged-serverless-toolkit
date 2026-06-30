from __future__ import annotations

from functools import cache
from typing import Any, Protocol

import boto3

from serverless_toolkit.aws.secretsmanager.settings import (
    SecretsManagerSettings,
    get_secretsmanager_settings,
)


class SecretsManagerClientProtocol(Protocol):
    """Secret retrieval operations exposed by the Secrets Manager client."""

    def get_secret_value(self, **kwargs: Any) -> dict[str, Any]: ...


def get_secretsmanager_client(
    settings: SecretsManagerSettings | None = None,
) -> SecretsManagerClientProtocol:
    """Return a Secrets Manager client cached by its effective settings."""
    return _get_cached_secretsmanager_client(settings or get_secretsmanager_settings())


@cache
def _get_cached_secretsmanager_client(
    settings: SecretsManagerSettings,
) -> SecretsManagerClientProtocol:
    """Create and cache a Secrets Manager client for immutable settings."""
    return boto3.client("secretsmanager", **settings.client_kwargs())


def reset_secretsmanager_client_cache() -> None:
    """Clear all cached Secrets Manager clients."""
    _get_cached_secretsmanager_client.cache_clear()
