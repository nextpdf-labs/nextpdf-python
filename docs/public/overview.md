---
title: "Python SDK overview"
summary: "Use the NextPDF Python SDK when a Python application needs citation-ready PDF extraction, semantic document structure, or AI-agent tools backed by NextPDF Connect."
stability: stable
since: "1.0.0"
deprecated_since: ""
replaced_by: ""
edition: core
audience: [newcomer, senior]
mode: explanation
version_lifecycle: active
eol_date: ""
prerequisites: ["Python 3.10 or newer", "A NextPDF Connect endpoint for production extraction"]
related: ["/python/quickstart/", "/python/cli/", "/python/mcp/"]
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

# Python SDK overview

The NextPDF Python SDK is for Python applications that need PDF extraction with provenance. It returns structured blocks with citation anchors such as page index, confidence, optional bounding boxes, and semantic node identifiers when the source PDF exposes that structure.

Use the SDK when your pipeline needs to answer questions like "which page did this text come from?", "which table supports this value?", or "what changed between these two PDFs?" without treating PDF extraction as anonymous plain text.

## What it provides

- A synchronous `NextPDF` client for scripts, batch jobs, and notebooks.
- An asynchronous `AsyncNextPDF` client for `asyncio`, FastAPI, and other async runtimes.
- A command-line interface for streaming extraction results from large files.
- An optional MCP server so AI agents can call PDF extraction tools directly.
- A remote backend for production use with NextPDF Connect.
- A local beta backend for offline extraction through `pypdf`.

## Backend choices

The remote backend sends PDF bytes to a NextPDF Connect server. This is the recommended production path because it centralizes extraction behavior, authentication, quotas, and operational controls.

The local backend runs inside the Python process. It is useful for offline tests and tagged PDFs, but it cannot provide precise bounding boxes and uses heuristic paragraph-level extraction for untagged PDFs.

## Limitations

The SDK does not perform OCR. Scanned or image-only PDFs need an OCR step before NextPDF can extract embedded text. Complex layouts, overlapping text, and unusual PDF producers can also reduce extraction quality.

For very large PDFs, prefer the CLI workflow because it streams output and avoids materializing the full result set in memory.
