"""NextPDF async client."""

from __future__ import annotations

from .api._ast_async import AsyncAstAPI


class AsyncNextPDF:
    """
    Async client for the NextPDF Connect API.

    Usage::

        async with AsyncNextPDF(base_url="https://...", api_key="...") as client:
            ast = await client.ast.get_document_ast(pdf_data=bytes_)

    Or without context manager::

        client = AsyncNextPDF(base_url="...", api_key="...")
        ast = await client.ast.get_document_ast(pdf_data=bytes_)
    """

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        api_version: str = "v1",
    ) -> None:
        if not base_url:
            raise ValueError("base_url must not be empty")
        if not api_key:
            raise ValueError("api_key must not be empty")

        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.api_version = api_version

        self.ast = AsyncAstAPI(self)

    async def __aenter__(self) -> AsyncNextPDF:
        return self

    async def __aexit__(self, *_: object) -> None:
        pass
