from __future__ import annotations

import pytest
from pydantic import ValidationError

from nextpdf import AstDocument, AstNode, BoundingBox, CitationAnchor, CitedTextBlock, NodeType


class TestNodeType:
    def test_has_all_14_values(self) -> None:
        values = {m.value for m in NodeType}
        assert len(values) == 14
        assert "document" in values
        assert "form_field" in values

    def test_is_str_enum(self) -> None:
        assert NodeType.PARAGRAPH == "paragraph"


class TestBoundingBox:
    def test_valid_bbox(self) -> None:
        b = BoundingBox(x=0.1, y=0.2, width=0.5, height=0.3)
        assert b.x == 0.1

    def test_x_out_of_range_raises(self) -> None:
        with pytest.raises(ValidationError):
            BoundingBox(x=-0.1, y=0.0, width=0.5, height=0.5)

    def test_width_exceeds_one_raises(self) -> None:
        with pytest.raises(ValidationError):
            BoundingBox(x=0.0, y=0.0, width=1.1, height=0.5)

    def test_y_out_of_range_raises(self) -> None:
        with pytest.raises(ValidationError):
            BoundingBox(x=0.0, y=1.5, width=0.5, height=0.5)


class TestCitationAnchor:
    def test_stores_all_fields(self) -> None:
        anchor = CitationAnchor(
            node_id="n-42",
            page_index=3,
            bbox=BoundingBox(x=0.1, y=0.2, width=0.4, height=0.1),
            confidence=0.95,
            content_hash="sha256:deadbeef",
        )
        assert anchor.node_id == "n-42"
        assert anchor.page_index == 3
        assert anchor.confidence == 0.95
        assert anchor.content_hash == "sha256:deadbeef"

    def test_content_hash_optional(self) -> None:
        anchor = CitationAnchor(
            node_id="n-1",
            page_index=0,
            bbox=BoundingBox(x=0.0, y=0.0, width=0.5, height=0.5),
            confidence=1.0,
        )
        assert anchor.content_hash is None

    def test_page_index_negative_raises(self) -> None:
        with pytest.raises(ValidationError):
            CitationAnchor(
                node_id="n-1",
                page_index=-1,
                bbox=BoundingBox(x=0.0, y=0.0, width=0.5, height=0.5),
                confidence=0.5,
            )

    def test_confidence_out_of_range_raises(self) -> None:
        with pytest.raises(ValidationError):
            CitationAnchor(
                node_id="n-1",
                page_index=0,
                bbox=BoundingBox(x=0.0, y=0.0, width=0.5, height=0.5),
                confidence=1.5,
            )


class TestAstNode:
    def test_deserializes_correctly(self) -> None:
        node = AstNode.model_validate(
            {
                "id": "node-1",
                "type": "paragraph",
                "page_index": 0,
                "text_content": "Hello world",
                "attributes": {"lang": "en"},
                "children": [],
            }
        )
        assert node.id == "node-1"
        assert node.type == NodeType.PARAGRAPH
        assert node.text_content == "Hello world"

    def test_optional_fields_default_to_none(self) -> None:
        node = AstNode.model_validate({"id": "n", "type": "section", "page_index": 1})
        assert node.bbox is None
        assert node.text_content is None
        assert node.pdf_object_number is None
        assert node.mcid is None

    def test_estimated_tokens_no_text(self) -> None:
        node = AstNode.model_validate({"id": "n", "type": "figure", "page_index": 0})
        assert node.estimated_tokens == 0

    def test_estimated_tokens_with_text(self) -> None:
        node = AstNode.model_validate(
            {"id": "n", "type": "paragraph", "page_index": 0, "text_content": "a" * 40}
        )
        assert node.estimated_tokens == 10

    def test_estimated_tokens_short_text_returns_at_least_one(self) -> None:
        node = AstNode.model_validate(
            {"id": "n", "type": "heading", "page_index": 0, "text_content": "Hi"}
        )
        assert node.estimated_tokens == 1

    def test_nested_children_deserialize(self) -> None:
        node = AstNode.model_validate(
            {
                "id": "parent",
                "type": "section",
                "page_index": 0,
                "children": [{"id": "child", "type": "paragraph", "page_index": 0}],
            }
        )
        assert len(node.children) == 1
        assert node.children[0].id == "child"


