# Post-GA Backlog -- nextpdf-python

Prioritized work items for after the 1.0.0 GA release. These are **candidates**, not commitments. Priorities may shift based on user feedback and operational needs.

---

## P1 -- First Maintenance Cycle (1-2 weeks post-GA)

| # | Item | Description | Effort |
|---|------|-------------|--------|
| 1 | Local backend bbox support | Investigate content-stream glyph position extraction for real bounding boxes | L |
| 2 | Local backend per-element text | Add MCID-to-text-run mapping from PDF content streams for tagged PDFs | L |
| 3 | MCP real-server integration test | Test MCP tools against a running NextPDF Connect server end-to-end | M |
| 4 | feature_request.yml template | Add GitHub issue template for feature requests | S |
| 5 | Fix 2 pre-existing ruff test issues | E501 line length and B017 blind exception in test_cited_tables_api.py | S |

---

## P2 -- Near-Term Product Improvement (1-2 months)

| # | Item | Description | Effort |
|---|------|-------------|--------|
| 6 | Real PDF benchmark corpus | Build 30+ PDF corpus with ground-truth for quality measurement | M |
| 7 | Cross-platform CI | Add Windows and macOS to GitHub Actions test matrix | S |
| 8 | Local engine quality metrics | Publish measured F1 scores against benchmark corpus | M |
| 9 | LangChain DocumentLoader | Provide a nextpdf-backed DocumentLoader for LangChain integration | M |
| 10 | CLI local backend support | Add --backend local flag to CLI commands for offline extraction | S |

---

## P3 -- Longer-Term Enhancement (3+ months)

| # | Item | Description | Effort |
|---|------|-------------|--------|
| 11 | Local backend promotion criteria | Define quality gates for promoting local backend from beta to stable | S |
| 12 | Content-stream MCID parser | Build a dedicated parser for mapping MCIDs to text runs (enables per-element text) | XL |
| 13 | pdfminer.six evaluation | Evaluate as alternative/complementary text extraction backend | M |
| 14 | OpenTelemetry integration | Add opt-in tracing for debugging agent workflows | M |
| 15 | PDF caching layer | Cache AST results by content hash for repeated extraction | M |
| 16 | Token budget implementation | Implement AST pruning to respect token budget parameter | M |

---

## Local Backend Beta-to-Stable Promotion Criteria

The local backend may be promoted from beta to stable when all of the following conditions are met:

1. **Bounding box coordinates** are available for tagged PDFs.
2. **Per-element text extraction** works on tagged PDFs (not just page-level).
3. **Benchmark corpus** exists with measured quality meeting these thresholds:
   - Tagged text F1 >= 95%
   - Tagged table cell accuracy >= 80%
   - Untagged-simple text F1 >= 75%
4. **Integration test suite** covers >= 30 real-world PDFs.
5. **No known crash paths** on valid PDF input.

---

## Effort Key

| Code | Duration |
|------|----------|
| S | 1-2 days |
| M | 3-5 days |
| L | 5-10 days |
| XL | 10+ days |
