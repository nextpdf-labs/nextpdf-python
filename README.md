# nextpdf

**Citation-ready PDF extraction for Python.**

Extract text, tables, and semantic structure from any PDF.
Every extracted block carries a citation anchor with page index, confidence score, and optional bounding box.

AI-agent-native. Pure Python. MIT licensed.

[![PyPI version](https://badge.fury.io/py/nextpdf.svg)](https://pypi.org/project/nextpdf/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![mypy: strict](https://img.shields.io/badge/mypy-strict-brightgreen.svg)](http://mypy-lang.org/)

---

## Install

```bash
pip install nextpdf
```

Requires Python 3.10+. Dependencies: `httpx`, `pydantic >= 2.0`, `anyio >= 4.0`, `click >= 8.0`, `pypdf >= 4.0`.

For MCP server support (AI agent integration):

```bash
pip install nextpdf[mcp]
```

---

## Quick Start

Connect to a NextPDF Connect server (self-hosted or hosted):

```python
from nextpdf import NextPDF

client = NextPDF(base_url="http://localhost:8080", api_key="your-key")

with open("document.pdf", "rb") as f:
    blocks = client.ast.extract_cited_text(f.read())

for block in blocks:
    page = block.citation.page_index
    conf = block.citation.confidence
    print(f"[page {page}, confidence {conf:.2f}] {block.text[:100]}")
```

**Large files:** For PDFs over 100 MB, use the CLI (`nextpdf extract text`) which streams output and avoids loading full results into memory at once.

---

## CLI Quick Start

The `nextpdf` command provides PDF extraction directly from the terminal:

```bash
# Extract text as JSON
nextpdf extract text document.pdf --base-url http://localhost:8080 --api-key your-key

# Extract tables as CSV
nextpdf extract tables invoice.pdf --format csv --base-url http://localhost:8080 --api-key your-key

# Get document info (page count, structure summary)
nextpdf info document.pdf --base-url http://localhost:8080 --api-key your-key

# Get the full semantic AST
nextpdf ast document.pdf --base-url http://localhost:8080 --api-key your-key

# Check SDK version (no server required)
nextpdf version
```

You can also set environment variables to avoid repeating connection details:

```bash
export NEXTPDF_BASE_URL=http://localhost:8080
export NEXTPDF_API_KEY=your-key
nextpdf extract text document.pdf
```

---

## Use with Claude Code (MCP)

nextpdf ships an MCP server that gives AI agents (Claude Code, etc.) native PDF extraction tools.

**Setup:**

Add to your Claude Code MCP config:

```json
{
  "mcpServers": {
    "nextpdf": {
      "command": "python",
      "args": ["-m", "nextpdf.mcp"],
      "env": {
        "NEXTPDF_BASE_URL": "http://localhost:8080",
        "NEXTPDF_API_KEY": "your-key"
      }
    }
  }
}
```

Once configured, Claude Code can call tools like `nextpdf_extract_text`, `nextpdf_extract_tables`, `nextpdf_get_ast`, `nextpdf_search`, `nextpdf_get_outline`, `nextpdf_diff`, and `nextpdf_info` directly during conversations.

---

## Features

| Feature | Remote (NextPDF Connect) | Local (pypdf, beta) |
|---------|:---:|:---:|
| Semantic AST extraction (tagged PDFs) | Yes | Yes |
| Citation anchors (page + bbox + node ID) | Yes | Yes (no bbox for local) |
| Cited text extraction | Yes | Yes |
| Cited table extraction | Yes | Yes (tagged PDFs only) |
| Heuristic fallback for untagged PDFs | Yes | Yes (confidence 0.5) |
| Node search by type, page, text | Yes | Yes |
| Single-node subtree fetch | Yes | Yes |
| AST diff between two PDFs | Yes | Yes |
| CJK document support | Yes | Depends on PDF encoding |
| Async client (`AsyncNextPDF`) | Yes | Yes |
| CLI tool (`nextpdf` command) | Yes | -- |
| MCP server for AI agents | Yes | -- |

---

## Backends

nextpdf supports two extraction backends:

### Remote Backend (default)

Sends PDF bytes to a NextPDF Connect server over HTTP. This is the mature, recommended path for production use.

```python
from nextpdf import NextPDF

# Connects to NextPDF Connect server
client = NextPDF(base_url="http://localhost:8080", api_key="your-key")
```

Run your own server:

```bash
docker run -p 8080:8080 nextpdf/connect:latest
```

### Local Backend (beta)

Uses `pypdf` for offline extraction directly in your Python process. No remote server required. Currently in beta -- works well for tagged PDFs but has limitations with complex layouts and untagged documents.

```python
from nextpdf import AsyncNextPDF
from nextpdf.backends.local import LocalBackend

backend = LocalBackend()
client = AsyncNextPDF(backend=backend)

with open("document.pdf", "rb") as f:
    blocks = await client.ast.extract_cited_text(f.read())
```

**Local backend limitations:**
- No bounding box coordinates (bbox is always a full-page placeholder)
- Heuristic mode for untagged PDFs produces paragraph-level splits at confidence 0.5
- Table extraction only works on tagged PDFs with explicit StructTree table elements
- Text extraction quality depends on pypdf's text layout engine

---

## When to Use nextpdf vs Alternatives

| Need | nextpdf | pypdf | pdfplumber | pymupdf |
|------|---------|-------|------------|---------|
| Citation anchors (page + bbox + node ID) | Yes -- every block | No | Manual work | Manual work |
| Semantic AST (headings, sections, lists) | Yes -- from PDF StructTree | No | No | Partial |
| AI agent integration (MCP, structured output) | Built-in | No | No | No |
| Table extraction with citations | Yes | No | Yes (no citations) | Yes (no citations) |
| No server required | Beta (local backend) | Yes | Yes | Yes |
| OCR / scanned PDFs | No | No | No | Yes (via Tesseract) |
| License | MIT | BSD | MIT | AGPL |

**Use nextpdf when** you need citation-tracked, structured extraction for AI pipelines, RAG systems, or document analysis where provenance matters.

**Use alternatives when** you need OCR for scanned documents, pixel-level rendering, or you only need raw text without structure.

---

## Limitations

- **No OCR.** nextpdf does not handle scanned/image-only PDFs. Text must be embedded in the PDF.
- **Untagged PDFs produce lower confidence results.** When a PDF has no StructTree, the heuristic fallback splits text into paragraphs with confidence 0.5. Headings, lists, and tables are not detected in heuristic mode.
- **Complex layouts.** Multi-column layouts, overlapping text boxes, and non-standard PDF producers may yield incomplete or misordered text.
- **No bounding boxes in local backend.** The local (pypdf) backend cannot extract precise bounding box coordinates. Citation anchors use full-page placeholders.
- **Remote backend requires a server.** The default remote backend requires a running NextPDF Connect server (self-hosted or hosted).
- **Platform testing.** Tested on Linux. Pure Python, should work on Windows/macOS but not extensively tested on those platforms.

---

## Async Usage

The `AsyncNextPDF` client uses `httpx.AsyncClient` internally with connection pooling. It is safe for use with `asyncio`, FastAPI, and any async framework:

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
        print(f"  {len(r)} blocks")

asyncio.run(process_documents(["doc1.pdf", "doc2.pdf"]))
```

The sync `NextPDF` client wraps the async client and is event-loop-safe (works in Jupyter notebooks and FastAPI).

---

## Error Handling

```python
from nextpdf import NextPDF
from nextpdf.models.errors import NextPDFError, NextPDFAPIError, QuotaExceededError

client = NextPDF(base_url="http://localhost:8080", api_key="your-key")

try:
    with open("document.pdf", "rb") as f:
        blocks = client.ast.extract_cited_text(f.read())
except QuotaExceededError as e:
    print(f"Rate limit hit (HTTP {e.status_code}): {e}")
except NextPDFAPIError as e:
    print(f"API error {e.status_code}: {e}")
except NextPDFError as e:
    print(f"SDK error: {e}")
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, and PR guidelines.

---

## License

MIT. See [LICENSE](LICENSE) for the full text.

---

## Links

- GitHub: [https://github.com/nextpdf-labs/nextpdf-python](https://github.com/nextpdf-labs/nextpdf-python)
- PyPI: [https://pypi.org/project/nextpdf/](https://pypi.org/project/nextpdf/)
- Documentation: [https://nextpdf.dev/docs/python](https://nextpdf.dev/docs/python)
