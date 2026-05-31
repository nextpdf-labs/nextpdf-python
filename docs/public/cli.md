---
title: "Python CLI"
summary: "Run citation-aware PDF extraction from the terminal with the NextPDF Python command-line interface."
stability: stable
since: "1.0.0"
deprecated_since: ""
replaced_by: ""
edition: core
audience: [newcomer, senior]
mode: how-to
version_lifecycle: active
eol_date: ""
prerequisites: ["Python 3.10 or newer", "The nextpdf package installed", "A NextPDF Connect endpoint for remote extraction"]
related: ["/python/overview/", "/python/quickstart/", "/python/mcp/"]
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

# Python CLI

The `nextpdf` command provides PDF extraction from the terminal. It is the preferred interface for large documents because command output can be streamed and redirected.

Extract text as JSON:

```bash
nextpdf extract text document.pdf --base-url http://localhost:8080 --api-key your-key
```

Extract tables as CSV:

```bash
nextpdf extract tables invoice.pdf --format csv --base-url http://localhost:8080 --api-key your-key
```

Inspect document metadata and structure:

```bash
nextpdf info document.pdf --base-url http://localhost:8080 --api-key your-key
```

Get the full semantic AST:

```bash
nextpdf ast document.pdf --base-url http://localhost:8080 --api-key your-key
```

Print the installed SDK version without contacting a server:

```bash
nextpdf version
```

## Configure once per shell

Set connection settings once and omit repeated flags:

```bash
export NEXTPDF_BASE_URL=http://localhost:8080
export NEXTPDF_API_KEY=your-key
nextpdf extract text document.pdf
```

On Windows PowerShell:

```powershell
$env:NEXTPDF_BASE_URL = "http://localhost:8080"
$env:NEXTPDF_API_KEY = "your-key"
nextpdf extract text document.pdf
```

## Output shape

Text extraction emits blocks with citation metadata. Table extraction can emit structured formats such as JSON or CSV depending on the command options. Use JSON when downstream tools need page indexes, confidence scores, or semantic anchors.
