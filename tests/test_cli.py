"""CLI smoke tests using click.testing.CliRunner."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from nextpdf._version import __version__
from nextpdf.cli import main
from nextpdf.models.ast import (
    AstDocument,
    AstNode,
    BoundingBox,
    CitationAnchor,
    CitedTableBlock,
    CitedTableCell,
    CitedTextBlock,
    ExtractCitedTablesResponse,
    NodeType,
)


@pytest.fixture()
def runner() -> CliRunner:
    """Create a CliRunner instance."""
    return CliRunner()


@pytest.fixture()
def sample_pdf_file(tmp_path: object) -> str:
    """Write a minimal fake PDF to a temporary file and return its path."""
    from pathlib import Path

    p = Path(str(tmp_path)) / "test.pdf"
    p.write_bytes(b"%PDF-1.4 fake content for testing")
    return str(p)


@pytest.fixture()
def sample_cited_blocks() -> list[CitedTextBlock]:
    """Build sample CitedTextBlock list for mocking."""
    return [
        CitedTextBlock(
            text="Introduction to the document.",
            citation=CitationAnchor(
                node_id="ast:abc123:0:1",
                page_index=0,
                bbox=BoundingBox(x=0.1, y=0.2, width=0.8, height=0.05),
                confidence=0.95,
            ),
            node_type="heading",
        ),
        CitedTextBlock(
            text="This is the first paragraph of content.",
            citation=CitationAnchor(
                node_id="ast:abc123:0:2",
                page_index=0,
                bbox=BoundingBox(x=0.1, y=0.3, width=0.8, height=0.1),
                confidence=0.88,
            ),
            node_type="paragraph",
        ),
    ]


@pytest.fixture()
def sample_ast_document() -> AstDocument:
    """Build a sample AstDocument for mocking."""
    return AstDocument.model_validate(
        {
            "schemaVersion": "1.0",
            "sourceHash": "deadbeef1234",
            "pageCount": 3,
            "root": {
                "id": "node-root",
                "type": "document",
                "page_index": 0,
                "text_content": "Root content",
                "attributes": {},
                "children": [
                    {
                        "id": "node-h1",
                        "type": "heading",
                        "page_index": 0,
                        "text_content": "Chapter 1",
                        "attributes": {"level": 1},
                        "children": [],
                    },
                ],
            },
        }
    )


@pytest.fixture()
def sample_tables_response() -> ExtractCitedTablesResponse:
    """Build a sample ExtractCitedTablesResponse for mocking."""
    return ExtractCitedTablesResponse(
        tables=[
            CitedTableBlock(
                table_node_id="tbl-1",
                page_index=0,
                citation_anchor=None,
                row_count=2,
                col_count=2,
                rows=[
                    [
                        CitedTableCell(row=0, col=0, text="A1", bbox=None, confidence=0.9),
                        CitedTableCell(row=0, col=1, text="B1", bbox=None, confidence=0.9),
                    ],
                    [
                        CitedTableCell(row=1, col=0, text="A2", bbox=None, confidence=0.9),
                        CitedTableCell(row=1, col=1, text="B2", bbox=None, confidence=0.9),
                    ],
                ],
            ),
        ],
        table_count=1,
        pages_processed=1,
    )


# ---------------------------------------------------------------------------
# Basic CLI tests
# ---------------------------------------------------------------------------


class TestHelp:
    """Test help output for all commands."""

    def test_main_help(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "NextPDF CLI" in result.output

    def test_extract_help(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["extract", "--help"])
        assert result.exit_code == 0
        assert "Extract structured content" in result.output

    def test_extract_text_help(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["extract", "text", "--help"])
        assert result.exit_code == 0
        assert "PDF_PATH" in result.output

    def test_extract_tables_help(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["extract", "tables", "--help"])
        assert result.exit_code == 0
        assert "PDF_PATH" in result.output

    def test_ast_help(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["ast", "--help"])
        assert result.exit_code == 0
        assert "semantic AST" in result.output

    def test_info_help(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["info", "--help"])
        assert result.exit_code == 0
        assert "document info" in result.output.lower()


class TestVersion:
    """Test version command."""

    def test_version_prints_version(self, runner: CliRunner) -> None:
        result = runner.invoke(main, ["version"])
        assert result.exit_code == 0
        assert __version__ in result.output

    def test_version_no_credentials_needed(self, runner: CliRunner) -> None:
        """Version should work without --base-url and --api-key."""
        result = runner.invoke(
            main,
            ["version"],
            env={
                "NEXTPDF_BASE_URL": "",
                "NEXTPDF_API_KEY": "",
            },
        )
        assert result.exit_code == 0
        assert "nextpdf" in result.output


class TestExtractTextMissing:
    """Test extract text with missing arguments."""

    def test_missing_pdf_path(self, runner: CliRunner) -> None:
        result = runner.invoke(
            main,
            [
                "--base-url",
                "http://localhost:8080",
                "--api-key",
                "test-key",
                "extract",
                "text",
            ],
        )
        assert result.exit_code != 0

    def test_file_not_found(self, runner: CliRunner) -> None:
        result = runner.invoke(
            main,
            [
                "--base-url",
                "http://localhost:8080",
                "--api-key",
                "test-key",
                "extract",
                "text",
                "/nonexistent/path/file.pdf",
            ],
        )
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Mocked SDK call tests
# ---------------------------------------------------------------------------


class TestExtractText:
    """Test extract text with mocked SDK calls."""

    def test_json_output(
        self,
        runner: CliRunner,
        sample_pdf_file: str,
        sample_cited_blocks: list[CitedTextBlock],
    ) -> None:
        with patch("nextpdf.cli._build_client") as mock_build:
            mock_client = MagicMock()
            mock_client.ast.extract_cited_text.return_value = sample_cited_blocks
            mock_build.return_value = mock_client

            result = runner.invoke(
                main,
                [
                    "--base-url",
                    "http://localhost:8080",
                    "--api-key",
                    "test-key",
                    "extract",
                    "text",
                    sample_pdf_file,
                ],
            )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["text"] == "Introduction to the document."

    def test_markdown_output(
        self,
        runner: CliRunner,
        sample_pdf_file: str,
        sample_cited_blocks: list[CitedTextBlock],
    ) -> None:
        with patch("nextpdf.cli._build_client") as mock_build:
            mock_client = MagicMock()
            mock_client.ast.extract_cited_text.return_value = sample_cited_blocks
            mock_build.return_value = mock_client

            result = runner.invoke(
                main,
                [
                    "--base-url",
                    "http://localhost:8080",
                    "--api-key",
                    "test-key",
                    "extract",
                    "text",
                    sample_pdf_file,
                    "--format",
                    "markdown",
                ],
            )

        assert result.exit_code == 0
        assert "[p0]" in result.output
        assert "Introduction to the document." in result.output
        assert "cite:" in result.output

    def test_plain_output(
        self,
        runner: CliRunner,
        sample_pdf_file: str,
        sample_cited_blocks: list[CitedTextBlock],
    ) -> None:
        with patch("nextpdf.cli._build_client") as mock_build:
            mock_client = MagicMock()
            mock_client.ast.extract_cited_text.return_value = sample_cited_blocks
            mock_build.return_value = mock_client

            result = runner.invoke(
                main,
                [
                    "--base-url",
                    "http://localhost:8080",
                    "--api-key",
                    "test-key",
                    "extract",
                    "text",
                    sample_pdf_file,
                    "--format",
                    "plain",
                ],
            )

        assert result.exit_code == 0
        lines = result.output.strip().split("\n")
        assert len(lines) == 2
        assert lines[0] == "Introduction to the document."
        assert lines[1] == "This is the first paragraph of content."


class TestExtractTables:
    """Test extract tables with mocked SDK calls."""

    def test_json_output(
        self,
        runner: CliRunner,
        sample_pdf_file: str,
        sample_tables_response: ExtractCitedTablesResponse,
    ) -> None:
        with patch("nextpdf.cli._build_client") as mock_build:
            mock_client = MagicMock()
            mock_client.ast.extract_cited_tables.return_value = sample_tables_response
            mock_build.return_value = mock_client

            result = runner.invoke(
                main,
                [
                    "--base-url",
                    "http://localhost:8080",
                    "--api-key",
                    "test-key",
                    "extract",
                    "tables",
                    sample_pdf_file,
                ],
            )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["table_count"] == 1
        assert len(data["tables"]) == 1

    def test_csv_output(
        self,
        runner: CliRunner,
        sample_pdf_file: str,
        sample_tables_response: ExtractCitedTablesResponse,
    ) -> None:
        with patch("nextpdf.cli._build_client") as mock_build:
            mock_client = MagicMock()
            mock_client.ast.extract_cited_tables.return_value = sample_tables_response
            mock_build.return_value = mock_client

            result = runner.invoke(
                main,
                [
                    "--base-url",
                    "http://localhost:8080",
                    "--api-key",
                    "test-key",
                    "extract",
                    "tables",
                    sample_pdf_file,
                    "--format",
                    "csv",
                ],
            )

        assert result.exit_code == 0
        assert "A1" in result.output
        assert "B2" in result.output


class TestAstCommand:
    """Test ast command with mocked SDK calls."""

    def test_ast_json_output(
        self,
        runner: CliRunner,
        sample_pdf_file: str,
        sample_ast_document: AstDocument,
    ) -> None:
        with patch("nextpdf.cli._build_client") as mock_build:
            mock_client = MagicMock()
            mock_client.ast.get_document_ast.return_value = sample_ast_document
            mock_build.return_value = mock_client

            result = runner.invoke(
                main,
                [
                    "--base-url",
                    "http://localhost:8080",
                    "--api-key",
                    "test-key",
                    "ast",
                    sample_pdf_file,
                ],
            )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["page_count"] == 3
        assert data["root"]["type"] == "document"


class TestInfoCommand:
    """Test info command with mocked SDK calls."""

    def test_info_output(
        self,
        runner: CliRunner,
        sample_pdf_file: str,
        sample_ast_document: AstDocument,
    ) -> None:
        with patch("nextpdf.cli._build_client") as mock_build:
            mock_client = MagicMock()
            mock_client.ast.get_document_ast.return_value = sample_ast_document
            mock_build.return_value = mock_client

            result = runner.invoke(
                main,
                [
                    "--base-url",
                    "http://localhost:8080",
                    "--api-key",
                    "test-key",
                    "info",
                    sample_pdf_file,
                ],
            )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["page_count"] == 3
        assert data["source_hash"] == "deadbeef1234"
        assert data["root_node_type"] == "document"
        assert data["root_children_count"] == 1


class TestOutputFile:
    """Test --output flag writes to file."""

    def test_output_to_file(
        self,
        runner: CliRunner,
        sample_pdf_file: str,
        sample_cited_blocks: list[CitedTextBlock],
        tmp_path: object,
    ) -> None:
        from pathlib import Path

        output_file = str(Path(str(tmp_path)) / "output.json")

        with patch("nextpdf.cli._build_client") as mock_build:
            mock_client = MagicMock()
            mock_client.ast.extract_cited_text.return_value = sample_cited_blocks
            mock_build.return_value = mock_client

            result = runner.invoke(
                main,
                [
                    "--base-url",
                    "http://localhost:8080",
                    "--api-key",
                    "test-key",
                    "--output",
                    output_file,
                    "extract",
                    "text",
                    sample_pdf_file,
                ],
            )

        assert result.exit_code == 0
        written = Path(output_file).read_text(encoding="utf-8")
        data = json.loads(written)
        assert len(data) == 2


class TestErrorHandling:
    """Test that SDK errors are handled gracefully."""

    def test_sdk_error_shows_message(
        self,
        runner: CliRunner,
        sample_pdf_file: str,
    ) -> None:
        from nextpdf.models.errors import NextPDFAPIError

        with patch("nextpdf.cli._build_client") as mock_build:
            mock_client = MagicMock()
            mock_client.ast.extract_cited_text.side_effect = NextPDFAPIError(
                "Server unavailable",
                status_code=503,
            )
            mock_build.return_value = mock_client

            result = runner.invoke(
                main,
                [
                    "--base-url",
                    "http://localhost:8080",
                    "--api-key",
                    "test-key",
                    "extract",
                    "text",
                    sample_pdf_file,
                ],
            )

        assert result.exit_code != 0
        assert "Server unavailable" in result.stderr
