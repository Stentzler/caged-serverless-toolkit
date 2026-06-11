from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import cache
from typing import Any

from botocore.config import Config


@dataclass(frozen=True)
class S3Settings:
    """Runtime configuration for S3 SDK clients."""

    endpoint_url: str | None = field(
        default_factory=lambda: (
            os.getenv("S3_ENDPOINT_URL") or os.getenv("AWS_ENDPOINT_URL_S3")
        )
    )
    max_pool_connections: int = field(
        default_factory=lambda: int(os.getenv("S3_MAX_POOL_CONNECTIONS", "10"))
    )

    def __post_init__(self) -> None:
        if self.max_pool_connections < 1:
            msg = "max_pool_connections must be greater than zero"
            raise ValueError(msg)

    def client_kwargs(self) -> dict[str, Any]:
        """Return boto3 client kwargs with optional endpoint overrides."""
        kwargs: dict[str, Any] = {
            "config": build_s3_config(self.max_pool_connections),
        }

        if self.endpoint_url:
            kwargs["endpoint_url"] = self.endpoint_url

        return kwargs


@cache
def get_s3_settings() -> S3Settings:
    """Return the shared environment-derived S3 settings."""
    return S3Settings()


def build_s3_config(max_pool_connections: int) -> Config:
    """Build botocore config for S3 clients."""
    return Config(max_pool_connections=max_pool_connections)
