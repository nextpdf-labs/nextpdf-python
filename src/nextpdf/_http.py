"""HTTP transport layer with retry and timeout handling."""

from __future__ import annotations

import platform
import sys
from typing import Any

import httpx

from .models.errors import (
    AstBuildTimeoutError,
    AstNoStructTreeError,
    NextPDFAPIError,
    NextPDFLicenseError,
    QuotaExceededError,
)

DEFAULT_TIMEOUT = httpx.Timeout(60.0, connect=10.0)
DEFAULT_RETRIES = 3
_PY_VERSION = f"{sys.version_info.major}.{sys.version_info.minor}"
USER_AGENT = f"nextpdf-python/0.1.0 (python {_PY_VERSION})"

__all__ = [
    "DEFAULT_RETRIES",
    "DEFAULT_TIMEOUT",
    "USER_AGENT",
    "build_request_headers",
    "raise_for_error_response",
]


def build_request_headers(api_key: str) -> dict[str, str]:
    """Build standard HTTP headers for NextPDF API requests."""
    return {
        "Authorization": f"Bearer {api_key}",
        "User-Agent": USER_AGENT,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def raise_for_error_response(response: httpx.Response) -> None:
    """Map HTTP error responses to typed NextPDF exceptions."""
    if response.status_code < 400:
        return

    try:
        body: dict[str, Any] = response.json()
    except Exception:
        body = {}

    error_code: str | None = body.get("code") or body.get("error_code")
    message: str = body.get("message") or body.get("detail") or response.text or "Unknown error"

    if response.status_code == 402:
        raise NextPDFLicenseError(message)

    if response.status_code == 422 and error_code == "ast/no-struct-tree":
        raise AstNoStructTreeError()

    if response.status_code == 504 and error_code == "ast/build-timeout":
        raise AstBuildTimeoutError()

    if response.status_code == 429:
        retry_after_str = response.headers.get("Retry-After")
        retry_after = (
            int(retry_after_str) if retry_after_str and retry_after_str.isdigit() else None
        )
        raise QuotaExceededError(message, retry_after=retry_after)

    raise NextPDFAPIError(message, status_code=response.status_code, error_code=error_code)
