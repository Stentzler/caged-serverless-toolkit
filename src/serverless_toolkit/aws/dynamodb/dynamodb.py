from __future__ import annotations

from functools import cache
from typing import Protocol

import boto3

from serverless_toolkit.aws.dynamodb.settings import (
    DynamoDBSettings,
    get_dynamodb_settings,
)


class DynamoDBResourceProtocol(Protocol):
    """Minimal DynamoDB resource operations exposed by boto3."""

    def Table(self, name: str) -> object: ...


def get_dynamodb_resource(
    settings: DynamoDBSettings | None = None,
) -> DynamoDBResourceProtocol:
    """Return a DynamoDB resource cached by its effective settings."""
    return _get_cached_dynamodb_resource(settings or get_dynamodb_settings())


@cache
def _get_cached_dynamodb_resource(
    settings: DynamoDBSettings,
) -> DynamoDBResourceProtocol:
    """Create and cache a DynamoDB resource for immutable settings."""
    return boto3.resource("dynamodb", **settings.resource_kwargs())


def get_dynamodb_table(
    table_name: str,
    settings: DynamoDBSettings | None = None,
) -> object:
    """Return a DynamoDB table from the shared cached resource."""
    return get_dynamodb_resource(settings).Table(table_name)


def reset_dynamodb_resource_cache() -> None:
    """Clear all cached DynamoDB resources."""
    _get_cached_dynamodb_resource.cache_clear()
