"""Async AST API methods."""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING, Any

import httpx

from .._http import DEFAULT_TIMEOUT, build_request_headers, raise_for_error_response
from ..models.ast import (
    AstDocument,
    AstNode,
    AstNodeMeta,
    CitedTextBlock,
    GetAstNodeResponse,
    SearchAstNodesResponse,
)

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

    def _parse_meta(self, data: dict[str, Any]) -> AstNodeMeta:
        """Extract _meta block from response data."""
        raw = data.get("_meta", {})
        if not isinstance(raw, dict):
            return AstNodeMeta()
        return AstNodeMeta(
            etag=raw.get("etag"),
            pages_processed=raw.get("pages_processed"),
        )

    async def get_ast_node(
        self,
        pdf_data: bytes,
        node_id: str,
    ) -> GetAstNodeResponse:
        """Retrieve a single AST node by its node ID.

        Args:
            pdf_data: Raw PDF bytes.
            node_id: Node ID in format ast:{hash6}:{pageIdx}:{seq}.

        Returns:
            GetAstNodeResponse containing the found node and metadata.

        Raises:
            NextPDFError: If the node is not found or request fails.
        """
        payload: dict[str, object] = {
            "pdf_data": base64.b64encode(pdf_data).decode(),
            "node_id": node_id,
        }

        async with httpx.AsyncClient(
            headers=build_request_headers(self._client.api_key),
            timeout=DEFAULT_TIMEOUT,
        ) as http:
            response = await http.post(
                f"{self._client.base_url}/v1/ast/node",
                json=payload,
            )

        raise_for_error_response(response)
        raw: dict[str, Any] = response.json()
        return GetAstNodeResponse(
            node=AstNode.model_validate(raw["node"]),
            meta=self._parse_meta(raw),
        )

    async def search_ast_nodes(
        self,
        pdf_data: bytes,
        *,
        node_type: str | None = None,
        page_index: int | None = None,
        text_query: str | None = None,
        max_results: int = 100,
    ) -> SearchAstNodesResponse:
        """Search AST nodes by type, page, or text content.

        Args:
            pdf_data: Raw PDF bytes.
            node_type: Filter by node type value (e.g. "heading", "table").
            page_index: 0-based page index filter.
            text_query: Case-insensitive substring search on textContent.
            max_results: Maximum nodes to return (default 100).

        Returns:
            SearchAstNodesResponse with matching nodes list.
        """
        payload: dict[str, object] = {
            "pdf_data": base64.b64encode(pdf_data).decode(),
            "max_results": max_results,
        }
        if node_type is not None:
            payload["node_type"] = node_type
        if page_index is not None:
            payload["page_index"] = page_index
        if text_query is not None:
            payload["text_query"] = text_query

        async with httpx.AsyncClient(
            headers=build_request_headers(self._client.api_key),
            timeout=DEFAULT_TIMEOUT,
        ) as http:
            response = await http.post(
                f"{self._client.base_url}/v1/ast/search",
                json=payload,
            )

        raise_for_error_response(response)
        raw = response.json()
        return SearchAstNodesResponse.model_validate(
            {
                "nodes": raw.get("nodes", []),
                "total_matches": raw.get("total_matches", 0),
                "truncated": raw.get("truncated", False),
                "meta": self._parse_meta(raw),
            }
        )
