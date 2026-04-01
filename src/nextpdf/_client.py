"""NextPDF synchronous client."""

from __future__ import annotations

from ._async_client import AsyncNextPDF
from .api._ast import AstAPI


class NextPDF:
    """
    Synchronous client for the NextPDF Connect API.

    Usage::

        client = NextPDF(base_url="https://...", api_key="...")
        ast = client.ast.get_document_ast(pdf_data=bytes_)
    """

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        api_version: str = "v1",
    ) -> None:
        self._async = AsyncNextPDF(
            base_url=base_url,
            api_key=api_key,
            api_version=api_version,
        )
        self.ast = AstAPI(self._async.ast)
