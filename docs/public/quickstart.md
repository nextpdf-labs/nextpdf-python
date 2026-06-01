---
title: "Python SDK quickstart"
summary: "Install the NextPDF Python SDK, connect it to a NextPDF Connect endpoint, and extract cited text from a PDF with page-level provenance."
stability: stable
since: "1.0.0"
deprecated_since: ""
replaced_by: ""
edition: core
audience: [newcomer]
mode: tutorial
version_lifecycle: active
eol_date: ""
prerequisites: ["Python 3.10 or newer", "A running NextPDF Connect server", "An API key if the endpoint requires authentication"]
related: ["/python/overview/", "/python/cli/", "/python/mcp/"]
citations: []
runnable_example: ""
reproducibility_profile: semantic
output_hash: ""
performance_budget: { wall_ms: 1000, peak_mb: 128 }
compatibility: ["8.4"]
commercial_context:
  core_alternative: ""
  premium_advantage: ""
  conversion_link: ""
source_repo: nextpdf-python
source_ref: main
source_hash: ""
manifest_hash: ""
export_control_class: none
last_reviewed: "2026-05-27"
reviewer: "@nextpdf-docs-team"
publish: false
gated: false
inclusive_language_checked: true
i18n_ready: true
xliff_segments: 0
---

# Python SDK quickstart

Install the SDK from PyPI:

```bash
pip install nextpdf
```

Create a client that points to your NextPDF Connect endpoint:

```python
from nextpdf import NextPDF

client = NextPDF(base_url="http://localhost:8080", api_key="your-key")

with open("document.pdf", "rb") as file:
    blocks = client.ast.extract_cited_text(file.read())

for block in blocks:
    page = block.citation.page_index
    confidence = block.citation.confidence
    print(f"[page {page}, confidence {confidence:.2f}] {block.text[:100]}")
```

If your endpoint does not require an API key, omit `api_key`.

## Use environment variables

The CLI and agent workflows can read connection settings from the environment:

```bash
export NEXTPDF_BASE_URL=http://localhost:8080
export NEXTPDF_API_KEY=your-key
```

On Windows PowerShell:

```powershell
$env:NEXTPDF_BASE_URL = "http://localhost:8080"
$env:NEXTPDF_API_KEY = "your-key"
```

## Handle common errors

Catch SDK and API exceptions around extraction calls:

```python
from nextpdf import NextPDF
from nextpdf.models.errors import NextPDFAPIError, NextPDFError, QuotaExceededError

client = NextPDF(base_url="http://localhost:8080", api_key="your-key")

try:
    with open("document.pdf", "rb") as file:
        blocks = client.ast.extract_cited_text(file.read())
except QuotaExceededError as error:
    print(f"Rate limit hit: {error}")
except NextPDFAPIError as error:
    print(f"API error {error.status_code}: {error}")
except NextPDFError as error:
    print(f"SDK error: {error}")
```

Use the CLI for PDFs over 100 MB so results can stream without loading every extracted block into memory at once.
