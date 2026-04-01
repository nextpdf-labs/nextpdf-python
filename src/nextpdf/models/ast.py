"""Pydantic v2 models for NextPDF AST responses."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class NodeType(str, Enum):
    """AST node type vocabulary."""

    DOCUMENT = "document"
    SECTION = "section"
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST = "list"
    LIST_ITEM = "list_item"
    TABLE = "table"
    TABLE_ROW = "table_row"
    TABLE_CELL = "table_cell"
    FIGURE = "figure"
    CODE = "code"
    ANNOTATION = "annotation"
    ARTIFACT = "artifact"
    FORM_FIELD = "form_field"


class BoundingBox(BaseModel):
    """Normalized bounding box (0.0-1.0 coordinates)."""

    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)
    width: float = Field(ge=0.0, le=1.0)
    height: float = Field(ge=0.0, le=1.0)


class CitationAnchor(BaseModel):
    """Citation reference with spatial position."""

    node_id: str
    page_index: int = Field(ge=0)
    bbox: BoundingBox
    confidence: float = Field(ge=0.0, le=1.0)
    content_hash: str | None = None


class AstNode(BaseModel):
    """Single node in the AST tree."""

    id: str
    type: NodeType
    page_index: int = Field(ge=0)
    bbox: BoundingBox | None = None
    text_content: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    children: list[AstNode] = Field(default_factory=list)  # pyright: ignore[reportUnknownVariableType]
    pdf_object_number: int | None = None
    mcid: int | None = None

    @property
    def estimated_tokens(self) -> int:
        """Rough token estimate for this node's text content."""
        if not self.text_content:
            return 0
        # Simplified: ~4 chars per token
        return max(1, len(self.text_content) // 4)


# Enable forward reference resolution for recursive model
AstNode.model_rebuild()


class AstDocument(BaseModel):
    """Top-level AST document."""

    schema_version: str = Field(alias="schemaVersion")
    source_hash: str = Field(alias="sourceHash")
    page_count: int = Field(ge=1, alias="pageCount")
    root: AstNode

    model_config = {"populate_by_name": True}

    @property
    def estimated_tokens(self) -> int:
        """Rough token estimate for the entire document."""
        return self._count_tokens(self.root)

    def _count_tokens(self, node: AstNode) -> int:
        total = node.estimated_tokens
        for child in node.children:
            total += self._count_tokens(child)
        return total


class CitedTextBlock(BaseModel):
    """Extracted text block with citation."""

    text: str
    citation: CitationAnchor
    node_type: str | None = None
    # chunk_index is present when token-budget pagination is active
    chunk_index: int | None = None
    # depth is present in the UntaggedFallbackBuilder path only
    depth: int | None = Field(default=None, ge=0)


class AstNodeMeta(BaseModel):
    """Metadata returned with AST tool responses (ETag, metering)."""

    etag: str | None = None
    pages_processed: int | None = None

    model_config = ConfigDict(frozen=True)


class AstNodeShallow(BaseModel):
    """Shallow node representation from search results (no deep children)."""

    id: str
    type: NodeType
    page_index: int
    bbox: BoundingBox | None = None
    text_content: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    children_count: int = 0

    model_config = ConfigDict(frozen=True)


class GetAstNodeResponse(BaseModel):
    """Response from get_ast_node."""

    node: AstNode
    meta: AstNodeMeta = Field(default_factory=AstNodeMeta)

    model_config = ConfigDict(frozen=True)


class SearchAstNodesResponse(BaseModel):
    """Response from search_ast_nodes."""

    nodes: list[AstNodeShallow]
    total_matches: int
    truncated: bool = False
    meta: AstNodeMeta = Field(default_factory=AstNodeMeta)

    model_config = ConfigDict(frozen=True)


class CitedTableCell(BaseModel):
    """A single cell within a cited table block."""

    model_config = ConfigDict(frozen=True)

    row: int
    col: int
    row_span: int = 1
    col_span: int = 1
    text: str | None
    bbox: BoundingBox | None
    confidence: float


class CitedTableBlock(BaseModel):
    """A table extracted from a PDF page with its citation anchor."""

    model_config = ConfigDict(frozen=True)

    table_node_id: str
    page_index: int
    citation_anchor: CitationAnchor | None
    row_count: int
    col_count: int
    rows: list[list[CitedTableCell]]


class ExtractCitedTablesResponse(BaseModel):
    """Response from extract_cited_tables."""

    model_config = ConfigDict(frozen=True)

    tables: list[CitedTableBlock]
    table_count: int
    pages_processed: int | None = None


class AstDiffEntry(BaseModel):
    """A single entry in the AST diff between two PDF versions."""

    model_config = ConfigDict(frozen=True)

    type: str  # "added" | "removed" | "changed"
    node_id: str
    node_type: str
    page_index: int
    text_preview: str | None = None


class AstDiffSummary(BaseModel):
    """Aggregate counts from an AST diff operation."""

    model_config = ConfigDict(frozen=True)

    added_node_count: int
    removed_node_count: int
    changed_node_count: int


class GetAstDiffResponse(BaseModel):
    """Response from get_ast_diff."""

    model_config = ConfigDict(frozen=True)

    original_page_count: int
    modified_page_count: int
    summary: AstDiffSummary
    diff: list[AstDiffEntry]
    pages_processed: int | None = None