class TestAstDocument:
    def test_round_trip_model_dump_validate(self, ast_document_payload: dict) -> None:
        doc = AstDocument.model_validate(ast_document_payload)
        dumped = doc.model_dump(by_alias=True)
        doc2 = AstDocument.model_validate(dumped)
        assert doc2.schema_version == doc.schema_version
        assert doc2.source_hash == doc.source_hash
        assert doc2.page_count == doc.page_count

    def test_alias_fields(self, ast_document_payload: dict) -> None:
        doc = AstDocument.model_validate(ast_document_payload)
        assert doc.schema_version == "1.0"
        assert doc.source_hash == "abc123def456"
        assert doc.page_count == 2

    def test_populate_by_name(self) -> None:
        doc = AstDocument.model_validate(
            {
                "schema_version": "1.0",
                "source_hash": "xyz",
                "page_count": 1,
                "root": {"id": "r", "type": "document", "page_index": 0},
            }
        )
        assert doc.schema_version == "1.0"

    def test_estimated_tokens_sums_tree(self, ast_document_payload: dict) -> None:
        doc = AstDocument.model_validate(ast_document_payload)
        assert doc.estimated_tokens >= doc.root.estimated_tokens

    def test_page_count_must_be_at_least_one(self) -> None:
        with pytest.raises(ValidationError):
            AstDocument.model_validate(
                {
                    "schemaVersion": "1.0",
                    "sourceHash": "abc",
                    "pageCount": 0,
                    "root": {"id": "r", "type": "document", "page_index": 0},
                }
            )


class TestCitedTextBlock:
    def test_valid_block(self) -> None:
        block = CitedTextBlock(
            text="Important finding.",
            citation=CitationAnchor(
                node_id="n-7",
                page_index=2,
                bbox=BoundingBox(x=0.0, y=0.5, width=0.8, height=0.05),
                confidence=0.87,
            ),
            node_type="paragraph",
            depth=2,
        )
        assert block.text == "Important finding."
        assert block.depth == 2

    def test_depth_cannot_be_negative(self) -> None:
        with pytest.raises(ValidationError):
            CitedTextBlock(
                text="text",
                citation=CitationAnchor(
                    node_id="n",
                    page_index=0,
                    bbox=BoundingBox(x=0.0, y=0.0, width=0.5, height=0.5),
                    confidence=0.5,
                ),
                depth=-1,
            )

    def test_depth_is_optional(self) -> None:
        block = CitedTextBlock(
            text="Pro path block.",
            citation=CitationAnchor(
                node_id="n-1",
                page_index=0,
                bbox=BoundingBox(x=0.0, y=0.0, width=0.5, height=0.1),
                confidence=0.95,
            ),
        )
        assert block.depth is None

    def test_chunk_index_is_optional(self) -> None:
        block = CitedTextBlock(
            text="Fallback path block.",
            citation=CitationAnchor(
                node_id="n-2",
                page_index=1,
                bbox=BoundingBox(x=0.0, y=0.1, width=0.5, height=0.1),
                confidence=0.3,
            ),
            depth=0,
        )
        assert block.chunk_index is None

    def test_chunk_index_can_be_set(self) -> None:
        block = CitedTextBlock(
            text="Chunked block.",
            citation=CitationAnchor(
                node_id="n-3",
                page_index=0,
                bbox=BoundingBox(x=0.0, y=0.2, width=0.8, height=0.05),
                confidence=0.92,
            ),
            chunk_index=5,
        )
        assert block.chunk_index == 5
        assert block.depth is None
