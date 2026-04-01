"""Tests for the local PDF extraction backend (pypdf)."""

from __future__ import annotations

import io

import pytest
from pypdf import PdfWriter

from nextpdf.backends.local import LocalBackend
from nextpdf.models.ast import (
    AstDocument,
    CitedTextBlock,
    ExtractCitedTablesResponse,
    GetAstDiffResponse,
    GetAstNodeResponse,
    NodeType,
    SearchAstNodesResponse,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _create_minimal_pdf() -> bytes:
    """Create a minimal valid (but empty) PDF using pypdf."""
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _create_multi_page_pdf(page_count: int = 3) -> bytes:
    """Create a multi-page blank PDF."""
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


@pytest.fixture()
def minimal_pdf() -> bytes:
    return _create_minimal_pdf()


@pytest.fixture()
def multi_page_pdf() -> bytes:
    return _create_multi_page_pdf(5)


@pytest.fixture()
def backend() -> LocalBackend:
    return LocalBackend()


@pytest.fixture()
def strict_backend() -> LocalBackend:
    return LocalBackend(max_pages=3, max_file_size=50_000)


# ---------------------------------------------------------------------------
# get_document_ast
# ---------------------------------------------------------------------------


class TestGetDocumentAst:
    """Test the get_document_ast method."""

    async def test_minimal_pdf_produces_valid_ast(
        self,
        backend: LocalBackend,
        minimal_pdf: bytes,
    ) -> None:
        doc = await backend.get_document_ast(minimal_pdf)

        assert isinstance(doc, AstDocument)
        assert doc.schema_version == "1.0"
        assert doc.page_count == 1
        assert doc.root.type == NodeType.DOCUMENT
        assert len(doc.source_hash) == 64  # sha256 hex

    async def test_multi_page_pdf_page_count(
        self,
        backend: LocalBackend,
        multi_page_pdf: bytes,
    ) -> None:
        doc = await backend.get_document_ast(multi_page_pdf)
        assert doc.page_count == 5

    async def test_source_hash_is_deterministic(
        self,
        backend: LocalBackend,
        minimal_pdf: bytes,
    ) -> None:
        doc1 = await backend.get_document_ast(minimal_pdf)
        doc2 = await backend.get_document_ast(minimal_pdf)
        assert doc1.source_hash == doc2.source_hash

    async def test_untagged_pdf_uses_heuristic(
        self,
        backend: LocalBackend,
        minimal_pdf: bytes,
    ) -> None:
        doc = await backend.get_document_ast(minimal_pdf)
        # Blank pages produce heuristic sections with no paragraph children
        assert doc.root.type == NodeType.DOCUMENT
        assert doc.root.attributes.get("heuristic") is True

    async def test_page_range_limits_sections(
        self,
        backend: LocalBackend,
        multi_page_pdf: bytes,
    ) -> None:
        doc = await backend.get_document_ast(
            multi_page_pdf,
            page_range_start=1,
            page_range_end=2,
        )
        # For heuristic mode, sections correspond to pages in range
        sections = [c for c in doc.root.children if c.type == NodeType.SECTION]
        # Should only have sections for pages 1 and 2
        page_indices = {s.page_index for s in sections}
        assert page_indices == {1, 2}


# ---------------------------------------------------------------------------
# Resource protection
# ---------------------------------------------------------------------------


class TestResourceProtection:
    """Test file size and page count limits."""

    async def test_oversized_file_rejected(
        self,
        strict_backend: LocalBackend,
    ) -> None:
        big_data = b"%PDF-1.4 " + b"x" * 60_000
        with pytest.raises(ValueError, match="exceeds maximum"):
            await strict_backend.get_document_ast(big_data)

    async def test_too_many_pages_rejected(
        self,
        strict_backend: LocalBackend,
    ) -> None:
        pdf_data = _create_multi_page_pdf(5)
        with pytest.raises(ValueError, match="exceeding maximum"):
            await strict_backend.get_document_ast(pdf_data)

    async def test_empty_bytes_rejected(
        self,
        backend: LocalBackend,
    ) -> None:
        with pytest.raises(ValueError, match="Cannot open PDF"):
            await backend.get_document_ast(b"")

    async def test_corrupt_bytes_rejected(
        self,
        backend: LocalBackend,
    ) -> None:
        with pytest.raises(ValueError, match="Cannot open PDF"):
            await backend.get_document_ast(b"not a pdf at all")


# ---------------------------------------------------------------------------
# extract_cited_text
# ---------------------------------------------------------------------------


class TestExtractCitedText:
    """Test text extraction with citations."""

    async def test_returns_list_of_cited_blocks(
        self,
        backend: LocalBackend,
        minimal_pdf: bytes,
    ) -> None:
        blocks = await backend.extract_cited_text(minimal_pdf)
        assert isinstance(blocks, list)
        # Blank PDF may have zero text blocks
        for block in blocks:
            assert isinstance(block, CitedTextBlock)
            assert block.citation.confidence >= 0.0
            assert block.citation.confidence <= 1.0

    async def test_heuristic_confidence_is_half(
        self,
        backend: LocalBackend,
        minimal_pdf: bytes,
    ) -> None:
        blocks = await backend.extract_cited_text(minimal_pdf)
        for block in blocks:
            assert block.citation.confidence == 0.5

    async def test_page_index_filter(
        self,
        backend: LocalBackend,
        multi_page_pdf: bytes,
    ) -> None:
        blocks = await backend.extract_cited_text(multi_page_pdf, page_index=0)
        for block in blocks:
            assert block.citation.page_index == 0

    async def test_headings_only_filter(
        self,
        backend: LocalBackend,
        minimal_pdf: bytes,
    ) -> None:
        blocks = await backend.extract_cited_text(minimal_pdf, headings_only=True)
        for block in blocks:
            assert block.node_type == "heading"


# ---------------------------------------------------------------------------
# extract_cited_tables
# ---------------------------------------------------------------------------


class TestExtractCitedTables:
    """Test table extraction."""

    async def test_heuristic_returns_empty_tables(
        self,
        backend: LocalBackend,
        minimal_pdf: bytes,
    ) -> None:
        resp = await backend.extract_cited_tables(minimal_pdf)
        assert isinstance(resp, ExtractCitedTablesResponse)
        assert resp.table_count == 0
        assert resp.tables == []


# ---------------------------------------------------------------------------
# search_ast_nodes
# ---------------------------------------------------------------------------


class TestSearchAstNodes:
    """Test AST node search."""

    async def test_search_returns_response(
        self,
        backend: LocalBackend,
        minimal_pdf: bytes,
    ) -> None:
        resp = await backend.search_ast_nodes(minimal_pdf)
        assert isinstance(resp, SearchAstNodesResponse)
        assert resp.total_matches >= 1  # at least the document root

    async def test_search_by_type(
        self,
        backend: LocalBackend,
        minimal_pdf: bytes,
    ) -> None:
        resp = await backend.search_ast_nodes(minimal_pdf, node_type="document")
        for node in resp.nodes:
            assert node.type == NodeType.DOCUMENT

    async def test_search_max_results(
        self,
        backend: LocalBackend,
        multi_page_pdf: bytes,
    ) -> None:
        resp = await backend.search_ast_nodes(multi_page_pdf, max_results=2)
        assert len(resp.nodes) <= 2


# ---------------------------------------------------------------------------
# get_ast_node
# ---------------------------------------------------------------------------


class TestGetAstNode:
    """Test single node retrieval."""

    async def test_find_root_node(
        self,
        backend: LocalBackend,
        minimal_pdf: bytes,
    ) -> None:
        doc = await backend.get_document_ast(minimal_pdf)
        resp = await backend.get_ast_node(minimal_pdf, doc.root.id)
        assert isinstance(resp, GetAstNodeResponse)
        assert resp.node.id == doc.root.id

    async def test_missing_node_raises(
        self,
        backend: LocalBackend,
        minimal_pdf: bytes,
    ) -> None:
        with pytest.raises(ValueError, match="Node not found"):
            await backend.get_ast_node(minimal_pdf, "ast:000000:0:999999")


# ---------------------------------------------------------------------------
# get_ast_diff
# ---------------------------------------------------------------------------


class TestGetAstDiff:
    """Test AST diff between two PDFs."""

    async def test_identical_pdfs_produce_empty_diff(
        self,
        backend: LocalBackend,
        minimal_pdf: bytes,
    ) -> None:
        resp = await backend.get_ast_diff(minimal_pdf, minimal_pdf)
        assert isinstance(resp, GetAstDiffResponse)
        assert resp.summary.added_node_count == 0
        assert resp.summary.removed_node_count == 0

    async def test_different_pdfs_produce_diff(
        self,
        backend: LocalBackend,
    ) -> None:
        pdf_a = _create_minimal_pdf()
        pdf_b = _create_multi_page_pdf(3)
        resp = await backend.get_ast_diff(pdf_a, pdf_b)
        assert isinstance(resp, GetAstDiffResponse)
        # Different page counts should produce some differences
        assert resp.original_page_count == 1
        assert resp.modified_page_count == 3


# ---------------------------------------------------------------------------
# Protocol compliance
# ---------------------------------------------------------------------------


class TestProtocolCompliance:
    """Verify LocalBackend satisfies the PdfBackend protocol."""

    def test_is_instance_of_protocol(self) -> None:
        from nextpdf.backends.protocol import PdfBackend

        backend = LocalBackend()
        assert isinstance(backend, PdfBackend)
