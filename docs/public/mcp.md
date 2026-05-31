---
title: "Python MCP server"
summary: "Expose NextPDF PDF extraction tools to MCP-capable AI agents by running the Python SDK's bundled MCP server."
stability: stable
since: "1.0.0"
deprecated_since: ""
replaced_by: ""
edition: core
audience: [senior]
mode: how-to
version_lifecycle: active
eol_date: ""
prerequisites: ["Python 3.10 or newer", "The nextpdf[mcp] extra installed", "A NextPDF Connect endpoint"]
related: ["/python/overview/", "/python/quickstart/", "/python/cli/"]
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

# Python MCP server

The NextPDF Python SDK ships a Model Context Protocol (MCP) server that exposes
PDF extraction operations as native agent tools. An MCP-capable agent — for
example Claude Code — registers the server once and then calls NextPDF tools
the same way it calls any other tool.

The server is a thin adapter. Each tool reads a PDF from local disk, calls the
async client against your NextPDF Connect endpoint, and returns the result as a
JSON string. The server itself holds no business logic and stores no data
between calls.

Install the SDK with the MCP extra:

```bash
pip install nextpdf[mcp]
```

The `mcp` extra adds the upstream `mcp` package (constraint `mcp>=1.0,<2.0`).
The server requires Python 3.10 or newer.

