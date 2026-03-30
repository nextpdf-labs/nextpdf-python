"""NextPDF SDK error hierarchy."""

from __future__ import annotations


class NextPDFError(Exception):
    """Base error for all NextPDF SDK errors."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class NextPDFAPIError(NextPDFError):
    """HTTP-level error from the NextPDF Connect API."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        error_code: str | None = None,
    ) -> None:
        super().__init__(message, status_code=status_code)
        self.error_code = error_code


class NextPDFLicenseError(NextPDFAPIError):
    """Operation requires a higher-tier license."""

    UPGRADE_URL = "https://nextpdf.dev/pricing"

    def __init__(self, message: str) -> None:
        super().__init__(
            f"{message}\nUpgrade at: {self.UPGRADE_URL}",
            status_code=402,
            error_code="license/tier-required",
        )


class QuotaExceededError(NextPDFAPIError):
    """Rate limit or quota exceeded."""

    PRICING_URL = "https://nextpdf.dev/pricing"

    def __init__(self, message: str, *, retry_after: int | None = None) -> None:
        super().__init__(
            f"{message}\nSee: {self.PRICING_URL}",
            status_code=429,
            error_code="quota/exceeded",
        )
        self.retry_after = retry_after


class AstNoStructTreeError(NextPDFAPIError):
    """PDF has no StructTree (untagged), heuristic not enabled."""

    def __init__(self) -> None:
        super().__init__(
            "PDF has no structure tree. Use heuristic=True for untagged PDFs (Pro tier).",
            status_code=422,
            error_code="ast/no-struct-tree",
        )


class AstBuildTimeoutError(NextPDFAPIError):
    """AST build timed out - try reducing page_range."""

    def __init__(self) -> None:
        super().__init__(
            "AST build timed out. Try reducing the page_range parameter.",
            status_code=504,
            error_code="ast/build-timeout",
        )
