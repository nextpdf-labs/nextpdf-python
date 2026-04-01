"""Async AST API methods — delegates to PdfBackend."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..backends.protocol import PdfBackend
    from ..models.ast import (
        AstDocument,
        CitedTextBlock,
        ExtractCitedTablesResponse,
        GetAstDiffResponse,
        GetAstNodeResponse,
        SearchAstNodesResponse,
    )


class AsyncAstAPI:
    """Async wrapper for AST endpoints — delegates to a PdfBackend."""

    def __init__(self, backend: PdfBackend) -> None:
        self._backend = backend

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
            NextPDFLicenseError: Feature requires a higher-tier license on the remote server.
            QuotaExceededError: Daily page limit exceeded.
        """
        return await self._backend.get_document_ast(
            pdf_data,
            page_range_start=page_range_start,
            page_range_end=page_range_end,
            token_budget=token_budget,
        )

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
        return await self._backend.extract_cited_text(
            pdf_data,
            page_index=page_index,
            headings_only=headings_only,
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
        return await self._backend.get_ast_node(pdf_data, node_id)

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
        return await self._backend.search_ast_nodes(
            pdf_data,
            node_type=node_type,
            page_index=page_index,
            text_query=text_query,
            max_results=max_results,
        )

    async def extract_cited_tables(
        self,
        pdf_data: bytes,
        *,
        page_range: dict[str, int] | None = None,
    ) -> ExtractCitedTablesResponse:
        """Extract all tables from a PDF with citation anchors.

        Args:
            pdf_data: Raw PDF bytes.
            page_range: Optional dict with 'start' and 'end' page indices (0-based).

        Returns:
            ExtractCitedTablesResponse with table matrix and citation anchors.
        """
        return await self._backend.extract_cited_tables(
            pdf_data,
            page_range=page_range,
        )

    async def get_ast_diff(
        self,
        original_pdf_data: bytes,
        modified_pdf_data: bytes,
    ) -> GetAstDiffResponse:
        """Compare two PDFs and return structural AST differences.

        Args:
            original_pdf_data: Raw bytes of the original PDF.
            modified_pdf_data: Raw bytes of the modified PDF.

        Returns:
            GetAstDiffResponse with added/removed/changed node summary.
        """
        return await self._backend.get_ast_diff(original_pdf_data, modified_pdf_data)
