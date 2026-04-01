"""Tests for extract_cited_tables and get_ast_diff (Phase 2a)."""

from __future__ import annotations

import base64
import json

import httpx
import pytest
import respx
from pydantic import ValidationError

from nextpdf import AsyncNextPDF, NextPDF
from nextpdf.models.ast import (
    AstDiffEntry,
    AstDiffSummary,
    CitedTableBlock,
    CitedTableCell,
    ExtractCitedTablesResponse,
    GetAstDiffResponse,
)

BASE_URL = "https://api.nextpdf.test"
API_KEY = "test-key-phase2a"

PDF_BYTES = b"%PDF-1.4 fake content"
PDF_BYTES_MOD = b"%PDF-1.4 modified content"

EXTRACT_CITED_TABLES_RESPONSE = {
    "tables": [
        {
            "table_node_id": "ast:abc123:0:5",
            "page_index": 0,
            "citation_anchor": {
                "node_id": "ast:abc123:0:5",
                "page_index": 0,
                "bbox": {"x": 0.1, "y": 0.2, "width": 0.8, "height": 0.3},
                "confidence": 0.97,
                "content_hash": None,
            },
            "row_count": 2,
            "col_count": 3,
            "rows": [
                [
                    {
                        "row": 0,
                        "col": 0,
                        "row_span": 1,
                        "col_span": 1,
                        "text": "Header A",
                        "bbox": None,
                        "confidence": 0.99,
                    },
                    {
                        "row": 0,
                        "col": 1,
                        "row_span": 1,
                        "col_span": 1,
                        "text": "Header B",
                        "bbox": None,
                        "confidence": 0.99,
                    },
                    {
                        "row": 0,
                        "col": 2,
                        "row_span": 1,
                        "col_span": 1,
                        "text": "Header C",
                        "bbox": None,
                        "confidence": 0.98,
                    },
                ],
                [
                    {
                        "row": 1,
                        "col": 0,
                        "row_span": 1,
                        "col_span": 1,
                        "text": "Val 1",
                        "bbox": None,
                        "confidence": 0.95,
                    },
                    {
                        "row": 1,
                        "col": 1,
                        "row_span": 1,
                        "col_span": 1,
                        "text": "Val 2",
                        "bbox": None,
                        "confidence": 0.95,
                    },
                    {
                        "row": 1,
                        "col": 2,
                        "row_span": 1,
                        "col_span": 1,
                        "text": None,
                        "bbox": None,
                        "confidence": 0.0,
                    },
                ],
            ],
        }
    ],
    "table_count": 1,
    "_meta": {"etag": None, "pages_processed": 5},
}

EXTRACT_CITED_TABLES_EMPTY_RESPONSE = {
    "tables": [],
    "table_count": 0,
}

GET_AST_DIFF_RESPONSE = {
    "original_page_count": 4,
    "modified_page_count": 5,
    "summary": {
        "added_node_count": 3,
        "removed_node_count": 1,
        "changed_node_count": 2,
    },
    "diff": [
        {
            "type": "added",
            "node_id": "ast:xyz789:4:1",
            "node_type": "paragraph",
            "page_index": 4,
            "text_preview": "New paragraph added on page 5.",
        },
        {
            "type": "removed",
            "node_id": "ast:abc123:1:3",
            "node_type": "heading",
            "page_index": 1,
            "text_preview": "Old section removed.",
        },
        {
            "type": "changed",
            "node_id": "ast:abc123:0:2",
            "node_type": "table",
            "page_index": 0,
            "text_preview": None,
        },
    ],
    "_meta": {"etag": None, "pages_processed": 9},
}

GET_AST_DIFF_IDENTICAL_RESPONSE = {
    "original_page_count": 2,
    "modified_page_count": 2,
    "summary": {
        "added_node_count": 0,
        "removed_node_count": 0,
        "changed_node_count": 0,
    },
    "diff": [],
}


