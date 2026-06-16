from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import cache
from typing import Any

from botocore.config import Config


@dataclass(frozen=True)
class DynamoDBSettings:
    """Runtime configuration for DynamoDB SDK resources."""

    region_name: str | None = None
    endpoint_url: str | None = field(
        default_factory=lambda: (
            os.getenv("DYNAMODB_ENDPOINT_URL") or os.getenv("AWS_ENDPOINT_URL_DYNAMODB")
        )
    )
    max_pool_connections: int = field(
        default_factory=lambda: int(os.getenv("DYNAMODB_MAX_POOL_CONNECTIONS", "10"))
    )

    def __post_init__(self) -> None:
        if self.max_pool_connections < 1:
            msg = "max_pool_connections must be greater than zero"
            raise ValueError(msg)

    def resource_kwargs(self) -> dict[str, Any]:
        """Return boto3 resource kwargs without production-only endpoint overrides."""
        kwargs: dict[str, Any] = {
            "config": build_dynamodb_config(self.max_pool_connections),
        }

        if self.region_name:
            kwargs["region_name"] = self.region_name

        if self.endpoint_url:
            kwargs["endpoint_url"] = self.endpoint_url

        return kwargs


@cache
def get_dynamodb_settings() -> DynamoDBSettings:
    """Return the shared environment-derived DynamoDB settings."""
    return DynamoDBSettings()


def build_dynamodb_config(max_pool_connections: int) -> Config:
    """Build botocore config for DynamoDB clients."""
    return Config(max_pool_connections=max_pool_connections)
