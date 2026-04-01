"""NextPDF async client."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .api._ast_async import AsyncAstAPI
from .backends.remote import RemoteBackend

if TYPE_CHECKING:
    from .backends.protocol import PdfBackend


class AsyncNextPDF:
    """
    Async client for the NextPDF Connect API.

    Usage::

        async with AsyncNextPDF(base_url="https://...", api_key="...") as client:
            ast = await client.ast.get_document_ast(pdf_data=bytes_)

    Or without context manager::

        client = AsyncNextPDF(base_url="...", api_key="...")
        ast = await client.ast.get_document_ast(pdf_data=bytes_)

    Advanced — inject a custom backend::

        client = AsyncNextPDF(backend=my_backend)
    """

    def __init__(
        self,
        *,
        base_url: str = "",
        api_key: str = "",
        api_version: str = "v1",
        backend: PdfBackend | None = None,
    ) -> None:
        if backend is not None:
            self._backend: PdfBackend = backend
            self._owns_backend: bool = False
            # Preserve public attributes for tests that inspect them
            self.base_url: str = base_url.rstrip("/") if base_url else ""
            self.api_key: str = api_key
            self.api_version: str = api_version
        else:
            if not base_url:
                raise ValueError("base_url must not be empty")
            if not api_key:
                raise ValueError("api_key must not be empty")

            self.base_url = base_url.rstrip("/")
            self.api_key = api_key
            self.api_version = api_version
            self._backend = RemoteBackend(
                base_url=self.base_url,
                api_key=api_key,
                api_version=api_version,
            )
            self._owns_backend = True

        self.ast: AsyncAstAPI = AsyncAstAPI(self._backend)

    async def __aenter__(self) -> AsyncNextPDF:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying backend and release resources."""
        if self._owns_backend and isinstance(self._backend, RemoteBackend):
            await self._backend.close()