class TestExtractCitedTablesAsync:
    @respx.mock
    @pytest.mark.asyncio
    async def test_extract_cited_tables_success(self) -> None:
        """extract_cited_tables parses tables, cells and citation anchors correctly."""
        respx.post(f"{BASE_URL}/v1/tools/extract_cited_tables").mock(
            return_value=httpx.Response(200, json=EXTRACT_CITED_TABLES_RESPONSE)
        )

        async with AsyncNextPDF(base_url=BASE_URL, api_key=API_KEY) as client:
            result = await client.ast.extract_cited_tables(PDF_BYTES)

        assert result.table_count == 1
        assert len(result.tables) == 1
        table = result.tables[0]
        assert table.table_node_id == "ast:abc123:0:5"
        assert table.page_index == 0
        assert table.row_count == 2
        assert table.col_count == 3
        assert table.citation_anchor is not None
        assert table.citation_anchor.confidence == 0.97
        assert len(table.rows) == 2
        assert table.rows[0][0].text == "Header A"
        assert table.rows[1][2].text is None
        assert result.pages_processed == 5

    @respx.mock
    @pytest.mark.asyncio
    async def test_extract_cited_tables_empty(self) -> None:
        """extract_cited_tables returns empty list when no tables found."""
        respx.post(f"{BASE_URL}/v1/tools/extract_cited_tables").mock(
            return_value=httpx.Response(200, json=EXTRACT_CITED_TABLES_EMPTY_RESPONSE)
        )

        async with AsyncNextPDF(base_url=BASE_URL, api_key=API_KEY) as client:
            result = await client.ast.extract_cited_tables(PDF_BYTES)

        assert result.table_count == 0
        assert result.tables == []
        assert result.pages_processed is None

    @respx.mock
    @pytest.mark.asyncio
    async def test_extract_cited_tables_sends_base64_pdf(self) -> None:
        """extract_cited_tables encodes the PDF as base64 in the request body."""
        route = respx.post(f"{BASE_URL}/v1/tools/extract_cited_tables").mock(
            return_value=httpx.Response(200, json=EXTRACT_CITED_TABLES_EMPTY_RESPONSE)
        )

        async with AsyncNextPDF(base_url=BASE_URL, api_key=API_KEY) as client:
            await client.ast.extract_cited_tables(PDF_BYTES)

        assert route.called
        body = json.loads(route.calls.last.request.content)
        assert body["pdf_data"] == base64.b64encode(PDF_BYTES).decode("ascii")
        assert "page_range" not in body

    @respx.mock
    @pytest.mark.asyncio
    async def test_extract_cited_tables_with_page_range(self) -> None:
        """extract_cited_tables sends page_range when provided."""
        route = respx.post(f"{BASE_URL}/v1/tools/extract_cited_tables").mock(
            return_value=httpx.Response(200, json=EXTRACT_CITED_TABLES_EMPTY_RESPONSE)
        )

        async with AsyncNextPDF(base_url=BASE_URL, api_key=API_KEY) as client:
            await client.ast.extract_cited_tables(
                PDF_BYTES,
                page_range={"start": 0, "end": 2},
            )

        body = json.loads(route.calls.last.request.content)
        assert body["page_range"] == {"start": 0, "end": 2}

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_extract_cited_tables_success(self) -> None:
        """Async extract_cited_tables returns ExtractCitedTablesResponse instance."""
        respx.post(f"{BASE_URL}/v1/tools/extract_cited_tables").mock(
            return_value=httpx.Response(200, json=EXTRACT_CITED_TABLES_RESPONSE)
        )

        async with AsyncNextPDF(base_url=BASE_URL, api_key=API_KEY) as client:
            result = await client.ast.extract_cited_tables(PDF_BYTES)

        assert isinstance(result, ExtractCitedTablesResponse)


class TestGetAstDiffAsync:
    @respx.mock
    @pytest.mark.asyncio
    async def test_get_ast_diff_success(self) -> None:
        """get_ast_diff parses summary, diff entries and page counts correctly."""
        respx.post(f"{BASE_URL}/v1/tools/get_ast_diff").mock(
            return_value=httpx.Response(200, json=GET_AST_DIFF_RESPONSE)
        )

        async with AsyncNextPDF(base_url=BASE_URL, api_key=API_KEY) as client:
            result = await client.ast.get_ast_diff(PDF_BYTES, PDF_BYTES_MOD)

        assert result.original_page_count == 4
        assert result.modified_page_count == 5
        assert result.summary.added_node_count == 3
        assert result.summary.removed_node_count == 1
        assert result.summary.changed_node_count == 2
        assert len(result.diff) == 3
        assert result.diff[0].type == "added"
        assert result.diff[0].node_id == "ast:xyz789:4:1"
        assert result.diff[1].type == "removed"
        assert result.diff[2].type == "changed"
        assert result.diff[2].text_preview is None
        assert result.pages_processed == 9

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_ast_diff_identical_pdfs_returns_zero_diff(self) -> None:
        """get_ast_diff returns zero counts and empty diff for identical PDFs."""
        respx.post(f"{BASE_URL}/v1/tools/get_ast_diff").mock(
            return_value=httpx.Response(200, json=GET_AST_DIFF_IDENTICAL_RESPONSE)
        )

        async with AsyncNextPDF(base_url=BASE_URL, api_key=API_KEY) as client:
            result = await client.ast.get_ast_diff(PDF_BYTES, PDF_BYTES)

        assert result.summary.added_node_count == 0
        assert result.summary.removed_node_count == 0
        assert result.summary.changed_node_count == 0
        assert result.diff == []
        assert result.pages_processed is None

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_ast_diff_sends_both_pdfs(self) -> None:
        """get_ast_diff encodes both PDFs as base64 in the request body."""
        route = respx.post(f"{BASE_URL}/v1/tools/get_ast_diff").mock(
            return_value=httpx.Response(200, json=GET_AST_DIFF_IDENTICAL_RESPONSE)
        )

        async with AsyncNextPDF(base_url=BASE_URL, api_key=API_KEY) as client:
            await client.ast.get_ast_diff(PDF_BYTES, PDF_BYTES_MOD)

        assert route.called
        body = json.loads(route.calls.last.request.content)
        assert body["original_pdf_data"] == base64.b64encode(PDF_BYTES).decode("ascii")
        assert body["modified_pdf_data"] == base64.b64encode(PDF_BYTES_MOD).decode("ascii")

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_get_ast_diff_success(self) -> None:
        """Async get_ast_diff returns GetAstDiffResponse instance."""
        respx.post(f"{BASE_URL}/v1/tools/get_ast_diff").mock(
            return_value=httpx.Response(200, json=GET_AST_DIFF_RESPONSE)
        )

        async with AsyncNextPDF(base_url=BASE_URL, api_key=API_KEY) as client:
            result = await client.ast.get_ast_diff(PDF_BYTES, PDF_BYTES_MOD)

        assert isinstance(result, GetAstDiffResponse)