Run the server module from your MCP client configuration. The example below
reads both connection values from the host environment rather than embedding a
secret in the configuration file (see [Security](#security-api-key-scoping-and-least-privilege)):

```json
{
  "mcpServers": {
    "nextpdf": {
      "command": "python",
      "args": ["-m", "nextpdf.mcp"],
      "env": {
        "NEXTPDF_BASE_URL": "https://connect.example.com",
        "NEXTPDF_API_KEY": "${NEXTPDF_API_KEY}"
      }
    }
  }
}
```

The `python -m nextpdf.mcp` entry point runs `main()`, which starts the server
over standard input/output (stdio) via `asyncio.run(serve())`. Do not confuse
this with `python -m nextpdf`, which runs the command-line interface (CLI), not
the MCP server.

`NEXTPDF_BASE_URL` and `NEXTPDF_API_KEY` are both required. The server builds
its client lazily on the first tool call; if either variable is empty it raises
a `RuntimeError` that is returned to the agent as a tool error rather than
crashing the process.

## Tool catalog and SDK mapping

The server registers eight tools. Every tool name carries the `nextpdf_` prefix.
Each one maps to a method on the async client's `ast` namespace
(`AsyncNextPDF.ast`), except for the two composite tools noted below, which are
assembled inside the server from lower-level calls.

| MCP tool | SDK call | Notes |
| --- | --- | --- |
| `nextpdf_extract_text` | `ast.extract_cited_text(pdf_data, page_index=..., headings_only=...)` | Returns a list of `CitedTextBlock`. |
| `nextpdf_extract_tables` | `ast.extract_cited_tables(pdf_data, page_range=...)` | Returns `ExtractCitedTablesResponse`. |
| `nextpdf_get_ast` | `ast.get_document_ast(pdf_data, page_range_start=0, page_range_end=..., token_budget=...)` | Returns `AstDocument`. |
| `nextpdf_info` | `ast.get_document_ast(pdf_data)` | Server projects a metadata summary; no dedicated endpoint. |
| `nextpdf_health` | none | Inspects environment variables only; performs no network call. |
| `nextpdf_search` | `ast.search_ast_nodes(pdf_data, node_type=..., page_index=..., text_query=..., max_results=...)` | Returns `SearchAstNodesResponse`. |
| `nextpdf_get_outline` | `ast.search_ast_nodes(pdf_data, node_type="heading", max_results=500)` | Server reshapes heading nodes into an outline. |
| `nextpdf_diff` | `ast.get_ast_diff(original_pdf_data, modified_pdf_data)` | Returns `GetAstDiffResponse`. |

Tool input notes you should know before wiring an agent:

- All path inputs (`pdf_path`, `original_pdf_path`, `modified_pdf_path`) are
  absolute paths to files **on the machine running the server**. The agent
  passes a path; the server reads the bytes locally. There is no upload tool.
- `nextpdf_extract_text` declares a `max_pages` field in its input schema, but
  the text handler does not pass it to the SDK. Page scoping for text happens
  through `page_index` (a single 0-based page). Use `nextpdf_get_ast` with
  `max_pages` when you need to bound a whole-document walk.
- `nextpdf_get_ast` translates `max_pages` into an inclusive page range of
  `[0, max_pages - 1]` (default `max_pages` is 50). Pass `token_budget` to cap
  the size of the returned tree.
- `nextpdf_info` returns `schema_version`, `source_hash`, `page_count`,
  `estimated_tokens`, `root_node_type`, and `root_children_count`. These come
  from the `AstDocument` model, where `estimated_tokens` is a computed property
  (roughly four characters per token).
- `nextpdf_get_outline` returns one entry per heading with `id`, `page_index`,
  `text`, and `depth` (read from the node's `attributes["level"]`, defaulting
  to 1), plus `heading_count`, `total_matches`, and `truncated`.

The cited-extraction tools attach a `CitationAnchor` to every result. Each
anchor carries `node_id`, `page_index`, a normalized `bbox` (coordinates in the
range 0.0 to 1.0), and a `confidence` score (0.0 to 1.0). Agents that need
provenance should surface these fields rather than the raw text alone.

## Error handling, timeouts, and quota

The server never lets an exception escape to the agent transport. The
`call_tool` dispatcher catches every error and returns it as JSON `TextContent`,
so a failed tool call yields a structured payload the agent can read rather than
a dropped connection. The payload shapes are:

| Condition | Returned JSON |
| --- | --- |
| Unknown tool name | `{"error": "Unknown tool: <name>"}` |
| Missing input file | `{"error": "PDF file not found: <path>"}` |
| Any `NextPDFError` subclass | `{"error": "<message>", "error_type": "<class>", "status_code": <int?>}` |
| Any other exception | `{"error": "Unexpected error: <message>"}` |

`status_code` is included only when the underlying error carries one. The SDK
maps HTTP responses to a typed exception hierarchy, all rooted at `NextPDFError`:

| Exception | HTTP status | `error_code` | When |
| --- | --- | --- | --- |
| `NextPDFLicenseError` | 402 | `license/tier-required` | The endpoint requires a higher server-side license tier for the operation. |
| `AstNoStructTreeError` | 422 | `ast/no-struct-tree` | The PDF is untagged and heuristic fallback is not enabled on the server. |
| `QuotaExceededError` | 429 | `quota/exceeded` | A rate limit or quota was hit. Carries `retry_after` (seconds) when the server sends a `Retry-After` header. |
| `AstBuildTimeoutError` | 504 | `ast/build-timeout` | The AST build exceeded the server's time budget. Reduce the page range. |
| `NextPDFAPIError` | other 4xx/5xx | server-provided | Any other API-level failure. |

Practical guidance for agent integrations:

- **Timeouts.** The HTTP client uses a fixed default timeout — 60 seconds total
  with a 10-second connect timeout. A slow or large document surfaces as either
  an `AstBuildTimeoutError` (the server gave up building the AST) or, if the
  client itself times out, an `Unexpected error` payload from the transport
  layer. When you see `ast/build-timeout`, instruct the agent to narrow scope:
  lower `max_pages` on `nextpdf_get_ast`, or set `page_index` /
  `page_start` and `page_end` on the extraction tools.
- **Quota and backoff.** On a 429, the tool returns `error_type` of
  `QuotaExceededError` with `status_code` 429. The `retry_after` value lives on
  the exception object; because the server serializes only `error`,
  `error_type`, and `status_code`, the agent should treat 429 as a signal to
  pause and retry later rather than parsing a retry header from the tool output.
  Enforce quotas at the Connect endpoint, not in the agent.
- **Untagged PDFs.** A 422 `ast/no-struct-tree` means the source PDF has no
  structure tree. Enable heuristic mode on the server for those documents, or
  route them to a tagging step before extraction.

## Security: API-key scoping and least privilege

Treat the API key as a secret with the same care you give a database password.

- **Never embed the key in the MCP configuration file.** The JSON example above
  references `${NEXTPDF_API_KEY}` so the value resolves from the host
  environment or a secret manager at launch time. A configuration file commits
  to source control; a secret must not.
- **Scope the key to read-only extraction.** The MCP server calls only the
  AST extraction surface (`extract_cited_text`, `extract_cited_tables`,
  `get_document_ast`, `search_ast_nodes`, `get_ast_diff`). It performs no
  rendering, signing, redaction, or document mutation. Issue the agent a key
  whose server-side scope is limited to those read paths, so a compromised agent
  cannot reach write or higher-tier operations.
- **Use a dedicated key per agent.** A per-agent key lets you revoke or rotate
  one integration without affecting others, and it makes endpoint logs
  attributable to a specific agent.
- **Constrain the filesystem.** Because every tool reads an absolute path from
  local disk, the server can read any file the host process can read. Run it as
  an unprivileged user, restrict its working directory to a documents folder,
  and never run it as a privileged account.
- **Prefer Transport Layer Security (TLS).** Point `NEXTPDF_BASE_URL` at an
  `https://` endpoint in any non-local deployment. The SDK sends the key as a
  `Bearer` token in the `Authorization` header, so plaintext transport would
  expose it on the wire.

See [Connect security and operations](/connect/security-and-operations/) for the
endpoint-side controls that back these client-side practices.

## Testing the server locally before wiring an agent

Validate the server in isolation before you connect an agent. The fastest check
needs no PDF and no network:

```bash
python -c "from nextpdf.mcp import _tool_definitions; print(len(_tool_definitions()))"
```

A correct install prints `8`. If you see an `ImportError` mentioning the `mcp`
extra, the optional dependency is missing — reinstall with `pip install
nextpdf[mcp]`.

Next, exercise the same SDK paths the tools use, through the CLI, which talks to
your endpoint with the same two environment variables. Set them once:

```bash
export NEXTPDF_BASE_URL="https://connect.example.com"
export NEXTPDF_API_KEY="$(cat /run/secrets/nextpdf_api_key)"
```

Then confirm version, connectivity, and a real extraction:

```bash
nextpdf version
nextpdf info /path/to/sample.pdf
nextpdf extract text /path/to/sample.pdf --headings-only
```

`nextpdf version` runs without credentials and confirms the package imports.
`nextpdf info` exercises `get_document_ast`, the same call behind
`nextpdf_get_ast` and `nextpdf_info`. If both succeed, the credentials and
endpoint are correct and the matching MCP tools will work.

To drive the MCP protocol directly, use the upstream MCP Inspector (shipped with
the `mcp` package). Point it at the same command and environment your agent will
use, then list and invoke tools by hand. Verify that `nextpdf_health` reports
`status: "ok"` — it returns `misconfigured` whenever `NEXTPDF_BASE_URL` or
`NEXTPDF_API_KEY` is unset, which is the quickest way to catch a missing
environment value before an agent ever calls a real tool.

## Monitoring and debugging tool calls

The MCP server communicates over stdio, so its standard output carries the
protocol stream and must stay clean. The server does not configure its own
application logging, which means your primary observability channels are the
structured tool-error payloads, the CLI, and your endpoint's own logs.

- **Tool-error payloads are the signal.** Every failed call returns a JSON
  object with `error` and, for SDK errors, `error_type` and `status_code` (see
  [Error handling](#error-handling-timeouts-and-quota)). Have the agent host
  record these payloads; they identify the failing tool and the precise cause
  without any extra instrumentation in the server.
- **Reproduce through the CLI with debug logging.** The MCP server itself emits
  no logs, but the CLI exercises the same SDK calls and does log. Reproduce a
  failing tool through the matching CLI command with `--log-level debug`. The
  CLI logs to stderr with timestamps and records full tracebacks for unexpected
  errors, which is the most direct way to see what a handler is doing without
  attaching a debugger.
- **Health as a probe.** Call `nextpdf_health` to confirm the server sees a
  base URL and an API key. The result reports `sdk_version`, `server_url`,
  `api_key_configured` (a boolean, never the key itself), and `status`.
- **Endpoint-side observability.** Because each tool maps to one Connect request,
  correlate tool activity with endpoint access logs by API key and timestamp.
  Run the endpoint behind the same authentication, quota, and observability
  controls you use for other service clients.

## Troubleshooting common agent-integration issues

| Symptom | Likely cause | Resolution |
| --- | --- | --- |
| Server fails to start with an `ImportError` about the `mcp` extra | The `mcp` optional dependency is not installed | Install with `pip install nextpdf[mcp]`. |
| First tool call returns `{"error": "NEXTPDF_BASE_URL environment variable is required..."}` | The MCP `env` block did not pass the base URL, or the shell did not expand `${NEXTPDF_BASE_URL}` | Set the variable in the agent host environment and confirm the launcher expands it. |
| `nextpdf_health` reports `"status": "misconfigured"` | One of the two required variables is empty | Supply both `NEXTPDF_BASE_URL` and `NEXTPDF_API_KEY`. |
| Every path-based tool returns `{"error": "PDF file not found: <path>"}` | The agent passed a relative or host-side path the server process cannot see | Pass an absolute path readable by the server's user; confirm with `nextpdf info <path>`. |
| Tool returns `error_type` `NextPDFLicenseError` (status 402) | The operation needs a higher server-side license tier | Use an endpoint and key entitled to the operation. |
| Tool returns `error_type` `AstNoStructTreeError` (status 422) | The PDF is untagged and heuristic fallback is off | Enable heuristic mode on the endpoint, or tag the PDF first. |
| Tool returns `error_type` `QuotaExceededError` (status 429) | A rate limit or quota was reached | Pause and retry; raise the endpoint quota if the limit is too low. |
| Tool returns `error_type` `AstBuildTimeoutError` (status 504), or a transport timeout | The document is too large for the time budget | Narrow scope with `max_pages`, `page_index`, or `page_start`/`page_end`. |
| The agent registers no NextPDF tools | The agent invoked `python -m nextpdf` (the CLI) instead of `python -m nextpdf.mcp` | Use `python -m nextpdf.mcp` as the `command`/`args`. |

For endpoint-level failures and deployment checks, see
[Connect troubleshooting](/connect/troubleshooting/). For the underlying SDK
operations these tools wrap, see the [CLI reference](/python/cli/) and the
[SDK overview](/python/overview/).
