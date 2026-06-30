from __future__ import annotations

from functools import cache
from typing import Any, Protocol

import boto3

from serverless_toolkit.aws.ses.settings import SESSettings, get_ses_settings


class SESClientProtocol(Protocol):
    """Email send operations exposed by the SESv2 client."""

    def send_email(self, **kwargs: Any) -> dict[str, Any]: ...


def get_ses_client(settings: SESSettings | None = None) -> SESClientProtocol:
    """Return an SESv2 client cached by its effective settings."""
    return _get_cached_ses_client(settings or get_ses_settings())


@cache
def _get_cached_ses_client(settings: SESSettings) -> SESClientProtocol:
    """Create and cache an SESv2 client for immutable settings."""
    return boto3.client("sesv2", **settings.client_kwargs())


def reset_ses_client_cache() -> None:
    """Clear all cached SESv2 clients."""
    _get_cached_ses_client.cache_clear()
