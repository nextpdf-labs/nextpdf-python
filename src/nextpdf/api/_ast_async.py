"""Async AST API methods."""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING

import httpx

from .._http import DEFAULT_TIMEOUT, build_request_headers, raise_for_error_response
from ..models.ast import AstDocument, CitedTextBlock

if TYPE_CHECKING:
    from .._async_client import AsyncNextPDF


class AsyncAstAPI:
    """Async wrapper for AST endpoints."""

    def __init__(self, client: AsyncNextPDF) -> None:
        self._client = client

    async def get_document_ast(
        self,
        pdf_data: bytes,
        *,
        page_range_start: int | None = None,
        page_range_end: int | None = None,
        token_budget: int | None = None,
    ) -> AstDocument:
        """
        Build a Semantic AST from PDF bytes.

        Args:
            pdf_data: Raw PDF bytes.
            page_range_start: 0-based start page (inclusive). None = from beginning.
            page_range_end: 0-based end page (inclusive). None = to end.
            token_budget: Approximate token limit for the returned AST.

        Returns:
            AstDocument with full tree and citation anchors.

        Raises:
            AstNoStructTreeError: PDF is untagged and heuristic not enabled.
            NextPDFLicenseError: Requires Pro or higher tier.
            QuotaExceededError: Daily page limit exceeded.
        """
        payload: dict[str, object] = {
            "pdf_data": base64.b64encode(pdf_data).decode(),
        }
        if page_range_start is not None:
            payload["page_range_start"] = page_range_start
        if page_range_end is not None:
            payload["page_range_end"] = page_range_end
        if token_budget is not None:
            payload["token_budget"] = token_budget

        async with httpx.AsyncClient(
            headers=build_request_headers(self._client.api_key),
            timeout=DEFAULT_TIMEOUT,
        ) as http:
            response = await http.post(
                f"{self._client.base_url}/v1/ast/document",
                json=payload,
            )

        raise_for_error_response(response)
        return AstDocument.model_validate(response.json())

    async def extract_cited_text(
        self,
        pdf_data: bytes,
        *,
        page_index: int | None = None,
        headings_only: bool = False,
    ) -> list[CitedTextBlock]:
        """
        Extract text blocks with citation anchors.

        Args:
            pdf_data: Raw PDF bytes.
            page_index: If set, extract only from this page (0-based).
            headings_only: If True, extract only heading nodes.

        Returns:
            List of CitedTextBlock objects, each with a citation anchor.
        """
        payload: dict[str, object] = {
            "pdf_data": base64.b64encode(pdf_data).decode(),
        }
        if page_index is not None:
            payload["page_index"] = page_index
        if headings_only:
            payload["headings_only"] = True

        async with httpx.AsyncClient(
            headers=build_request_headers(self._client.api_key),
            timeout=DEFAULT_TIMEOUT,
        ) as http:
            response = await http.post(
                f"{self._client.base_url}/v1/ast/extract-cited-text",
                json=payload,
            )

        raise_for_error_response(response)
        data: dict[str, list[dict[str, object]]] = response.json()
        return [CitedTextBlock.model_validate(block) for block in data.get("blocks", [])]
