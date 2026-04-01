"""Use the local pypdf backend -- no remote server required.

This example demonstrates offline PDF extraction using the local backend.
The local backend is currently in beta and has limitations compared to the
remote backend (see README.md for details).

Usage:
    python local_backend.py document.pdf
"""
from __future__ import annotations

import asyncio
import sys

from nextpdf import AsyncNextPDF
from nextpdf.backends.local import LocalBackend


async def main(pdf_path: str) -> None:
    # Create a local backend -- no server URL or API key needed
    backend = LocalBackend()
    client = AsyncNextPDF(backend=backend)

    with open(pdf_path, "rb") as f:
        pdf_data = f.read()

    # Extract the semantic AST
    doc = await client.ast.get_document_ast(pdf_data)
    print(f"Pages: {doc.page_count}")
    print(f"Schema: {doc.schema_version}")
    print(f"Source hash: {doc.source_hash[:16]}...")
    print()

    # Extract cited text blocks
    blocks = await client.ast.extract_cited_text(pdf_data)
    print(f"Extracted {len(blocks)} text block(s):\n")

    for block in blocks:
        page = block.citation.page_index
        conf = block.citation.confidence
        label = "heuristic" if conf < 1.0 else "tagged"
        print(f"  [page {page}, {label}, confidence {conf:.2f}]")
        print(f"  {block.text[:150]}")
        print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python local_backend.py <pdf_path>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
