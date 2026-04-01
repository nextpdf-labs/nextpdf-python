"""Local PDF extraction backend using pypdf -- no remote server required."""

from __future__ import annotations

import hashlib
import io
import logging
from typing import Any

import pypdf
from pypdf.generic import (
    ArrayObject,
    DictionaryObject,
    IndirectObject,
)

from nextpdf.models.ast import (
    AstDiffEntry,
    AstDiffSummary,
    AstDocument,
    AstNode,
    AstNodeMeta,
    AstNodeShallow,
    BoundingBox,
    CitationAnchor,
    CitedTableBlock,
    CitedTableCell,
    CitedTextBlock,
    ExtractCitedTablesResponse,
    GetAstDiffResponse,
    GetAstNodeResponse,
    NodeType,
    SearchAstNodesResponse,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SCHEMA_VERSION = "1.0"

_DEFAULT_MAX_PAGES = 2000
_DEFAULT_MAX_FILE_SIZE = 200_000_000  # 200 MB

_STRUCT_TAG_MAP: dict[str, NodeType] = {
    "/Document": NodeType.DOCUMENT,
    "/Sect": NodeType.SECTION,
    "/Part": NodeType.SECTION,
    "/Div": NodeType.SECTION,
    "/H": NodeType.HEADING,
    "/H1": NodeType.HEADING,
    "/H2": NodeType.HEADING,
    "/H3": NodeType.HEADING,
    "/H4": NodeType.HEADING,
    "/H5": NodeType.HEADING,
    "/H6": NodeType.HEADING,
    "/P": NodeType.PARAGRAPH,
    "/L": NodeType.LIST,
    "/LI": NodeType.LIST_ITEM,
    "/Table": NodeType.TABLE,
    "/TR": NodeType.TABLE_ROW,
    "/TD": NodeType.TABLE_CELL,
    "/TH": NodeType.TABLE_CELL,
    "/Figure": NodeType.FIGURE,
    "/Code": NodeType.CODE,
    "/Annot": NodeType.ANNOTATION,
    "/Art": NodeType.ARTIFACT,
}

_HEADING_LEVEL_MAP: dict[str, int] = {
    "/H": 1,
    "/H1": 1,
    "/H2": 2,
    "/H3": 3,
    "/H4": 4,
    "/H5": 5,
    "/H6": 6,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# pypdf's object graph uses PdfObject | None loosely and wraps every
# reference in IndirectObject.  We intentionally accept/return ``Any`` in
# these two thin resolution helpers and immediately narrow via isinstance.
# The ANN401 suppression is scoped to just these two functions.


def _resolve(obj: Any) -> Any:  # noqa: ANN401
    """Dereference pypdf IndirectObject chains to their actual value."""
    while isinstance(obj, IndirectObject):
        obj = obj.get_object()
    return obj


def _resolve_dict(obj: Any) -> DictionaryObject | None:  # noqa: ANN401
    """Resolve *obj* and return it only if it is a DictionaryObject."""
    resolved = _resolve(obj)
    return resolved if isinstance(resolved, DictionaryObject) else None


def _compute_source_hash(pdf_data: bytes) -> str:
    """SHA-256 of the first 4 KB of the PDF, used as a stable identifier."""
    return hashlib.sha256(pdf_data[:4096]).hexdigest()


def _make_node_id(hash6: str, page_index: int, seq: int) -> str:
    """Generate a stable, deterministic node ID."""
    return f"ast:{hash6}:{page_index}:{seq}"


def _content_hash(text: str) -> str:
    """Short content hash for citation anchors."""
    return hashlib.sha256(
        text.encode("utf-8", errors="replace"),
    ).hexdigest()[:16]


def _is_struct_elem(obj: object) -> bool:
    """Return True when *obj* is a DictionaryObject with an /S tag."""
    return isinstance(obj, DictionaryObject) and obj.get("/S") is not None


# ---------------------------------------------------------------------------
# StructTree walker
# ---------------------------------------------------------------------------


class _StructTreeWalker:
    """Walk a PDF StructTree and produce an AstNode tree."""

    def __init__(self, reader: pypdf.PdfReader, hash6: str) -> None:
        self._reader = reader
        self._hash6 = hash6
        self._seq: int = 0
        # Build page-object-number to page-index mapping
        self._page_index_map: dict[int, int] = {}
        for idx, page in enumerate(reader.pages):
            ref = getattr(page, "indirect_reference", None)
            if ref is not None:
                self._page_index_map[ref.idnum] = idx

    def next_seq(self) -> int:
        """Return the next sequence number and increment the counter."""
        seq = self._seq
        self._seq += 1
        return seq

    def _resolve_page_index(self, elem: DictionaryObject) -> int:
        """Determine the page index of a struct element."""
        pg_raw = elem.get("/Pg")
        if pg_raw is None:
            return 0

        pg_resolved = _resolve(pg_raw)
        if not isinstance(pg_resolved, DictionaryObject):
            return 0

        # Fast path via indirect-object id
        idnum: int | None = getattr(pg_raw, "idnum", None)
        if idnum is not None:
            cached = self._page_index_map.get(idnum)
            if cached is not None:
                return cached

        # Slow fallback: linear scan
        for i, page in enumerate(self._reader.pages):
            ref = getattr(page, "indirect_reference", None)
            if ref is not None and idnum is not None and ref.idnum == idnum:
                return i
        return 0

    def _extract_element_text(
        self,
        elem: DictionaryObject,
        page_index: int,
    ) -> str:
        """Best-effort text extraction from a struct element's content."""
        k_raw = elem.get("/K")
        if k_raw is None:
            return ""

        k_val = _resolve(k_raw)

        # /K can be an integer MCID, a dict, or an array of them.
        # For non-leaf elements /K contains child StructElems --
        # we must NOT grab page text (children handle that).
        if isinstance(k_val, ArrayObject):
            if any(_is_struct_elem(_resolve(item)) for item in k_val):
                return ""
        elif _is_struct_elem(k_val):
            return ""

        # Leaf element -- try to extract text from the page.
        try:
            if 0 <= page_index < len(self._reader.pages):
                text = self._reader.pages[page_index].extract_text() or ""
                return text.strip()
        except Exception:
            pass
        return ""

    def _collect_children(
        self,
        k_val: object,
    ) -> list[AstNode]:
        """Collect child AstNodes from a /K entry value."""
        children: list[AstNode] = []
        if isinstance(k_val, ArrayObject):
            for child_raw in k_val:
                if _is_struct_elem(_resolve(child_raw)):
                    child_node = self.walk(child_raw)
                    if child_node is not None:
                        children.append(child_node)
        elif _is_struct_elem(k_val):
            child_node = self.walk(k_val)
            if child_node is not None:
                children.append(child_node)
        return children

    def _build_attributes(
        self,
        struct_type: str,
    ) -> dict[str, Any]:
        """Build the attributes dict for a struct element."""
        attributes: dict[str, Any] = {}
        if struct_type in _HEADING_LEVEL_MAP:
            attributes["level"] = _HEADING_LEVEL_MAP[struct_type]
        attributes["struct_type"] = struct_type
        return attributes

    def walk(self, elem_raw: object) -> AstNode | None:
        """Recursively walk a struct element and return an AstNode."""
        elem = _resolve(elem_raw)
        if not isinstance(elem, DictionaryObject):
            return None

        struct_type_raw = elem.get("/S")
        if struct_type_raw is None:
            return None

        struct_type = str(struct_type_raw)
        node_type = _STRUCT_TAG_MAP.get(struct_type, NodeType.ARTIFACT)
        page_index = self._resolve_page_index(elem)
        node_id = _make_node_id(
            self._hash6,
            page_index,
            self.next_seq(),
        )

        # MCID
        k_val = _resolve(elem.get("/K"))
        mcid = k_val if isinstance(k_val, int) else None

        children = self._collect_children(k_val)

        # Only extract text for leaf nodes
        text_content: str | None = None
        if not children:
            raw_text = self._extract_element_text(elem, page_index)
            if raw_text:
                text_content = raw_text

        return AstNode(
            id=node_id,
            type=node_type,
            page_index=page_index,
            bbox=None,
            text_content=text_content,
            attributes=self._build_attributes(struct_type),
            children=children,
            mcid=mcid,
        )


# ---------------------------------------------------------------------------
# LocalBackend
# ---------------------------------------------------------------------------


class LocalBackend:
    """Local PDF extraction using pypdf -- no remote server required.

    Implements the :class:`~nextpdf.backends.protocol.PdfBackend` protocol
    so it can be injected into :class:`~nextpdf.AsyncNextPDF` as a drop-in
    replacement for the remote backend.

    Two extraction paths:

    1. **Tagged PDF** -- walks the PDF StructTree to build a semantic AST.
    2. **Heuristic fallback** -- splits page text into paragraphs when no
       StructTree is present.  Confidence is 0.5 for heuristic nodes.
    """

    def __init__(
        self,
        *,
        max_pages: int = _DEFAULT_MAX_PAGES,
        max_file_size: int = _DEFAULT_MAX_FILE_SIZE,
    ) -> None:
        self._max_pages: int = max_pages
        self._max_file_size: int = max_file_size

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_input(self, pdf_data: bytes) -> None:
        """Raise ValueError if the PDF data exceeds configured limits."""
        if len(pdf_data) > self._max_file_size:
            raise ValueError(
                f"PDF size {len(pdf_data):,} bytes exceeds maximum {self._max_file_size:,} bytes"
            )

    @staticmethod
    def _open_reader(pdf_data: bytes) -> pypdf.PdfReader:
        """Open a PdfReader from raw bytes (strict=False for tolerance)."""
        try:
            return pypdf.PdfReader(io.BytesIO(pdf_data), strict=False)
        except Exception as exc:
            raise ValueError(f"Cannot open PDF: {exc}") from exc

    @staticmethod
    def _has_struct_tree(reader: pypdf.PdfReader) -> bool:
        """Check whether the PDF contains a StructTreeRoot."""
        try:
            root = _resolve_dict(reader.trailer.get("/Root"))
            if root is not None:
                return root.get("/StructTreeRoot") is not None
        except Exception:
            pass
        return False

    @staticmethod
    def _get_struct_tree_root(
        reader: pypdf.PdfReader,
    ) -> DictionaryObject | None:
        """Return the resolved StructTreeRoot dictionary, or None."""
        try:
            root = _resolve_dict(reader.trailer.get("/Root"))
            if root is not None:
                return _resolve_dict(root.get("/StructTreeRoot"))
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------
    # Tagged PDF path
    # ------------------------------------------------------------------

    def _build_tagged_ast(
        self,
        reader: pypdf.PdfReader,
        source_hash: str,
    ) -> AstNode:
        """Walk the StructTree and produce the AST root node."""
        hash6 = source_hash[:6]
        walker = _StructTreeWalker(reader, hash6)

        st_root = self._get_struct_tree_root(reader)
        assert st_root is not None  # caller already verified

        children: list[AstNode] = []
        k_val = _resolve(st_root.get("/K"))

        if isinstance(k_val, ArrayObject):
            for child_raw in k_val:
                node = walker.walk(child_raw)
                if node is not None:
                    children.append(node)
        elif isinstance(k_val, DictionaryObject):
            node = walker.walk(k_val)
            if node is not None:
                children.append(node)

        # Use the first child as logical root when it is /Document,
        # otherwise wrap in an explicit document node.
        if len(children) == 1 and children[0].type == NodeType.DOCUMENT:
            return children[0]

        return AstNode(
            id=_make_node_id(hash6, 0, walker.next_seq()),
            type=NodeType.DOCUMENT,
            page_index=0,
            text_content=None,
            attributes={},
            children=children,
        )

    # ------------------------------------------------------------------
    # Heuristic (untagged) path
    # ------------------------------------------------------------------

    def _build_heuristic_ast(
        self,
        reader: pypdf.PdfReader,
        source_hash: str,
        *,
        page_range_start: int | None = None,
        page_range_end: int | None = None,
    ) -> AstNode:
        """Build a flat AST from plain text extraction (untagged PDFs)."""
        hash6 = source_hash[:6]
        seq = 0
        page_count = len(reader.pages)

        start = page_range_start if page_range_start is not None else 0
        end = page_range_end if page_range_end is not None else page_count - 1
        start = max(0, min(start, page_count - 1))
        end = max(start, min(end, page_count - 1))

        section_children: list[AstNode] = []

        for page_idx in range(start, end + 1):
            try:
                page_text = reader.pages[page_idx].extract_text() or ""
            except Exception:
                page_text = ""

            paragraphs = self._split_paragraphs(page_text)
            para_nodes: list[AstNode] = []
            for para_text in paragraphs:
                seq += 1
                para_nodes.append(
                    AstNode(
                        id=_make_node_id(hash6, page_idx, seq),
                        type=NodeType.PARAGRAPH,
                        page_index=page_idx,
                        bbox=None,
                        text_content=para_text,
                        attributes={"heuristic": True},
                        children=[],
                    )
                )

            seq += 1
            section_children.append(
                AstNode(
                    id=_make_node_id(hash6, page_idx, seq),
                    type=NodeType.SECTION,
                    page_index=page_idx,
                    bbox=None,
                    text_content=None,
                    attributes={"heuristic": True, "page": page_idx},
                    children=para_nodes,
                )
            )

        seq += 1
        return AstNode(
            id=_make_node_id(hash6, 0, seq),
            type=NodeType.DOCUMENT,
            page_index=0,
            text_content=None,
            attributes={"heuristic": True},
            children=section_children,
        )

    @staticmethod
    def _split_paragraphs(text: str) -> list[str]:
        """Split text into paragraph-like chunks on double newlines."""
        if not text.strip():
            return []

        raw_blocks = text.split("\n\n")
        result: list[str] = []
        for block in raw_blocks:
            cleaned = block.strip()
            if cleaned:
                result.append(cleaned)
        return result if result else [text.strip()]

    # ------------------------------------------------------------------
    # AST tree utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _walk_nodes(root: AstNode) -> list[AstNode]:
        """Depth-first walk of all nodes in the AST."""
        nodes: list[AstNode] = []
        stack: list[AstNode] = [root]
        while stack:
            node = stack.pop()
            nodes.append(node)
            for child in reversed(node.children):
                stack.append(child)
        return nodes

    @staticmethod
    def _find_node_by_id(
        root: AstNode,
        node_id: str,
    ) -> AstNode | None:
        """Find a node by ID in the AST tree."""
        stack: list[AstNode] = [root]
        while stack:
            node = stack.pop()
            if node.id == node_id:
                return node
            for child in reversed(node.children):
                stack.append(child)
        return None

    @staticmethod
    def _is_heuristic(root: AstNode) -> bool:
        """Check if the AST was built via heuristic fallback."""
        return bool(root.attributes.get("heuristic"))

    # ------------------------------------------------------------------
    # PdfBackend protocol: get_document_ast
    # ------------------------------------------------------------------

    async def get_document_ast(
        self,
        pdf_data: bytes,
        *,
        page_range_start: int | None = None,
        page_range_end: int | None = None,
        token_budget: int | None = None,  # reserved for future use
    ) -> AstDocument:
        """Build a Semantic AST from PDF bytes.

        ``token_budget`` is accepted for protocol compliance but not yet
        implemented in the local engine.  The method is ``async`` to
        satisfy the :class:`PdfBackend` protocol even though the actual
        work is synchronous.
        """
        _ = token_budget  # protocol parameter, not yet used
        self._validate_input(pdf_data)
        reader = self._open_reader(pdf_data)

        page_count = len(reader.pages)
        if page_count == 0:
            raise ValueError("PDF has zero pages")
        if page_count > self._max_pages:
            raise ValueError(f"PDF has {page_count} pages, exceeding maximum {self._max_pages}")

        source_hash = _compute_source_hash(pdf_data)

        if self._has_struct_tree(reader):
            logger.debug("Tagged PDF detected -- walking StructTree")
            root = self._build_tagged_ast(reader, source_hash)
        else:
            logger.debug(
                "Untagged PDF -- heuristic paragraph splitting",
            )
            root = self._build_heuristic_ast(
                reader,
                source_hash,
                page_range_start=page_range_start,
                page_range_end=page_range_end,
            )

        return AstDocument(
            schemaVersion=_SCHEMA_VERSION,
            sourceHash=source_hash,
            pageCount=page_count,
            root=root,
        )

    # ------------------------------------------------------------------
    # PdfBackend protocol: extract_cited_text
    # ------------------------------------------------------------------

    async def extract_cited_text(
        self,
        pdf_data: bytes,
        *,
        page_index: int | None = None,
        headings_only: bool = False,
    ) -> list[CitedTextBlock]:
        """Extract text blocks with citation anchors."""
        doc = await self.get_document_ast(pdf_data)
        is_heuristic = self._is_heuristic(doc.root)
        confidence = 0.5 if is_heuristic else 1.0

        all_nodes = self._walk_nodes(doc.root)
        blocks: list[CitedTextBlock] = []

        for node in all_nodes:
            if not node.text_content:
                continue
            if page_index is not None and node.page_index != page_index:
                continue
            if headings_only and node.type != NodeType.HEADING:
                continue

            anchor = CitationAnchor(
                node_id=node.id,
                page_index=node.page_index,
                bbox=node.bbox
                or BoundingBox(
                    x=0.0,
                    y=0.0,
                    width=1.0,
                    height=1.0,
                ),
                confidence=confidence,
                content_hash=_content_hash(node.text_content),
            )
            blocks.append(
                CitedTextBlock(
                    text=node.text_content,
                    citation=anchor,
                    node_type=node.type.value,
                )
            )

        return blocks

    # ------------------------------------------------------------------
    # PdfBackend protocol: extract_cited_tables
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_table_node(table_node: AstNode) -> CitedTableBlock:
        """Convert a TABLE AstNode into a CitedTableBlock."""
        rows_data: list[list[CitedTableCell]] = []
        row_idx = 0
        max_cols = 0

        for child in table_node.children:
            if child.type != NodeType.TABLE_ROW:
                continue
            row_cells: list[CitedTableCell] = []
            col_idx = 0
            for cell_node in child.children:
                if cell_node.type != NodeType.TABLE_CELL:
                    continue
                row_cells.append(
                    CitedTableCell(
                        row=row_idx,
                        col=col_idx,
                        text=cell_node.text_content,
                        bbox=cell_node.bbox,
                        confidence=1.0,
                    )
                )
                col_idx += 1
            if col_idx > max_cols:
                max_cols = col_idx
            rows_data.append(row_cells)
            row_idx += 1

        anchor: CitationAnchor | None = None
        if table_node.text_content:
            anchor = CitationAnchor(
                node_id=table_node.id,
                page_index=table_node.page_index,
                bbox=table_node.bbox
                or BoundingBox(
                    x=0.0,
                    y=0.0,
                    width=1.0,
                    height=1.0,
                ),
                confidence=1.0,
                content_hash=_content_hash(
                    table_node.text_content,
                ),
            )

        return CitedTableBlock(
            table_node_id=table_node.id,
            page_index=table_node.page_index,
            citation_anchor=anchor,
            row_count=row_idx,
            col_count=max_cols,
            rows=rows_data,
        )

    async def extract_cited_tables(
        self,
        pdf_data: bytes,
        *,
        page_range: dict[str, int] | None = None,
    ) -> ExtractCitedTablesResponse:
        """Extract tables from a PDF with citation anchors."""
        doc = await self.get_document_ast(pdf_data)

        if self._is_heuristic(doc.root):
            return ExtractCitedTablesResponse(
                tables=[],
                table_count=0,
                pages_processed=doc.page_count,
            )

        all_nodes = self._walk_nodes(doc.root)
        table_nodes = [n for n in all_nodes if n.type == NodeType.TABLE]

        if page_range is not None:
            p_start = page_range.get("start", 0)
            p_end = page_range.get("end", doc.page_count - 1)
            table_nodes = [t for t in table_nodes if p_start <= t.page_index <= p_end]

        tables = [self._parse_table_node(tn) for tn in table_nodes]

        return ExtractCitedTablesResponse(
            tables=tables,
            table_count=len(tables),
            pages_processed=doc.page_count,
        )

    # ------------------------------------------------------------------
    # PdfBackend protocol: search_ast_nodes
    # ------------------------------------------------------------------

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
        doc = await self.get_document_ast(pdf_data)
        all_nodes = self._walk_nodes(doc.root)

        matched: list[AstNodeShallow] = []
        for node in all_nodes:
            if node_type is not None and node.type.value != node_type:
                continue
            if page_index is not None and node.page_index != page_index:
                continue
            if text_query is not None and (
                not node.text_content or text_query.lower() not in node.text_content.lower()
            ):
                continue

            matched.append(
                AstNodeShallow(
                    id=node.id,
                    type=node.type,
                    page_index=node.page_index,
                    bbox=node.bbox,
                    text_content=node.text_content,
                    attributes=node.attributes,
                    children_count=len(node.children),
                )
            )

        total = len(matched)
        truncated = total > max_results
        matched = matched[:max_results]

        return SearchAstNodesResponse(
            nodes=matched,
            total_matches=total,
            truncated=truncated,
            meta=AstNodeMeta(),
        )

    # ------------------------------------------------------------------
    # PdfBackend protocol: get_ast_node
    # ------------------------------------------------------------------

    async def get_ast_node(
        self,
        pdf_data: bytes,
        node_id: str,
    ) -> GetAstNodeResponse:
        """Retrieve a single AST node by its node ID."""
        doc = await self.get_document_ast(pdf_data)
        found = self._find_node_by_id(doc.root, node_id)
        if found is None:
            raise ValueError(f"Node not found: {node_id}")

        return GetAstNodeResponse(
            node=found,
            meta=AstNodeMeta(),
        )

    # ------------------------------------------------------------------
    # PdfBackend protocol: get_ast_diff
    # ------------------------------------------------------------------

    @staticmethod
    def _node_sig(node: AstNode) -> str:
        """Signature for content-hash based node comparison."""
        text = node.text_content or ""
        return f"{node.page_index}:{node.type.value}:{_content_hash(text)}"

    @staticmethod
    def _build_sig_map(nodes: list[AstNode]) -> dict[str, AstNode]:
        """Build a first-occurrence signature map from a node list."""
        sigs: dict[str, AstNode] = {}
        for n in nodes:
            sig = LocalBackend._node_sig(n)
            if sig not in sigs:
                sigs[sig] = n
        return sigs

    @staticmethod
    def _collect_diff_entries(
        source: dict[str, AstNode],
        other: dict[str, AstNode],
        diff_type: str,
    ) -> list[AstDiffEntry]:
        """Collect diff entries for sigs present in *source* but not *other*."""
        entries: list[AstDiffEntry] = []
        for sig, node in source.items():
            if sig not in other:
                preview = (node.text_content or "")[:120] or None
                entries.append(
                    AstDiffEntry(
                        type=diff_type,
                        node_id=node.id,
                        node_type=node.type.value,
                        page_index=node.page_index,
                        text_preview=preview,
                    )
                )
        return entries

    async def get_ast_diff(
        self,
        original_pdf_data: bytes,
        modified_pdf_data: bytes,
    ) -> GetAstDiffResponse:
        """Compare two PDFs and return structural AST differences."""
        doc_a = await self.get_document_ast(original_pdf_data)
        doc_b = await self.get_document_ast(modified_pdf_data)

        sigs_a = self._build_sig_map(self._walk_nodes(doc_a.root))
        sigs_b = self._build_sig_map(self._walk_nodes(doc_b.root))

        diff_entries = self._collect_diff_entries(
            sigs_a, sigs_b, "removed"
        ) + self._collect_diff_entries(sigs_b, sigs_a, "added")

        added = sum(1 for e in diff_entries if e.type == "added")
        removed = sum(1 for e in diff_entries if e.type == "removed")

        return GetAstDiffResponse(
            original_page_count=doc_a.page_count,
            modified_page_count=doc_b.page_count,
            summary=AstDiffSummary(
                added_node_count=added,
                removed_node_count=removed,
                changed_node_count=0,
            ),
            diff=diff_entries,
            pages_processed=doc_a.page_count + doc_b.page_count,
        )
