# nextpdf 1.0.0

**Citation-ready PDF extraction for Python - AI-agent-native.**

This is the first stable release of nextpdf.

## Highlights

- **SDK**: `NextPDF` and `AsyncNextPDF` clients with typed Pydantic v2 models
- **CLI**: `nextpdf extract text`, `nextpdf extract tables`, `nextpdf ast`, `nextpdf info`
- **MCP Server**: 8 tools for AI agent integration (Claude Code, etc.) via `pip install nextpdf[mcp]`
- **Local Backend (beta)**: Offline PDF extraction using pypdf -- no server required
- **Remote Backend**: Production-grade extraction via NextPDF Connect server
- **Backend Protocol**: Pluggable `PdfBackend` abstraction for custom extraction engines

## Install

```bash
pip install nextpdf          # SDK + CLI + local backend
pip install nextpdf[mcp]     # + MCP server for AI agents
```

## Local Backend (Beta)

The local backend works offline but has limitations compared to the remote backend:
- No bounding box coordinates
- Heuristic-only extraction for untagged PDFs (confidence 0.5)
- Basic table cell text extraction

For production use with full accuracy, use the remote backend with NextPDF Connect.

## Quality

- 119 tests | mypy --strict | ruff | py.typed | Python 3.10-3.13
- MIT licensed

## Links

- [Documentation](https://nextpdf.dev/docs/python)
- [Changelog](CHANGELOG.md)
