# nextpdf

[![PyPI version](https://badge.fury.io/py/nextpdf.svg)](https://pypi.org/project/nextpdf/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![mypy: strict](https://img.shields.io/badge/mypy-strict-brightgreen.svg)](http://mypy-lang.org/)

**The PDF Runtime for AI Agents**

Extract structured, citation-ready content from any PDF. Every text block and table cell carries a verifiable citation anchor: page index, bounding box, node ID, and confidence score.

---

## Install

```bash
pip install nextpdf
```

Requires Python 3.10+. No C extensions. Depends on `httpx` and `pydantic >= 2.0`.

Connect to a NextPDF Connect Server (self-hosted via Docker or hosted API):

```bash
docker run -p 8080:8080 nextpdf/connect:latest
```

---

## Quick Examples

### Get the Semantic AST

```python
from nextpdf import NextPDF

client = NextPDF(base_url="http://localhost:8080", api_key="your-key")

with open("report.pdf", "rb") as f:
    result = client.ast.get_document_ast(f.read())

print(f"Pages: {result.ast.page_count}, Nodes: {result.ast.node_count}")
print(f"Schema: {result.ast.schema_version}")
print(f"ETag:   {result.meta.etag}")  # use as a cache key
```

### Extract Cited Text

```python
from nextpdf import NextPDF

client = NextPDF(base_url="http://localhost:8080", api_key="your-key")

with open("contract.pdf", "rb") as f:
    result = client.ast.extract_cited_text(f.read())

for block in result.blocks:
    page = block.citation.page_index
    node = block.citation.node_id
    conf = block.citation.confidence
    print(f"[page {page}] {block.text[:120]}")
    if block.citation.bbox:
        b = block.citation.bbox
        print(f"  bbox: ({b.x:.4f}, {b.y:.4f}, {b.width:.4f}, {b.height:.4f})")
    print(f"  node: {node}  confidence: {conf:.2f}")
```

### Extract Cited Tables

```python
from nextpdf import NextPDF

client = NextPDF(base_url="http://localhost:8080", api_key="your-key")

with open("invoice.pdf", "rb") as f:
    result = client.ast.extract_cited_tables(f.read())

print(f"Found {result.table_count} table(s)")

for table in result.tables:
    anchor = table.citation_anchor
    print(f"Table on page {anchor.page_index}: {table.row_count}r x {table.col_count}c")
    for row in table.rows:
        for cell in row:
            if cell.text:
                print(f"  [{cell.row},{cell.col}] {cell.text}")
```

---

## Features

| Feature | Status |
|---------|--------|
| Semantic AST extraction (tagged PDFs) | Available |
| Citation anchors (page + bbox + node ID) | Available |
| Cited text extraction | Available |
| Cited table extraction | Available |
| Node search by type, page, text | Available |
| Single-node subtree fetch | Available |
| Untagged PDF fallback (confidence 0.3) | Available |
| CJK document support (zh-TW, zh-CN, ja, ko) | Available |
| Async client (`AsyncNextPDF`) | Available |
| Token budget / large document pagination | Available (Pro) |
| Async jobs for large PDFs (>50 pages) | Available (Pro) |
| Round-trip PDF mutation | Phase 2b |
| HeuristicAstBuilder for untagged PDFs | Phase 2a |
| LangChain `DocumentLoader` | Prototype available |

---

## Async Usage

The `AsyncNextPDF` client uses `httpx.AsyncClient` internally and is safe for use with `asyncio`, FastAPI, and any async framework:

```python
import asyncio
from nextpdf import AsyncNextPDF

async def process_documents(paths: list[str]) -> None:
    client = AsyncNextPDF(base_url="http://localhost:8080", api_key="your-key")
    tasks = []
    for path in paths:
        with open(path, "rb") as f:
            tasks.append(client.ast.extract_cited_text(f.read()))
    results = await asyncio.gather(*tasks)
    for r in results:
        print(f"  {r.total_blocks} blocks")

asyncio.run(process_documents(["doc1.pdf", "doc2.pdf"]))
```

---

## Connect to Your Own Server

```python
from nextpdf import NextPDF

# Default: localhost
client = NextPDF(base_url="http://localhost:8080", api_key="your-key")

# Self-hosted production server
client = NextPDF(base_url="https://pdf.yourcompany.internal", api_key="your-key")

# Custom timeout (seconds)
client = NextPDF(
    base_url="http://localhost:8080",
    api_key="your-key",
    timeout=60.0,
)
```

---

## Error Handling

```python
from nextpdf import NextPDF
from nextpdf.errors import NextPDFError, NextPDFLicenseError, QuotaExceededError

client = NextPDF(base_url="http://localhost:8080", api_key="your-key")

try:
    with open("document.pdf", "rb") as f:
        result = client.ast.get_document_ast(f.read())
except NextPDFLicenseError as e:
    # Pro feature accessed without Pro license
    print(f"License required: {e.upgrade_url}")
except QuotaExceededError as e:
    # Daily page quota exceeded on hosted tier
    print(f"Quota exceeded: {e.pricing_url}")
except NextPDFError as e:
    print(f"Error {e.code}: {e.message}")
```

---

## Free Tier

- 1,000 pages per day
- No credit card required
- MIT license — use in any project

Upgrade to Pro for: async job processing for large PDFs, token budget control, heuristic AST for untagged PDFs, and higher daily volume.

---

## Links

- GitHub: [https://github.com/nextpdf-labs/nextpdf](https://github.com/nextpdf-labs/nextpdf)
- PyPI: [https://pypi.org/project/nextpdf/](https://pypi.org/project/nextpdf/)
- Documentation: [https://nextpdf.dev/docs](https://nextpdf.dev/docs)
- Discord: [https://discord.gg/nextpdf](https://discord.gg/nextpdf)
- MCP Registry: search "NextPDF Connect"
