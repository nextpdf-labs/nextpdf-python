"""NextPDF Python SDK - Citation-ready PDF extraction for AI agents."""

from ._async_client import AsyncNextPDF
from ._client import NextPDF
from ._version import __version__
from .models.ast import (
    AstDiffEntry,
    AstDiffSummary,
    AstDocument,
    AstNode,
    AstNodeMeta,
    AstNodeShallow,
    BoundingBox,
    CitationAnchor,
    CitedTableBlock,
    CitedTableCell,
    CitedTextBlock,
    ExtractCitedTablesResponse,
    GetAstDiffResponse,
    GetAstNodeResponse,
    NodeType,
    SearchAstNodesResponse,
)
from .models.errors import (
    AstBuildTimeoutError,
    AstNoStructTreeError,
    NextPDFAPIError,
    NextPDFError,
    NextPDFLicenseError,
    QuotaExceededError,
)

__all__ = [
    "AstBuildTimeoutError",
    "AstDiffEntry",
    "AstDiffSummary",
    "AstDocument",
    "AstNoStructTreeError",
    "AstNode",
    "AstNodeMeta",
    "AstNodeShallow",
    "AsyncNextPDF",
    "BoundingBox",
    "CitationAnchor",
    "CitedTableBlock",
    "CitedTableCell",
    "CitedTextBlock",
    "ExtractCitedTablesResponse",
    "GetAstDiffResponse",
    "GetAstNodeResponse",
    "NextPDF",
    "NextPDFAPIError",
    "NextPDFError",
    "NextPDFLicenseError",
    "NodeType",
    "QuotaExceededError",
    "SearchAstNodesResponse",
    "__version__",
]
