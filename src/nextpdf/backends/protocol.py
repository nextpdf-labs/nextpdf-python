"""Backend protocol for PDF extraction engines."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from nextpdf.models.ast import (
        AstDocument,
        CitedTextBlock,
        ExtractCitedTablesResponse,
        GetAstDiffResponse,
        GetAstNodeResponse,
        SearchAstNodesResponse,
    )


@runtime_checkable
class PdfBackend(Protocol):
    """Canonical async interface for PDF extraction backends."""

    async def get_document_ast(
        self,
        pdf_data: bytes,
        *,
        page_range_start: int | None = None,
        page_range_end: int | None = None,
        token_budget: int | None = None,
    ) -> AstDocument: ...

    async def extract_cited_text(
        self,
        pdf_data: bytes,
        *,
        page_index: int | None = None,
        headings_only: bool = False,
    ) -> list[CitedTextBlock]: ...

    async def extract_cited_tables(
        self,
        pdf_data: bytes,
        *,
        page_range: dict[str, int] | None = None,
    ) -> ExtractCitedTablesResponse: ...

    async def search_ast_nodes(
        self,
        pdf_data: bytes,
        *,
        node_type: str | None = None,
        page_index: int | None = None,
        text_query: str | None = None,
        max_results: int = 100,
    ) -> SearchAstNodesResponse: ...

    async def get_ast_node(
        self,
        pdf_data: bytes,
        node_id: str,
    ) -> GetAstNodeResponse: ...

    async def get_ast_diff(
        self,
        original_pdf_data: bytes,
        modified_pdf_data: bytes,
    ) -> GetAstDiffResponse: ...
