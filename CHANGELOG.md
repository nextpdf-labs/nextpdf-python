# Changelog

All notable changes to the NextPDF Python SDK are documented here.

## [0.3.0] — 2026-03-31

### Added (Phase 2a)
- `extract_cited_tables()` / `async_extract_cited_tables()` — extract structured table data with citation anchors
- `get_ast_diff()` / `async_get_ast_diff()` — compute structural diff between two AstDocuments
- `CitedTableBlock`, `CitedTableCell`, `ExtractCitedTablesResponse` models
- `AstDiffEntry`, `AstDiffSummary`, `GetAstDiffResponse` models

## [0.2.0] — 2026-03-31

### Added (Phase 1.x)
- `get_ast_node()` / `async_get_ast_node()` — retrieve a single AST node by ID
- `search_ast_nodes()` / `async_search_ast_nodes()` — query AST nodes by type and page
- `AstNodeMeta`, `AstNodeShallow`, `GetAstNodeResponse`, `SearchAstNodesResponse` models

## [0.1.0] — 2026-03-31

### Added (Phase 1 Must-Ship)
- `NextPDF` synchronous client and `AsyncNextPDF` asynchronous client
- `get_document_ast()` — extract full Semantic AST from a PDF
- `extract_cited_text()` — extract text blocks with citation anchors (page, bbox, nodeId)
- `AstDocument`, `AstNode`, `CitationAnchor`, `BoundingBox`, `NodeType` models
- `py.typed` PEP 561 marker
- Full `mypy --strict` compliance
- 78 tests (pytest + pytest-asyncio)
