"""Extract text with citations from a PDF.

Usage:
    python basic_extract_text.py document.pdf

Requires NEXTPDF_BASE_URL and NEXTPDF_API_KEY environment variables,
or pass --base-url and --api-key as arguments.
"""
from __future__ import annotations

import os
import sys

from nextpdf import NextPDF
from nextpdf.models.errors import NextPDFError


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python basic_extract_text.py <pdf_path>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    base_url = os.environ.get("NEXTPDF_BASE_URL", "http://localhost:8080")
    api_key = os.environ.get("NEXTPDF_API_KEY", "your-key")

    client = NextPDF(base_url=base_url, api_key=api_key)

    try:
        with open(pdf_path, "rb") as f:
            blocks = client.ast.extract_cited_text(f.read())
    except NextPDFError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Extracted {len(blocks)} text block(s)\n")

    for block in blocks:
        page = block.citation.page_index
        conf = block.citation.confidence
        node_id = block.citation.node_id
        print(f"[page {page}, confidence {conf:.2f}, node {node_id}]")
        print(f"  {block.text[:200]}")
        if block.citation.bbox:
            b = block.citation.bbox
            print(f"  bbox: ({b.x:.4f}, {b.y:.4f}, {b.width:.4f}, {b.height:.4f})")
        print()


if __name__ == "__main__":
    main()
