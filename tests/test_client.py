from __future__ import annotations

import pytest

from nextpdf import AsyncNextPDF, NextPDF


class TestNextPDF:
    def test_raises_for_empty_base_url(self) -> None:
        with pytest.raises(ValueError, match="base_url"):
            NextPDF(base_url="", api_key="test-key")

    def test_raises_for_empty_api_key(self) -> None:
        with pytest.raises(ValueError, match="api_key"):
            NextPDF(base_url="https://example.com", api_key="")

    def test_trailing_slash_stripped(self) -> None:
        client = NextPDF(base_url="https://example.com/", api_key="test-key")
        assert client._async.base_url == "https://example.com"

    def test_has_ast_attribute(self) -> None:
        client = NextPDF(base_url="https://example.com", api_key="test-key")
        assert hasattr(client, "ast")

    def test_multiple_trailing_slashes_stripped(self) -> None:
        client = NextPDF(base_url="https://example.com///", api_key="key")
        # rstrip only removes trailing, so we verify at least trailing stripped
        assert not client._async.base_url.endswith("/")


class TestAsyncNextPDF:
    def test_raises_for_empty_base_url(self) -> None:
        with pytest.raises(ValueError, match="base_url"):
            AsyncNextPDF(base_url="", api_key="test-key")

    def test_raises_for_empty_api_key(self) -> None:
        with pytest.raises(ValueError, match="api_key"):
            AsyncNextPDF(base_url="https://example.com", api_key="")

    def test_trailing_slash_stripped(self) -> None:
        client = AsyncNextPDF(base_url="https://example.com/", api_key="test-key")
        assert client.base_url == "https://example.com"

    def test_has_ast_attribute(self) -> None:
        client = AsyncNextPDF(base_url="https://example.com", api_key="test-key")
        assert hasattr(client, "ast")

    def test_api_version_default(self) -> None:
        client = AsyncNextPDF(base_url="https://example.com", api_key="key")
        assert client.api_version == "v1"

    def test_api_version_custom(self) -> None:
        client = AsyncNextPDF(base_url="https://example.com", api_key="key", api_version="v2")
        assert client.api_version == "v2"

    async def test_async_context_manager(self) -> None:
        async with AsyncNextPDF(base_url="https://example.com", api_key="key") as client:
            assert client.base_url == "https://example.com"
