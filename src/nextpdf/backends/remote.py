"""Remote backend — HTTP-based PDF extraction via the NextPDF Connect API."""

from __future__ import annotations

import base64
from typing import Any

import httpx

from nextpdf._http import DEFAULT_TIMEOUT, build_request_headers, raise_for_error_response
from nextpdf.models.ast import (
    AstDiffEntry,
    AstDiffSummary,
    AstDocument,
    AstNode,
    AstNodeMeta,
    CitedTableBlock,
    CitedTextBlock,
    ExtractCitedTablesResponse,
    GetAstDiffResponse,
    GetAstNodeResponse,
    SearchAstNodesResponse,
)


class RemoteBackend:
    """PdfBackend implementation backed by the NextPDF Connect HTTP API.

    Uses a single persistent ``httpx.AsyncClient`` for connection pooling.
    Must be used as an async context manager **or** explicitly closed via
    :meth:`close` to release underlying connections.
    """

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        api_version: str = "v1",
    ) -> None:
        if not base_url:
            raise ValueError("base_url must not be empty")
        if not api_key:
            raise ValueError("api_key must not be empty")

        self._base_url: str = base_url.rstrip("/")
        self._api_key: str = api_key
        self._api_version: str = api_version
        self._http: httpx.AsyncClient = httpx.AsyncClient(
            headers=build_request_headers(api_key),
            timeout=DEFAULT_TIMEOUT,
        )

    # -- lifecycle ------------------------------------------------------------

    async def __aenter__(self) -> RemoteBackend:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying HTTP client and release connections."""
        await self._http.aclose()

    # -- helpers --------------------------------------------------------------

    @staticmethod
    def _parse_meta(data: dict[str, Any]) -> AstNodeMeta:
        """Extract ``_meta`` block from response data."""
        raw = data.get("_meta", {})
        if not isinstance(raw, dict):
            return AstNodeMeta()
        return AstNodeMeta(
            etag=raw.get("etag"),  # pyright: ignore[reportUnknownArgumentType,reportUnknownMemberType]
            pages_processed=raw.get("pages_processed"),  # pyright: ignore[reportUnknownArgumentType,reportUnknownMemberType]
        )

    # -- PdfBackend protocol methods ------------------------------------------

    async def get_document_ast(
        self,
        pdf_data: bytes,
        *,
        page_range_start: int | None = None,
        page_range_end: int | None = None,
        token_budget: int | None = None,
    ) -> AstDocument:
        """Build a Semantic AST from PDF bytes."""
        payload: dict[str, object] = {
            "pdf_data": base64.b64encode(pdf_data).decode(),
        }
        if page_range_start is not None:
            payload["page_range_start"] = page_range_start
        if page_range_end is not None:
            payload["page_range_end"] = page_range_end
        if token_budget is not None:
            payload["token_budget"] = token_budget

        response = await self._http.post(
            f"{self._base_url}/v1/ast/document",
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
        """Extract text blocks with citation anchors."""
        payload: dict[str, object] = {
            "pdf_data": base64.b64encode(pdf_data).decode(),
        }
        if page_index is not None:
            payload["page_index"] = page_index
        if headings_only:
            payload["headings_only"] = True

        response = await self._http.post(
            f"{self._base_url}/v1/ast/extract-cited-text",
            json=payload,
        )
        raise_for_error_response(response)
        data: dict[str, list[dict[str, object]]] = response.json()
        return [CitedTextBlock.model_validate(block) for block in data.get("blocks", [])]

    async def extract_cited_tables(
        self,
        pdf_data: bytes,
        *,
        page_range: dict[str, int] | None = None,
    ) -> ExtractCitedTablesResponse:
        """Extract all tables from a PDF with citation anchors."""
        payload: dict[str, object] = {
            "pdf_data": base64.b64encode(pdf_data).decode("ascii"),
        }
        if page_range is not None:
            payload["page_range"] = page_range

        response = await self._http.post(
            f"{self._base_url}/v1/tools/extract_cited_tables",
            json=payload,
        )
        raise_for_error_response(response)
        raw: dict[str, Any] = response.json()
        meta = self._parse_meta(raw)
        return ExtractCitedTablesResponse(
            tables=[CitedTableBlock.model_validate(t) for t in raw.get("tables", [])],
            table_count=raw.get("table_count", 0),
            pages_processed=meta.pages_processed,
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
        """Search AST nodes by type, page, or text content."""
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

        response = await self._http.post(
            f"{self._base_url}/v1/ast/search",
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

    async def get_ast_node(
        self,
        pdf_data: bytes,
        node_id: str,
    ) -> GetAstNodeResponse:
        """Retrieve a single AST node by its node ID."""
        payload: dict[str, object] = {
            "pdf_data": base64.b64encode(pdf_data).decode(),
            "node_id": node_id,
        }

        response = await self._http.post(
            f"{self._base_url}/v1/ast/node",
            json=payload,
        )
        raise_for_error_response(response)
        raw: dict[str, Any] = response.json()
        return GetAstNodeResponse(
            node=AstNode.model_validate(raw["node"]),
            meta=self._parse_meta(raw),
        )

    async def get_ast_diff(
        self,
        original_pdf_data: bytes,
        modified_pdf_data: bytes,
    ) -> GetAstDiffResponse:
        """Compare two PDFs and return structural AST differences."""
        payload: dict[str, object] = {
            "original_pdf_data": base64.b64encode(original_pdf_data).decode("ascii"),
            "modified_pdf_data": base64.b64encode(modified_pdf_data).decode("ascii"),
        }

        response = await self._http.post(
            f"{self._base_url}/v1/tools/get_ast_diff",
            json=payload,
        )
        raise_for_error_response(response)
        raw = response.json()
        meta = self._parse_meta(raw)
        return GetAstDiffResponse(
            original_page_count=raw["original_page_count"],
            modified_page_count=raw["modified_page_count"],
            summary=AstDiffSummary.model_validate(raw["summary"]),
            diff=[AstDiffEntry.model_validate(e) for e in raw.get("diff", [])],
            pages_processed=meta.pages_processed,
        )
