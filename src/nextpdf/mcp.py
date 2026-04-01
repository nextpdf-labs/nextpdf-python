"""NextPDF MCP server for AI agent integration.

Exposes PDF extraction tools via the Model Context Protocol so that AI
agents (e.g. Claude Code) can call them as native tools.

Requires the ``mcp`` optional extra::

    pip install nextpdf[mcp]
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence

# ---------------------------------------------------------------------------
# Import guard — mcp is an optional dependency
# ---------------------------------------------------------------------------
try:
    from mcp.server import Server  # type: ignore[import-not-found]
    from mcp.server.stdio import stdio_server  # type: ignore[import-not-found]
    from mcp.types import TextContent, Tool  # type: ignore[import-not-found]
except ImportError:
    raise ImportError(
        "MCP server requires the 'mcp' extra. Install with: pip install nextpdf[mcp]"
    ) from None

from ._async_client import AsyncNextPDF
from ._version import __version__
from .models.errors import NextPDFError

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_MAX_PAGES: int = 50
_SERVER_NAME: str = "nextpdf"
_SERVER_VERSION: str = __version__
_DESC_PDF_PATH: str = "Absolute path to the PDF file on disk."
_DESC_MAX_PAGES: str = f"Maximum pages to process (default {_DEFAULT_MAX_PAGES})."


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------


def _tool_definitions() -> list[Tool]:
    """Return the full list of MCP tool definitions."""
    return [
        Tool(
            name="nextpdf_extract_text",
            description=(
                "Extract cited text blocks from a PDF file. Returns text with "
                "citation anchors (page index, bounding box, confidence score). "
                "Useful for retrieving document content with provenance."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "pdf_path": {
                        "type": "string",
                        "description": _DESC_PDF_PATH,
                    },
                    "max_pages": {
                        "type": "integer",
                        "description": (
                            f"Maximum pages to process (default {_DEFAULT_MAX_PAGES}). "
                            "Use to prevent context overflow on large documents."
                        ),
                        "default": _DEFAULT_MAX_PAGES,
                    },
                    "page_index": {
                        "type": "integer",
                        "description": "Extract only from this 0-based page index.",
                    },
                    "headings_only": {
                        "type": "boolean",
                        "description": "If true, extract only heading nodes.",
                        "default": False,
                    },
                },
                "required": ["pdf_path"],
            },
        ),
        Tool(
            name="nextpdf_extract_tables",
            description=(
                "Extract all tables from a PDF with citation anchors. Returns "
                "table structure with row/column data and cell-level bounding boxes."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "pdf_path": {
                        "type": "string",
                        "description": _DESC_PDF_PATH,
                    },
                    "max_pages": {
                        "type": "integer",
                        "description": (
                            f"Maximum pages to process (default {_DEFAULT_MAX_PAGES})."
                        ),
                        "default": _DEFAULT_MAX_PAGES,
                    },
                    "page_start": {
                        "type": "integer",
                        "description": "Start page index (0-based) for extraction.",
                    },
                    "page_end": {
                        "type": "integer",
                        "description": "End page index (0-based) for extraction.",
                    },
                },
                "required": ["pdf_path"],
            },
        ),
        Tool(
            name="nextpdf_get_ast",
            description=(
                "Get the full semantic AST (Abstract Syntax Tree) of a PDF. "
                "Returns a hierarchical tree of document nodes (headings, paragraphs, "
                "tables, lists, figures) with bounding boxes and text content."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "pdf_path": {
                        "type": "string",
                        "description": _DESC_PDF_PATH,
                    },
                    "max_pages": {
                        "type": "integer",
                        "description": (
                            f"Maximum pages to process (default {_DEFAULT_MAX_PAGES})."
                        ),
                        "default": _DEFAULT_MAX_PAGES,
                    },
                    "token_budget": {
                        "type": "integer",
                        "description": "Approximate token limit for the returned AST.",
                    },
                },
                "required": ["pdf_path"],
            },
        ),
        Tool(
            name="nextpdf_info",
            description=(
                "Get high-level document metadata: page count, schema version, "
                "source hash, estimated token count, and root structure summary."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "pdf_path": {
                        "type": "string",
                        "description": _DESC_PDF_PATH,
                    },
                },
                "required": ["pdf_path"],
            },
        ),
        Tool(
            name="nextpdf_health",
            description=(
                "Health and version check. Returns the SDK version and confirms "
                "connectivity to the NextPDF server."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="nextpdf_search",
            description=(
                "Search AST nodes by type, page index, or text content. "
                "Returns shallow node representations matching the query."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "pdf_path": {
                        "type": "string",
                        "description": _DESC_PDF_PATH,
                    },
                    "node_type": {
                        "type": "string",
                        "description": (
                            "Filter by node type (e.g. 'heading', 'paragraph', "
                            "'table', 'list', 'figure')."
                        ),
                    },
                    "page_index": {
                        "type": "integer",
                        "description": "Filter to a specific 0-based page index.",
                    },
                    "text_query": {
                        "type": "string",
                        "description": "Case-insensitive substring search on text content.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum nodes to return (default 100).",
                        "default": 100,
                    },
                },
                "required": ["pdf_path"],
            },
        ),
        Tool(
            name="nextpdf_get_outline",
            description=(
                "Get the document outline / table of contents. Extracts heading "
                "nodes from the AST to build a structural overview of the PDF."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "pdf_path": {
                        "type": "string",
                        "description": _DESC_PDF_PATH,
                    },
                },
                "required": ["pdf_path"],
            },
        ),
        Tool(
            name="nextpdf_diff",
            description=(
                "Compare two PDF files structurally. Returns a summary of "
                "added, removed, and changed AST nodes between the original "
                "and modified documents."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "original_pdf_path": {
                        "type": "string",
                        "description": "Absolute path to the original PDF.",
                    },
                    "modified_pdf_path": {
                        "type": "string",
                        "description": "Absolute path to the modified PDF.",
                    },
                },
                "required": ["original_pdf_path", "modified_pdf_path"],
            },
        ),
    ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_pdf_file(pdf_path: str) -> bytes:
    """Read PDF bytes from an absolute file path."""
    p = Path(pdf_path)
    if not p.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")
    if not p.is_file():
        raise ValueError(f"Path is not a file: {pdf_path}")
    return p.read_bytes()


def _serialize(obj: object) -> str:
    """Serialize a pydantic model or list to a JSON string."""
    data: object
    if isinstance(obj, list):
        data = [
            item.model_dump(mode="json") if hasattr(item, "model_dump") else item for item in obj
        ]
    elif hasattr(obj, "model_dump"):
        data = obj.model_dump(mode="json")
    else:
        data = obj
    return json.dumps(data, indent=2, ensure_ascii=False)


def _get_client() -> AsyncNextPDF:
    """Build an AsyncNextPDF client from environment variables."""
    base_url = os.environ.get("NEXTPDF_BASE_URL", "")
    api_key = os.environ.get("NEXTPDF_API_KEY", "")
    if not base_url:
        raise RuntimeError(
            "NEXTPDF_BASE_URL environment variable is required. Set it to your NextPDF server URL."
        )
    if not api_key:
        raise RuntimeError(
            "NEXTPDF_API_KEY environment variable is required. Set it to your NextPDF API key."
        )
    return AsyncNextPDF(base_url=base_url, api_key=api_key)


def _clamp_page_range(max_pages: int) -> tuple[int, int]:
    """Return (start, end) page range clamped by max_pages."""
    return 0, max(0, max_pages - 1)


# ---------------------------------------------------------------------------
# Tool dispatch
# ---------------------------------------------------------------------------


async def _handle_extract_text(arguments: dict[str, Any]) -> str:
    """Handle nextpdf_extract_text tool call."""
    pdf_path: str = arguments["pdf_path"]
    page_index: int | None = arguments.get("page_index")
    headings_only: bool = arguments.get("headings_only", False)

    pdf_data = _read_pdf_file(pdf_path)
    client = _get_client()

    blocks = await client.ast.extract_cited_text(
        pdf_data,
        page_index=page_index,
        headings_only=headings_only,
    )
    return _serialize(blocks)


async def _handle_extract_tables(arguments: dict[str, Any]) -> str:
    """Handle nextpdf_extract_tables tool call."""
    pdf_path: str = arguments["pdf_path"]
    page_start: int | None = arguments.get("page_start")
    page_end: int | None = arguments.get("page_end")

    pdf_data = _read_pdf_file(pdf_path)
    client = _get_client()

    page_range: dict[str, int] | None = None
    if page_start is not None or page_end is not None:
        page_range = {}
        if page_start is not None:
            page_range["start"] = page_start
        if page_end is not None:
            page_range["end"] = page_end

    response = await client.ast.extract_cited_tables(pdf_data, page_range=page_range)
    return _serialize(response)


async def _handle_get_ast(arguments: dict[str, Any]) -> str:
    """Handle nextpdf_get_ast tool call."""
    pdf_path: str = arguments["pdf_path"]
    max_pages: int = arguments.get("max_pages", _DEFAULT_MAX_PAGES)
    token_budget: int | None = arguments.get("token_budget")

    pdf_data = _read_pdf_file(pdf_path)
    client = _get_client()

    _, end = _clamp_page_range(max_pages)
    doc = await client.ast.get_document_ast(
        pdf_data,
        page_range_start=0,
        page_range_end=end,
        token_budget=token_budget,
    )
    return _serialize(doc)


async def _handle_info(arguments: dict[str, Any]) -> str:
    """Handle nextpdf_info tool call."""
    pdf_path: str = arguments["pdf_path"]

    pdf_data = _read_pdf_file(pdf_path)
    client = _get_client()
    doc = await client.ast.get_document_ast(pdf_data)

    info: dict[str, Any] = {
        "schema_version": doc.schema_version,
        "source_hash": doc.source_hash,
        "page_count": doc.page_count,
        "estimated_tokens": doc.estimated_tokens,
        "root_node_type": doc.root.type.value,
        "root_children_count": len(doc.root.children),
    }
    return json.dumps(info, indent=2, ensure_ascii=False)


async def _handle_health(_arguments: dict[str, Any]) -> str:
    """Handle nextpdf_health tool call."""
    base_url = os.environ.get("NEXTPDF_BASE_URL", "(not set)")
    has_key = bool(os.environ.get("NEXTPDF_API_KEY"))
    info: dict[str, Any] = {
        "sdk_version": __version__,
        "server_url": base_url,
        "api_key_configured": has_key,
        "status": "ok" if has_key and base_url != "(not set)" else "misconfigured",
    }
    return json.dumps(info, indent=2, ensure_ascii=False)


async def _handle_search(arguments: dict[str, Any]) -> str:
    """Handle nextpdf_search tool call."""
    pdf_path: str = arguments["pdf_path"]
    node_type: str | None = arguments.get("node_type")
    page_index: int | None = arguments.get("page_index")
    text_query: str | None = arguments.get("text_query")
    max_results: int = arguments.get("max_results", 100)

    pdf_data = _read_pdf_file(pdf_path)
    client = _get_client()

    response = await client.ast.search_ast_nodes(
        pdf_data,
        node_type=node_type,
        page_index=page_index,
        text_query=text_query,
        max_results=max_results,
    )
    return _serialize(response)


async def _handle_get_outline(arguments: dict[str, Any]) -> str:
    """Handle nextpdf_get_outline tool call.

    Extracts heading nodes from the AST to build a document outline.
    """
    pdf_path: str = arguments["pdf_path"]

    pdf_data = _read_pdf_file(pdf_path)
    client = _get_client()

    response = await client.ast.search_ast_nodes(
        pdf_data,
        node_type="heading",
        max_results=500,
    )

    outline: list[dict[str, Any]] = []
    for node in response.nodes:
        outline.append(
            {
                "id": node.id,
                "page_index": node.page_index,
                "text": node.text_content or "",
                "depth": node.attributes.get("level", 1),
            }
        )

    result: dict[str, Any] = {
        "outline": outline,
        "heading_count": len(outline),
        "total_matches": response.total_matches,
        "truncated": response.truncated,
    }
    return json.dumps(result, indent=2, ensure_ascii=False)


async def _handle_diff(arguments: dict[str, Any]) -> str:
    """Handle nextpdf_diff tool call."""
    original_path: str = arguments["original_pdf_path"]
    modified_path: str = arguments["modified_pdf_path"]

    original_data = _read_pdf_file(original_path)
    modified_data = _read_pdf_file(modified_path)
    client = _get_client()

    response = await client.ast.get_ast_diff(original_data, modified_data)
    return _serialize(response)


# Tool name -> handler mapping
_TOOL_HANDLERS: dict[str, Any] = {
    "nextpdf_extract_text": _handle_extract_text,
    "nextpdf_extract_tables": _handle_extract_tables,
    "nextpdf_get_ast": _handle_get_ast,
    "nextpdf_info": _handle_info,
    "nextpdf_health": _handle_health,
    "nextpdf_search": _handle_search,
    "nextpdf_get_outline": _handle_get_outline,
    "nextpdf_diff": _handle_diff,
}


# ---------------------------------------------------------------------------
# Server setup
# ---------------------------------------------------------------------------


def _create_server() -> Server:
    """Create and configure the MCP server with all tool handlers."""
    server = Server(_SERVER_NAME)

    @server.list_tools()  # type: ignore[untyped-decorator]
    async def list_tools() -> list[Tool]:
        return _tool_definitions()

    @server.call_tool()  # type: ignore[untyped-decorator]
    async def call_tool(name: str, arguments: dict[str, Any]) -> Sequence[TextContent]:
        handler = _TOOL_HANDLERS.get(name)
        if handler is None:
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"error": f"Unknown tool: {name}"}),
                )
            ]

        try:
            result = await handler(arguments)
            return [TextContent(type="text", text=result)]
        except FileNotFoundError as exc:
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"error": str(exc)}),
                )
            ]
        except NextPDFError as exc:
            error_info: dict[str, Any] = {
                "error": str(exc),
                "error_type": type(exc).__name__,
            }
            if exc.status_code is not None:
                error_info["status_code"] = exc.status_code
            return [
                TextContent(
                    type="text",
                    text=json.dumps(error_info),
                )
            ]
        except Exception as exc:
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"error": f"Unexpected error: {exc}"}),
                )
            ]

    return server


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def serve() -> None:
    """Run the NextPDF MCP server over stdio."""
    server = _create_server()
    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options)


def main() -> None:
    """Synchronous entry point for ``python -m nextpdf.mcp``."""
    asyncio.run(serve())


if __name__ == "__main__":
    main()
