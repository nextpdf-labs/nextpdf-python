"""Sync AST API methods (thin wrapper over AsyncAstAPI)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .._sync import run_sync

if TYPE_CHECKING:
    from ..models.ast import (
        AstDocument,
        CitedTextBlock,
        ExtractCitedTablesResponse,
        GetAstDiffResponse,
        GetAstNodeResponse,
        SearchAstNodesResponse,
    )
    from ._ast_async import AsyncAstAPI


class AstAPI:
    """Synchronous wrapper for AST endpoints."""

    def __init__(self, async_api: AsyncAstAPI) -> None:
        self._async = async_api

    def get_document_ast(
        self,
        pdf_data: bytes,
        *,
        page_range_start: int | None = None,
        page_range_end: int | None = None,
        token_budget: int | None = None,
    ) -> AstDocument:
        """
        Build a Semantic AST from PDF bytes (synchronous).

        See AsyncAstAPI.get_document_ast for full documentation.
        """
        return run_sync(
            self._async.get_document_ast(
                pdf_data,
                page_range_start=page_range_start,
                page_range_end=page_range_end,
                token_budget=token_budget,
            )
        )

    def extract_cited_text(
        self,
        pdf_data: bytes,
        *,
        page_index: int | None = None,
        headings_only: bool = False,
    ) -> list[CitedTextBlock]:
        """
        Extract text blocks with citation anchors (synchronous).

        See AsyncAstAPI.extract_cited_text for full documentation.
        """
        return run_sync(
            self._async.extract_cited_text(
                pdf_data,
                page_index=page_index,
                headings_only=headings_only,
            )
        )

    def get_ast_node(
        self,
        pdf_data: bytes,
        node_id: str,
    ) -> GetAstNodeResponse:
        """
        Retrieve a single AST node by its node ID (synchronous).

        See AsyncAstAPI.get_ast_node for full documentation.
        """
        return run_sync(self._async.get_ast_node(pdf_data, node_id))

    def search_ast_nodes(
        self,
        pdf_data: bytes,
        *,
        node_type: str | None = None,
        page_index: int | None = None,
        text_query: str | None = None,
        max_results: int = 100,
    ) -> SearchAstNodesResponse:
        """
        Search AST nodes by type, page, or text content (synchronous).

        See AsyncAstAPI.search_ast_nodes for full documentation.
        """
        return run_sync(
            self._async.search_ast_nodes(
                pdf_data,
                node_type=node_type,
                page_index=page_index,
                text_query=text_query,
                max_results=max_results,
            )
        )

    def extract_cited_tables(
        self,
        pdf_data: bytes,
        *,
        page_range: dict[str, int] | None = None,
    ) -> ExtractCitedTablesResponse:
        """
        Extract all tables from a PDF with citation anchors (synchronous).

        See AsyncAstAPI.extract_cited_tables for full documentation.
        """
        return run_sync(
            self._async.extract_cited_tables(
                pdf_data,
                page_range=page_range,
            )
        )

    def get_ast_diff(
        self,
        original_pdf_data: bytes,
        modified_pdf_data: bytes,
    ) -> GetAstDiffResponse:
        """
        Compare two PDFs and return structural AST differences (synchronous).

        See AsyncAstAPI.get_ast_diff for full documentation.
        """
        return run_sync(self._async.get_ast_diff(original_pdf_data, modified_pdf_data))
