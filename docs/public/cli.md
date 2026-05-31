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
last_reviewed: "2026-05-31"
reviewer: "@nextpdf-docs-team"
publish: false
gated: false
inclusive_language_checked: true
i18n_ready: true
xliff_segments: 0
---

# Python CLI

The `nextpdf` command runs PDF extraction from the terminal. You point it at a NextPDF Connect endpoint, pass a PDF, and receive structured output — cited text, tables, the full semantic Abstract Syntax Tree (AST), or a metadata summary — on standard output (stdout) or in a file.

## Command structure

The `nextpdf` command is a Click command group. Connection and session options — `--base-url`, `--api-key`, `--log-level`, `--output`/`-o`, and `--strict` — are defined on the **group**, so you place them **before** the subcommand. The subcommand and its own options (such as `--format` or `--page`) come **after**:

```text
nextpdf [GROUP OPTIONS] COMMAND [SUBCOMMAND] PDF_PATH [COMMAND OPTIONS]
```

Putting a group option after the subcommand fails. For example, `nextpdf info document.pdf --base-url ...` reports `Error: No such option: --base-url` and exits with status 2, because by the time Click parses `--base-url` it is already inside the `info` subcommand, which does not define that option.

The clearest way to avoid the ordering trap is to supply credentials through environment variables (see [Configure once per shell](#configure-once-per-shell)). The examples below show the explicit-flag form first so the correct order is unambiguous.

## Quick reference

Extract text as JSON:

```bash
nextpdf --base-url http://localhost:8080 --api-key "$NEXTPDF_API_KEY" extract text document.pdf
```

Extract tables as comma-separated values (CSV):

```bash
nextpdf --base-url http://localhost:8080 --api-key "$NEXTPDF_API_KEY" extract tables invoice.pdf --format csv
```

Inspect document metadata and structure:

```bash
nextpdf --base-url http://localhost:8080 --api-key "$NEXTPDF_API_KEY" info document.pdf
```

Get the full semantic AST:

```bash
nextpdf --base-url http://localhost:8080 --api-key "$NEXTPDF_API_KEY" ast document.pdf
```

Print the installed SDK version without contacting a server:

```bash
nextpdf version
```

The `version` command is the one command that needs neither `--base-url` nor `--api-key`. Every other command contacts the server and requires both.

Each example reads the API key from the `NEXTPDF_API_KEY` environment variable rather than embedding it on the command line. Treat the key as a secret: a literal key on the command line is visible in your shell history and in the process list (`ps`) to other users on the host.

## Commands and options

### Group options

You place these before the subcommand. Each connection option also reads from an environment variable, so you can omit the flag when the variable is set.

| Option | Environment variable | Default | Purpose |
| --- | --- | --- | --- |
| `--base-url` | `NEXTPDF_BASE_URL` | (required) | NextPDF Connect server URL. |
| `--api-key` | `NEXTPDF_API_KEY` | (required) | API key for bearer authentication. |
| `--log-level` | — | `warning` | Logging verbosity: `debug`, `info`, `warning`, or `error`. Logs go to standard error (stderr). |
| `--output`, `-o` | — | stdout | Write command output to a file instead of stdout. |
| `--strict` | — | off | Reserved for future use. The flag parses today but does not change behavior. |
| `--help`, `-h` | — | — | Show help and exit. |

The `--base-url` and `--api-key` values are required for every command except `version`. If either is missing — no flag and no environment variable — the command prints an error and exits with status 1.

### `nextpdf extract text`

Extract cited text blocks. Each block carries a citation anchor (node identifier, page index, bounding box, and a confidence score).

```text
nextpdf [GROUP OPTIONS] extract text PDF_PATH [--format FORMAT] [--page N] [--headings-only]
```

| Option | Values | Default | Purpose |
| --- | --- | --- | --- |
| `--format` | `json`, `markdown`, `plain` | `json` | Output format. |
| `--page` | integer | all pages | Extract only this 0-based page index. |
| `--headings-only` | flag | off | Extract only heading nodes. |

`PDF_PATH` is a file path, or `-` to read PDF bytes from stdin.

### `nextpdf extract tables`

Extract every table with citation anchors and cell-level structure.

```text
nextpdf [GROUP OPTIONS] extract tables PDF_PATH [--format FORMAT] [--page-start N] [--page-end N]
```

| Option | Values | Default | Purpose |
| --- | --- | --- | --- |
| `--format` | `json`, `csv` | `json` | Output format. |
| `--page-start` | integer | first page | Start page index (0-based). |
| `--page-end` | integer | last page | End page index (0-based). |

`PDF_PATH` is a file path, or `-` to read from stdin.

### `nextpdf ast`

Return the full semantic AST as JSON: a hierarchical tree of nodes (headings, paragraphs, tables, lists, figures) with bounding boxes and text content.

```text
nextpdf [GROUP OPTIONS] ast PDF_PATH [--page-start N] [--page-end N] [--token-budget N]
```

| Option | Values | Default | Purpose |
| --- | --- | --- | --- |
| `--page-start` | integer | first page | Start page index (0-based). |
| `--page-end` | integer | last page | End page index (0-based). |
| `--token-budget` | integer | unbounded | Approximate token limit for the returned AST. |

`PDF_PATH` is a file path, or `-` to read from stdin. The `ast` command produces a single document tree; it does not compare two PDFs. For structural diffing, see [Recipe: diff two PDF revisions](#recipe-diff-two-pdf-revisions).

### `nextpdf info`

Print a compact JSON summary of one document: schema version, source hash, page count, estimated token count, the root node type, and the number of root children.

```text
nextpdf [GROUP OPTIONS] info PDF_PATH
```

`PDF_PATH` is a file path, or `-` to read from stdin.

### `nextpdf version`

Print the installed SDK version (for example, `nextpdf 1.1.0`) and exit. This command contacts no server and needs no credentials.

```text
nextpdf version
```

## Configure once per shell

Set the connection options once as environment variables and omit the repeated flags. This form also avoids the option-ordering trap entirely, because the credentials never appear on the command line.

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

Prefer loading the key from a secret store or a `.env` file that you keep out of version control. Do not paste a production key into a shared terminal session or a script that you commit.

## Output formats

You select the output format per command with `--format`. The text and table commands support more than one format; `ast` and `info` always emit JSON.

| Command | Formats | Default |
| --- | --- | --- |
| `extract text` | `json`, `markdown`, `plain` | `json` |
| `extract tables` | `json`, `csv` | `json` |
| `ast` | `json` | `json` |
| `info` | `json` | `json` |

Choose JSON when a downstream program needs page indexes, confidence scores, or node identifiers. Choose CSV when a spreadsheet or a tabular pipeline consumes the tables. Choose `plain` or `markdown` text when a person, or a text-only tool, reads the result.

### Parsing JSON output

The text command emits a JSON array of cited blocks. Each block has `text`, a `citation` object (`node_id`, `page_index`, `bbox`, `confidence`), and an optional `node_type`. Send the output to a file with `--output` (or redirect stdout), then parse it.

This shell example uses `jq` to keep only headings on page 0:

```bash
nextpdf --output blocks.json extract text report.pdf --format json
jq '[.[] | select(.citation.page_index == 0 and .node_type == "heading") | .text]' blocks.json
```

The same data parses cleanly in Python. The CLI writes a JSON array, so you load it with the standard library and read the typed fields:

```python
"""Parse cited text blocks emitted by `nextpdf extract text --format json`."""

import json
from pathlib import Path


def load_headings(blocks_path: Path) -> list[str]:
    """Return the text of every heading block on page 0.

    Args:
        blocks_path: Path to the JSON file written by `nextpdf extract text`.

    Returns:
        The text of each heading-type block whose citation is on page 0.
    """
    raw = blocks_path.read_text(encoding="utf-8")
    blocks: list[dict[str, object]] = json.loads(raw)
    headings: list[str] = []
    for block in blocks:
        citation = block["citation"]
        if block.get("node_type") == "heading" and citation["page_index"] == 0:
            headings.append(str(block["text"]))
    return headings


if __name__ == "__main__":
    for heading in load_headings(Path("blocks.json")):
        print(heading)
```

When you need the validated, typed models rather than raw dictionaries, call the SDK directly instead of parsing CLI output. See the [Python overview](/python/overview/) for the `NextPDF` client and its `CitedTextBlock` return type.

### Parsing CSV output

With `--format csv`, the table command writes one CSV block per table. A comment row, `# Table N (pM)`, precedes each table and names its 1-based table number and 0-based page index; a blank line separates consecutive tables. The CLI quotes and escapes cell values with Python's `csv` module, so values that contain commas, quotes, or newlines round-trip safely.

```bash
nextpdf --output tables.csv extract tables statement.pdf --format csv
```

Because the file holds multiple CSV blocks, split on the comment rows before you parse each block as a standalone table:

```python
"""Split multi-table CSV output from `nextpdf extract tables --format csv`."""

import csv
import io
from pathlib import Path


def read_tables(csv_path: Path) -> list[list[list[str]]]:
    """Parse the multi-block CSV file into a list of tables.

    Each table is a list of rows; each row is a list of cell strings.
    The leading `# Table N (pM)` comment row is dropped from every table.

    Args:
        csv_path: Path to the file written by `nextpdf extract tables`.

    Returns:
        One parsed table per `# Table` block in the file.
    """
    text = csv_path.read_text(encoding="utf-8")
    tables: list[list[list[str]]] = []
    current: list[str] = []
    for line in text.splitlines(keepends=True):
        if line.startswith("# Table ") and current:
            tables.append(_parse_block(current))
            current = []
        current.append(line)
    if current:
        tables.append(_parse_block(current))
    return tables


def _parse_block(lines: list[str]) -> list[list[str]]:
    """Parse one CSV block, discarding its leading comment row."""
    reader = csv.reader(io.StringIO("".join(lines)))
    rows = [row for row in reader if row]
    return rows[1:] if rows and rows[0] and rows[0][0].startswith("# Table ") else rows


if __name__ == "__main__":
    for index, table in enumerate(read_tables(Path("tables.csv")), start=1):
        print(f"table {index}: {len(table)} rows")
```

## Exit codes and error detection

The CLI uses three exit codes. Check `$?` in shell scripts (or `$LASTEXITCODE` in PowerShell) to branch on success or failure, and read diagnostic messages from stderr, which stays separate from the data on stdout.

| Exit code | Meaning | Examples |
| --- | --- | --- |
| `0` | Success. | A command completed; `version` printed. |
| `1` | Runtime error. The CLI prints `Error: <message>` to stderr. | Input file not found or not a regular file, empty stdin, missing or invalid `--base-url`/`--api-key`, any server-side error (license required, quota exceeded, untagged PDF, build timeout, or other API failure). |
| `2` | Usage error, reported by Click. | Unknown command or option (including a group option placed after the subcommand), a missing required argument such as `PDF_PATH`. |

Every server-side failure surfaces as exit code 1 with a human-readable message on stderr. The SDK raises a typed exception — `NextPDFLicenseError` (HTTP 402), `QuotaExceededError` (HTTP 429), `AstNoStructTreeError` (HTTP 422, untagged PDF), `AstBuildTimeoutError` (HTTP 504), or the base `NextPDFAPIError` — and the CLI catches all of them under their shared `NextPDFError` base, printing the message and exiting 1. The CLI does not expose distinct exit codes per failure type, so to distinguish, for example, a quota error from a license error in a script, inspect the message text on stderr or call the SDK directly (see the [Python overview](/python/overview/) for the exception classes).

A scripting pattern that separates data from diagnostics:

```bash
#!/usr/bin/env bash
set -euo pipefail

# Credentials come from the environment, not the command line.
: "${NEXTPDF_BASE_URL:?set NEXTPDF_BASE_URL}"
: "${NEXTPDF_API_KEY:?set NEXTPDF_API_KEY}"

if nextpdf --output contract.ast.json ast contract.pdf; then
  echo "AST written to contract.ast.json"
else
  status=$?
  echo "nextpdf failed with exit code ${status}" >&2
  exit "${status}"
fi
```

Note that `--output` writes data to the named file and prints only the confirmation line `Written to <path>` to stderr, so stdout stays empty. Without `--output`, the data goes to stdout and you can redirect it.

## Recipes

Every recipe below uses only verified commands and flags. Credentials come from the environment in each case.

### Recipe: extract invoice tables to CSV

Turn a folder of invoices into one CSV file per document for a spreadsheet or accounting pipeline:

```bash
#!/usr/bin/env bash
set -euo pipefail

: "${NEXTPDF_BASE_URL:?set NEXTPDF_BASE_URL}"
: "${NEXTPDF_API_KEY:?set NEXTPDF_API_KEY}"

mkdir -p out
for pdf in invoices/*.pdf; do
  name="$(basename "${pdf}" .pdf)"
  nextpdf --output "out/${name}.csv" extract tables "${pdf}" --format csv
done
```

Each `out/<name>.csv` holds one CSV block per detected table, with a `# Table N (pM)` header preceding each. Parse the blocks with the [CSV reader shown above](#parsing-csv-output).

### Recipe: build a document outline

Combine `--headings-only` with the `markdown` format to produce a quick outline you can read or paste into notes:

```bash
nextpdf --output outline.md extract text whitepaper.pdf --headings-only --format markdown
```

### Recipe: diff two PDF revisions

The CLI's `ast` command returns the tree for a single document; it has no diff subcommand. Structural diffing lives in the SDK as `client.ast.get_ast_diff(...)` and in the Model Context Protocol (MCP) server as the `nextpdf_diff` tool. Run the diff through the SDK:

```python
"""Compare two PDF revisions structurally with the NextPDF SDK.

The API key is read from the environment, never hard-coded.
"""

import os
from pathlib import Path

from nextpdf import NextPDF


def diff_revisions(original: Path, modified: Path) -> None:
    """Print a structural diff summary between two PDF revisions.

    Args:
        original: Path to the earlier PDF revision.
        modified: Path to the later PDF revision.
    """
    base_url = os.environ["NEXTPDF_BASE_URL"]
    api_key = os.environ["NEXTPDF_API_KEY"]

    client = NextPDF(base_url=base_url, api_key=api_key)
    result = client.ast.get_ast_diff(
        original.read_bytes(),
        modified.read_bytes(),
    )

    summary = result.summary
    print(f"added:   {summary.added_node_count}")
    print(f"removed: {summary.removed_node_count}")
    print(f"changed: {summary.changed_node_count}")
    for entry in result.diff:
        preview = entry.text_preview or ""
        print(f"  {entry.type:<8} {entry.node_type:<12} p{entry.page_index} {preview}")


if __name__ == "__main__":
    diff_revisions(Path("contract-v1.pdf"), Path("contract-v2.pdf"))
```

To run the same diff from an AI agent rather than a script, register the MCP server and call the `nextpdf_diff` tool. See the [Python MCP server](/python/mcp/) page.

### Recipe: stream a PDF in from another tool

Read PDF bytes from stdin with `-` to chain `nextpdf` after a tool that emits a PDF on its own stdout:

```bash
curl --silent https://example.com/report.pdf | nextpdf info -
```

The `-` argument tells the command to read the document from stdin. If no bytes arrive, the command reports an error and exits 1.

## Performance notes

The CLI builds each response in memory and writes it once, so redirecting or piping output is straightforward, but the output is not produced incrementally — a large AST or table set is fully buffered before the first byte reaches stdout or the `--output` file. Plan memory and latency for whole-document responses, not for a stream.

Each `nextpdf` invocation creates a fresh client and HTTP connection, so a loop over many files opens and closes a connection per file. The connection cost is usually small next to server-side extraction time, but it is real overhead at scale.

- **Reuse one endpoint.** Point every invocation at the same NextPDF Connect deployment so the server reuses warmed caches and connection pools. Avoid spreading a batch across endpoints unless you are load-balancing on purpose.
- **Bound the work per call.** Use `--page`, `--page-start`/`--page-end`, or `--token-budget` to process only the pages you need. Smaller page ranges reduce both server time and response size; `--token-budget` caps the AST your agent has to read.
- **Batch in one process for large jobs.** For high-volume batches, prefer the Python SDK over repeated CLI calls: a single long-lived `NextPDF` (or `AsyncNextPDF`) client reuses one pooled HTTP connection across every document, which removes the per-process startup and connection setup that a CLI loop pays each time. The [Python overview](/python/overview/) shows the client lifecycle, and `AsyncNextPDF` supports concurrent extraction across many PDFs.
- **Keep logs out of the data path.** Leave `--log-level` at its default for batch runs. Diagnostic logs go to stderr and do not corrupt stdout data, but raising the level to `debug` adds noise and minor overhead.
