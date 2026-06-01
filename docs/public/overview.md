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
last_reviewed: "2026-05-31"
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
- A `nextpdf` command-line interface (CLI) for one-shot extraction from a file path or standard input, with output to standard output or a file.
- An optional Model Context Protocol (MCP) server so artificial-intelligence (AI) agents can call PDF extraction tools directly.
- A remote backend for production use with NextPDF Connect.
- A local backend for offline, library-only extraction through `pypdf`.

## Backend choices

The remote backend sends PDF bytes to a NextPDF Connect server. This is the recommended production path because it centralizes extraction behavior, authentication, quotas, and operational controls.

The local backend runs inside the Python process and reads PDFs through `pypdf`. It is useful for offline development and tagged PDFs. But it cannot provide precise bounding boxes and uses heuristic paragraph-level extraction for untagged PDFs. The local backend is library-only: you reach it by injecting a `LocalBackend` into `AsyncNextPDF`. The `nextpdf` CLI and the MCP server cannot use it. See [Backend choice matrix](#backend-choice-matrix) for the full comparison.

## Limitations

The SDK does not perform optical character recognition (OCR). Scanned or image-only PDFs need an OCR step before NextPDF can extract embedded text. Complex layouts, overlapping text, and unusual PDF producers can also reduce extraction quality.

The `nextpdf` CLI is remote-only and not a streaming interface. Each command reads the whole PDF into memory (from a file path or standard input), sends it to a NextPDF Connect server, builds the complete result in memory, then serializes it in a single write. You can redirect that output to a file with `--output` (or `-o`) or to standard output, but the result is fully buffered, not produced incrementally. The CLI cannot use the local `pypdf` backend.

## Choosing a client: sync vs async

Both clients share one `ast` method namespace and return the same Pydantic models. The difference is the concurrency model.

| Your context | Use | Why |
| --- | --- | --- |
| Scripts and batch jobs | `NextPDF` (sync) | Linear control flow; no event loop to manage. |
| Jupyter notebooks | `NextPDF` (sync) | `run_sync` detects the running event loop and dispatches to a worker thread, so blocking calls work inside cells. |
| The `nextpdf` CLI | `NextPDF` (sync, internal) | The CLI builds a sync client for you. |
| `asyncio` services | `AsyncNextPDF` | Native `await`; no thread hand-off. |
| FastAPI, Starlette, ASGI | `AsyncNextPDF` | Shares the request event loop and the same connection pool. |
| High-concurrency fan-out | `AsyncNextPDF` | Run many extractions concurrently with `asyncio.gather` over one pooled client. |

`NextPDF` wraps an internal `AsyncNextPDF` and runs each call through `run_sync`. Inside a running event loop (for example, a notebook), `run_sync` dispatches the coroutine to a single-worker thread with its own loop. So you do not hit the nested-`asyncio.run` error. In an `asyncio` or ASGI service, call `AsyncNextPDF` directly instead of paying for that thread hand-off on every call.

The async client owns an `httpx.AsyncClient` for connection pooling, so reuse one `AsyncNextPDF` instance and close it once. The sync `NextPDF` client does not expose a `close()` method. For long-lived async workloads, prefer `AsyncNextPDF` and manage its lifecycle explicitly (see [Production operational model](#production-operational-model)).

## Backend choice matrix

A backend implements the `PdfBackend` protocol. The remote backend (`RemoteBackend`) is selected automatically when you pass `base_url` and `api_key`. The local backend (`LocalBackend`) must be injected explicitly through the `backend=` parameter of `AsyncNextPDF`; it is not exported from the top-level `nextpdf` package and is not reachable from the CLI or the MCP server.

| Capability | Remote (`RemoteBackend`) | Local (`LocalBackend`) |
| --- | --- | --- |
| Selected by | `base_url` + `api_key` | `AsyncNextPDF(backend=LocalBackend(...))` |
| Network | NextPDF Connect over HyperText Transfer Protocol Secure (HTTPS) | None; runs in-process |
| Authentication, quotas, metering | Centralized on the server | None |
| Observability and operational controls | Server-side | None |
| Tagged PDF (StructTree) extraction | Yes | Yes |
| Untagged PDF extraction | Server engine | Heuristic paragraph split, confidence `0.5` |
| Bounding boxes | Yes (when the server provides them) | No (`bbox` is `None`) |
| Table extraction on untagged PDFs | Server engine | Returns no tables |
| Reachable from CLI / MCP server | Yes | No (library-only) |
| Recommended for | Production | Offline development, tagged-PDF tests |

Use the remote backend for production: it is the only path that gives you centralized authentication, quota enforcement, metering, and observability. Use the local backend for offline development and tests against tagged PDFs, while accepting heuristic results, no bounding boxes, and no tables on untagged input.

```python
"""Inject the local backend for offline, library-only extraction."""

from nextpdf import AsyncNextPDF
from nextpdf.backends.local import LocalBackend


async def extract_offline(pdf_bytes: bytes) -> None:
    """Extract cited text without a NextPDF Connect server."""
    async with AsyncNextPDF(backend=LocalBackend()) as client:
        blocks = await client.ast.extract_cited_text(pdf_bytes)
        for block in blocks:
            # Heuristic blocks on untagged PDFs report confidence 0.5.
            print(block.citation.confidence, block.text)
```

## Production operational model

In production you run the remote backend against NextPDF Connect. The patterns below cover client reuse, error handling, retries, quota handling, and timeouts. Every symbol used here exists in the SDK; the SDK does not retry for you, so the retry loop is your responsibility.

### Reuse the client and pool connections

`RemoteBackend` keeps one persistent `httpx.AsyncClient` for connection pooling. Construct `AsyncNextPDF` once, share it across requests, and close it on shutdown. Do not create a client per request.

```python
"""Reuse one pooled async client for the lifetime of the process."""

import asyncio
import os
from pathlib import Path

from nextpdf import AsyncNextPDF


async def main() -> None:
    """Run several extractions over a single pooled client."""
    base_url = os.environ["NEXTPDF_BASE_URL"]
    # Treat the API key as a secret; read it from the environment, never hard-code it.
    api_key = os.environ["NEXTPDF_API_KEY"]

    async with AsyncNextPDF(base_url=base_url, api_key=api_key) as client:
        pdf_paths = (Path("a.pdf"), Path("b.pdf"), Path("c.pdf"))
        tasks = [
            client.ast.get_document_ast(path.read_bytes())
            for path in pdf_paths
        ]
        documents = await asyncio.gather(*tasks)
        for document in documents:
            print(document.page_count, document.estimated_tokens)


if __name__ == "__main__":
    asyncio.run(main())
```

The async context manager calls `close()` on exit, which closes the underlying transport. Without a context manager, call `await client.close()` yourself.

### Handle errors with the exception hierarchy

The SDK raises a typed hierarchy. All errors derive from `NextPDFError`; HTTP-level failures derive from `NextPDFAPIError` and carry a `status_code`. Catch the specific types you can act on, and fall back to the base type.

| Exception | Raised when | Key attributes |
| --- | --- | --- |
| `NextPDFError` | Base type for every SDK error | `status_code` |
| `NextPDFAPIError` | Any HTTP error from the server | `status_code`, `error_code` |
| `NextPDFLicenseError` | HTTP 402; the feature needs a higher server tier | `status_code` (402) |
| `QuotaExceededError` | HTTP 429; rate limit or quota exceeded | `retry_after` |
| `AstNoStructTreeError` | HTTP 422; untagged PDF with heuristic mode off | `status_code` (422) |
| `AstBuildTimeoutError` | HTTP 504; AST build timed out | `status_code` (504) |

```python
"""Map SDK exceptions to caller-facing outcomes."""

from nextpdf import (
    AstBuildTimeoutError,
    AstNoStructTreeError,
    AsyncNextPDF,
    NextPDFAPIError,
    NextPDFError,
    NextPDFLicenseError,
    QuotaExceededError,
)


async def safe_extract(client: AsyncNextPDF, pdf_bytes: bytes) -> str:
    """Extract text, translating known failures into a stable status string."""
    try:
        blocks = await client.ast.extract_cited_text(pdf_bytes)
    except QuotaExceededError as exc:
        # exc.retry_after holds the server Retry-After value in seconds, or None.
        return f"rate-limited; retry after {exc.retry_after}s"
    except NextPDFLicenseError:
        return "feature requires a higher server tier"
    except AstNoStructTreeError:
        return "untagged PDF; enable heuristic mode or use a tagged PDF"
    except AstBuildTimeoutError:
        return "build timed out; reduce the page range"
    except NextPDFAPIError as exc:
        return f"server error (status {exc.status_code})"
    except NextPDFError:
        return "extraction failed"
    return "\n".join(block.text for block in blocks)
```

### Retry transient failures with backoff

The SDK does not retry automatically. Wrap calls in your own loop that retries on transient HTTP failures and honors the server `Retry-After` value, which `QuotaExceededError` exposes as `retry_after` (an integer number of seconds, or `None`). Use exponential backoff for other transient statuses, and do not retry `NextPDFLicenseError`.

```python
"""Retry transient failures with exponential backoff and Retry-After support."""

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from nextpdf import NextPDFAPIError, QuotaExceededError

_RETRYABLE_STATUS = frozenset({500, 502, 503, 504})

_T = TypeVar("_T")


async def with_retry(
    coro_factory: Callable[[], Awaitable[_T]],
    *,
    max_attempts: int = 4,
) -> _T:
    """Call coro_factory() with bounded retries on transient server errors.

    Args:
        coro_factory: A zero-argument callable returning a fresh awaitable.
        max_attempts: Maximum number of attempts before giving up.

    Returns:
        The awaited result of the first successful attempt.

    Raises:
        NextPDFAPIError: When all attempts fail or the error is not retryable.
    """
    delay = 1.0
    for attempt in range(1, max_attempts + 1):
        try:
            return await coro_factory()
        except QuotaExceededError as exc:
            if attempt == max_attempts:
                raise
            await asyncio.sleep(exc.retry_after if exc.retry_after is not None else delay)
            delay *= 2.0
        except NextPDFAPIError as exc:
            if attempt == max_attempts or exc.status_code not in _RETRYABLE_STATUS:
                raise
            await asyncio.sleep(delay)
            delay *= 2.0
    raise RuntimeError("unreachable")
```

### Manage quotas, rate limits, and timeouts

Quota and rate-limit enforcement live on the server. On HTTP 429 the SDK raises `QuotaExceededError` and parses the `Retry-After` header into `retry_after`. The remote backend also surfaces `X-RateLimit-*` headers on render responses, so you can throttle proactively before you hit a hard limit.

Request timeouts use a fixed default of 60 seconds total with a 10-second connect timeout (`httpx.Timeout(60.0, connect=10.0)`). To bound long AST builds, prefer narrowing the work with `page_range_start`, `page_range_end`, or `token_budget` rather than relying on the timeout alone; an over-long build returns `AstBuildTimeoutError` (HTTP 504).

## Example architectures

### Batch job

A batch worker reads PDFs, extracts cited text, and writes structured output. Reuse one pooled client, bound concurrency with a semaphore, and apply the retry helper above.

```python
"""Batch-extract a directory of PDFs over one pooled async client."""

import asyncio
import os
from pathlib import Path

from nextpdf import AsyncNextPDF


async def run_batch(input_dir: Path, concurrency: int = 8) -> None:
    """Extract cited text for every PDF in input_dir, bounded by concurrency."""
    semaphore = asyncio.Semaphore(concurrency)

    async def worker(client: AsyncNextPDF, path: Path) -> None:
        async with semaphore:
            blocks = await client.ast.extract_cited_text(path.read_bytes())
            out = path.with_suffix(".txt")
            out.write_text("\n".join(b.text for b in blocks), encoding="utf-8")

    async with AsyncNextPDF(
        base_url=os.environ["NEXTPDF_BASE_URL"],
        api_key=os.environ["NEXTPDF_API_KEY"],
    ) as client:
        await asyncio.gather(*(worker(client, p) for p in input_dir.glob("*.pdf")))
```

### Web service

A FastAPI service shares one `AsyncNextPDF` across requests on the application lifespan, so every request reuses the connection pool. Read credentials from the environment and treat the API key as a secret.

```python
"""FastAPI service that shares one pooled NextPDF client across requests."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile

from nextpdf import AsyncNextPDF


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create the pooled client on startup and close it on shutdown."""
    app.state.client = AsyncNextPDF(
        base_url=os.environ["NEXTPDF_BASE_URL"],
        api_key=os.environ["NEXTPDF_API_KEY"],
    )
    try:
        yield
    finally:
        await app.state.client.close()


app = FastAPI(lifespan=lifespan)


@app.post("/extract")
async def extract(file: UploadFile) -> dict[str, list[str]]:
    """Return cited text blocks for an uploaded PDF."""
    pdf_bytes = await file.read()
    blocks = await app.state.client.ast.extract_cited_text(pdf_bytes)
    return {"text": [block.text for block in blocks]}
```

### Agent tool

For AI agents, run the MCP server. It exposes PDF tools (for example `nextpdf_extract_text`, `nextpdf_extract_tables`, `nextpdf_get_ast`, `nextpdf_info`, `nextpdf_search`, `nextpdf_get_outline`, `nextpdf_diff`, and `nextpdf_health`) over standard input/output. The server reads `NEXTPDF_BASE_URL` and `NEXTPDF_API_KEY` from the environment and is therefore remote-backed; like the CLI, it cannot use the local backend. Install the optional extra and run the module.

```bash
pip install "nextpdf[mcp]"
python -m nextpdf.mcp
```

See [Python MCP server](/python/mcp/) for the agent integration walkthrough, [Python CLI](/python/cli/) for terminal usage, and [Python API reference](/python/api/) for the full client, model, and exception surface.
