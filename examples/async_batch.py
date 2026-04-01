"""Process multiple PDFs concurrently with the async client.

Usage:
    python async_batch.py doc1.pdf doc2.pdf doc3.pdf

Requires NEXTPDF_BASE_URL and NEXTPDF_API_KEY environment variables.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from nextpdf import AsyncNextPDF
from nextpdf.models.errors import NextPDFError


async def extract_one(
    client: AsyncNextPDF,
    pdf_path: str,
) -> tuple[str, int]:
    """Extract text from a single PDF and return (filename, block_count)."""
    with open(pdf_path, "rb") as f:
        pdf_data = f.read()
    blocks = await client.ast.extract_cited_text(pdf_data)
    return Path(pdf_path).name, len(blocks)


async def main(pdf_paths: list[str]) -> None:
    base_url = os.environ.get("NEXTPDF_BASE_URL", "http://localhost:8080")
    api_key = os.environ.get("NEXTPDF_API_KEY", "your-key")

    async with AsyncNextPDF(base_url=base_url, api_key=api_key) as client:
        tasks = [extract_one(client, path) for path in pdf_paths]

        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        except NextPDFError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    print(f"Processed {len(results)} PDF(s):\n")
    for result in results:
        if isinstance(result, Exception):
            print(f"  ERROR: {result}")
        else:
            name, count = result
            print(f"  {name}: {count} text block(s)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python async_batch.py <pdf1> <pdf2> ...")
        sys.exit(1)
    asyncio.run(main(sys.argv[1:]))
