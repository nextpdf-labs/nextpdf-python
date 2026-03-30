"""Shared pytest fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture
def minimal_pdf_bytes() -> bytes:
    """Minimal valid-looking PDF bytes for testing (not a real PDF)."""
    return b"%PDF-1.4 fake content"


@pytest.fixture
def ast_document_payload() -> dict[str, object]:
    """Minimal valid AstDocument JSON payload."""
    return {
        "schemaVersion": "1.0",
        "sourceHash": "abc123def456",
        "pageCount": 2,
        "root": {
            "id": "node-root",
            "type": "document",
            "page_index": 0,
            "text_content": "Hello world from the document",
            "attributes": {},
            "children": [
                {
                    "id": "node-1",
                    "type": "paragraph",
                    "page_index": 0,
                    "text_content": "First paragraph with some text content here.",
                    "attributes": {},
                    "children": [],
                }
            ],
        },
    }
