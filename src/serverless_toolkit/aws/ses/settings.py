from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import cache
from typing import Any

from botocore.config import Config


@dataclass(frozen=True)
class SESSettings:
    """Runtime configuration for SES SDK clients."""

    region_name: str | None = None
    endpoint_url: str | None = field(
        default_factory=lambda: (
            os.getenv("SES_ENDPOINT_URL") or os.getenv("AWS_ENDPOINT_URL_SES")
        )
    )
    max_pool_connections: int = field(
        default_factory=lambda: int(os.getenv("SES_MAX_POOL_CONNECTIONS", "10"))
    )

    def __post_init__(self) -> None:
        if self.max_pool_connections < 1:
            msg = "max_pool_connections must be greater than zero"
            raise ValueError(msg)

    def client_kwargs(self) -> dict[str, Any]:
        """Return boto3 client kwargs with optional endpoint overrides."""
        kwargs: dict[str, Any] = {
            "config": build_ses_config(self.max_pool_connections),
        }

        if self.region_name:
            kwargs["region_name"] = self.region_name

        if self.endpoint_url:
            kwargs["endpoint_url"] = self.endpoint_url

        return kwargs


@cache
def get_ses_settings() -> SESSettings:
    """Return the shared environment-derived SES settings."""
    return SESSettings()


def build_ses_config(max_pool_connections: int) -> Config:
    """Build botocore config for SES clients."""
    return Config(max_pool_connections=max_pool_connections)
