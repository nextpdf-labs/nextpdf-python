# nextpdf 1.0.0 -- Final External Review Packet

Release scenario: **S2**
Date: 2026-04-01
Package: `nextpdf` on PyPI
License: MIT
Python: 3.10+

---

## 1. Executive Status

nextpdf 1.0.0 is ready for external review under the S2 release scenario.

S2 means the SDK, CLI, and MCP server ship at GA grade. The local extraction
backend is included at beta grade. All quality gates are green: 119 tests
passing, mypy --strict clean across 19 files, ruff clean, wheel and sdist
build verified by twine.

## 2. Approved Release Scenario and Rationale

S2 was selected as an intentional product decision. The SDK, CLI, and MCP
surface areas are production-quality and semver-stable. The local backend
(pypdf-based) works and is protocol-compliant but has known quality
limitations: no bounding box coordinates, heuristic-only extraction for
untagged PDFs, and page-level (not per-element) text on tagged PDFs.

The remote backend, backed by NextPDF Connect, is the recommended production
path. It provides full bbox, per-element text, and high-confidence extraction.
The local backend serves offline and agent-sandbox scenarios where network
access is unavailable, at beta quality clearly documented throughout.

## 3. What Is GA-Grade

- `NextPDF` / `AsyncNextPDF` client classes with backend protocol abstraction
- Remote backend with persistent httpx connection pooling
- Event-loop-safe sync wrapper (Jupyter and FastAPI compatible)
- CLI: `extract text`, `extract tables`, `ast`, `info`, `version` commands
- MCP server: 8 tools with import guard, health probe, `max_pages` guardrails
- 16 Pydantic v2 models with full mypy --strict compliance
- `py.typed` PEP 561 marker shipping in wheel
- Error hierarchy: 5 typed exceptions, zero commercial language

## 4. What Is Beta-Grade

Local backend (pypdf-based):

- No bounding box coordinates (`bbox` always `None`)
- Heuristic fallback for untagged PDFs at confidence 0.5
- Tagged PDF text extraction at page level, not per-element
- Table cell text extraction is basic
- 22 tests pass, protocol-compliant with `PdfBackend`

## 5. Evidence Summary

| Gate | Result |
|------|--------|
| pytest | 119/119 passed |
| mypy --strict | 0 issues (19 files) |
| ruff check src | All passed |
| ruff format | All formatted |
| uv build | wheel + sdist clean |
| twine check | PASSED |
| CLI smoke | `nextpdf` reports 1.0.0 |
| MCP tools | 8/8 registered |
| MCP health | Returns 1.0.0 |
| MCP import guard | Actionable ImportError |
| Commercial language | Zero matches |
| Overclaim grep | Zero matches |
| py.typed in wheel | Present |
| Source LOC | 3,086 |
| Test LOC | 2,070 |

## 6. Claims Alignment Summary

- README header: "Citation-ready PDF extraction for Python" -- accurate.
- "Every extracted block carries a citation anchor with page index, confidence
  score, and optional bounding box" -- qualified with "optional".
- Features table clearly separates Remote vs Local (beta) capabilities.
- Limitations section is explicit about: no OCR, heuristic confidence, no
  local bbox, server requirement for remote backend.
- No "Pro tier", "Upgrade", "Free Tier", or "The PDF Runtime" language
  anywhere in `src/`.
- Local backend marked "beta" in README, CHANGELOG, examples, and code
  docstrings.
- `pyproject.toml` description: "Citation-ready PDF extraction for Python -
  AI-agent-native".

## 7. Architecture Summary

```
nextpdf/
  _client.py / _async_client.py  -- public client classes
  _sync.py                       -- event-loop-safe sync runner
  backends/
    protocol.py                  -- PdfBackend Protocol (6 async methods)
    remote.py                    -- HTTP client with connection pooling
    local.py                     -- pypdf-based extraction (beta)
  api/
    _ast.py / _ast_async.py      -- API layer delegates to backend
  cli.py                         -- click-based CLI (6 commands)
  mcp.py                         -- MCP server (8 tools, optional dep)
  models/
    ast.py                       -- 16 Pydantic v2 models
    errors.py                    -- 5 typed exceptions
```

The backend protocol (`PdfBackend`) defines 6 async methods. Both
`RemoteBackend` and `LocalBackend` implement it. The client classes accept
any backend at construction time. The MCP server and CLI both instantiate
clients through the same public API.

## 8. Residual Issues

| Issue | Severity | Blocking? | Disposition |
|-------|----------|-----------|-------------|
| Local backend no real bbox | Known | NO | Documented in README, CHANGELOG, docstrings |
| Local per-element text not implemented | Known | NO | Documented; page-level extraction only |
| MCP not tested with real NextPDF Connect server | Low | NO | Operational testing post-publish |
| 2 pre-existing ruff issues in test files | Cosmetic | NO | Inherited; not in src |
| No benchmark corpus in repo | Medium | NO for S2 | Deferred to post-GA |
| Cross-platform CI not in matrix | Low | NO | Documented as Linux-first |
| feature_request.yml template missing | Cosmetic | NO | Post-GA housekeeping |

## 9. Explicit Review Questions

1. Are README claims honestly aligned with S2 reality?
2. Is the local backend beta labeling clear and consistent?
3. Is the MCP tool surface well-designed for agent use?
4. Is the CLI UX clean and complete?
5. Are there any remaining overclaims or positioning errors?
6. Is the package metadata correct for PyPI?
7. Is the architecture sound for a 1.0 semver commitment?

## 10. Publish Recommendation

**YES**, after external review approval. Tag `v1.0.0`, push, publish via CI
trusted publisher.