class TestSyncDelegation:
    @respx.mock
    def test_sync_extract_cited_tables_delegates(self) -> None:
        """Sync extract_cited_tables delegates to async and returns correct type."""
        respx.post(f"{BASE_URL}/v1/tools/extract_cited_tables").mock(
            return_value=httpx.Response(200, json=EXTRACT_CITED_TABLES_RESPONSE)
        )

        client = NextPDF(base_url=BASE_URL, api_key=API_KEY)
        result = client.ast.extract_cited_tables(PDF_BYTES)

        assert isinstance(result, ExtractCitedTablesResponse)
        assert result.table_count == 1

    @respx.mock
    def test_sync_get_ast_diff_delegates(self) -> None:
        """Sync get_ast_diff delegates to async and returns correct type."""
        respx.post(f"{BASE_URL}/v1/tools/get_ast_diff").mock(
            return_value=httpx.Response(200, json=GET_AST_DIFF_RESPONSE)
        )

        client = NextPDF(base_url=BASE_URL, api_key=API_KEY)
        result = client.ast.get_ast_diff(PDF_BYTES, PDF_BYTES_MOD)

        assert isinstance(result, GetAstDiffResponse)
        assert result.original_page_count == 4


class TestModelFrozen:
    def test_cited_table_cell_model_frozen(self) -> None:
        """CitedTableCell is immutable (frozen=True)."""
        cell = CitedTableCell(
            row=0,
            col=0,
            text="value",
            bbox=None,
            confidence=0.9,
        )
        with pytest.raises(ValidationError):
            cell.text = "mutated"  # type: ignore[misc]

    def test_cited_table_block_model_frozen(self) -> None:
        """CitedTableBlock is immutable (frozen=True)."""
        block = CitedTableBlock(
            table_node_id="ast:abc:0:1",
            page_index=0,
            citation_anchor=None,
            row_count=0,
            col_count=0,
            rows=[],
        )
        with pytest.raises(ValidationError):
            block.row_count = 5  # type: ignore[misc]

    def test_extract_cited_tables_response_frozen(self) -> None:
        """ExtractCitedTablesResponse is immutable (frozen=True)."""
        resp = ExtractCitedTablesResponse(tables=[], table_count=0)
        with pytest.raises(ValidationError):
            resp.table_count = 99  # type: ignore[misc]

    def test_ast_diff_entry_model_frozen(self) -> None:
        """AstDiffEntry is immutable (frozen=True)."""
        entry = AstDiffEntry(
            type="added",
            node_id="ast:abc:0:1",
            node_type="paragraph",
            page_index=0,
        )
        with pytest.raises(ValidationError):
            entry.type = "removed"  # type: ignore[misc]

    def test_get_ast_diff_response_frozen(self) -> None:
        """GetAstDiffResponse is immutable (frozen=True)."""
        summary = AstDiffSummary(
            added_node_count=0,
            removed_node_count=0,
            changed_node_count=0,
        )
        resp = GetAstDiffResponse(
            original_page_count=1,
            modified_page_count=1,
            summary=summary,
            diff=[],
        )
        with pytest.raises(ValidationError):
            resp.original_page_count = 99  # type: ignore[misc]
