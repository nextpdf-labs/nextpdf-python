"""Extract tables with citations from a PDF.

Usage:
    python basic_extract_tables.py document.pdf

Requires NEXTPDF_BASE_URL and NEXTPDF_API_KEY environment variables.
"""
from __future__ import annotations

import os
import sys

from nextpdf import NextPDF
from nextpdf.models.errors import NextPDFError


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python basic_extract_tables.py <pdf_path>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    base_url = os.environ.get("NEXTPDF_BASE_URL", "http://localhost:8080")
    api_key = os.environ.get("NEXTPDF_API_KEY", "your-key")

    client = NextPDF(base_url=base_url, api_key=api_key)

    try:
        with open(pdf_path, "rb") as f:
            result = client.ast.extract_cited_tables(f.read())
    except NextPDFError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Found {result.table_count} table(s)\n")

    for i, table in enumerate(result.tables):
        print(f"--- Table {i + 1} (page {table.page_index}) ---")
        print(f"    {table.row_count} rows x {table.col_count} columns")

        for row in table.rows:
            cells_text = [cell.text or "" for cell in row]
            print(f"    | {' | '.join(cells_text)} |")

        if table.citation_anchor:
            anchor = table.citation_anchor
            print(f"    Citation: node={anchor.node_id}, confidence={anchor.confidence:.2f}")
        print()


if __name__ == "__main__":
    main()
