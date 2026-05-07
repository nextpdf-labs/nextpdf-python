"""Remote backend — HTTP-based PDF extraction via the NextPDF Connect API.

Covers server v5.2 endpoint surface:
  Core:       /healthz, /readyz, /api/v1/capabilities, /api/v1/render,
              /api/v1/jobs/*, /api/v1/extract-text, /api/v1/merge, /api/v1/split
  Sessions:   /api/v1/sessions/*
  Pro:        /api/v1/sign, /api/v1/fill-form, /api/v1/redact,
              /api/v1/compare, /api/v1/check-accessibility, /api/v1/optimize
  Enterprise: /api/v1/compliance-check, /api/v1/forensic-analyze, /api/v1/ai-certify

Security notes (OWASP Top 10 2025 A05 — Security Misconfiguration):
  - Bearer token is NEVER logged or included in error messages.
  - TLS verification is enabled by default; no insecure kwarg exposed.
  - Rate-limit headers (Retry-After, X-RateLimit-*) are surfaced in responses.
"""

from __future__ import annotations

import base64
from typing import Any

import httpx

from nextpdf._http import DEFAULT_TIMEOUT, build_request_headers, raise_for_error_response
from nextpdf.models.ast import (
    AstDiffEntry,
    AstDiffSummary,
    AstDocument,
    AstNode,
    AstNodeMeta,
    CitedTableBlock,
    CitedTextBlock,
    ExtractCitedTablesResponse,
    GetAstDiffResponse,
    GetAstNodeResponse,
    SearchAstNodesResponse,
)
from nextpdf.models.connect import (
    AccessibilityIssue,
    AddHtmlRequest,
    AddImageRequest,
    AddPageRequest,
    AddTableRequest,
    AddTextRequest,
    AiCertifyRequest,
    AiCertifyResponse,
    CapabilitiesResponse,
    CapabilityEntry,
    CheckAccessibilityRequest,
    CheckAccessibilityResponse,
    CompareRequest,
    CompareResponse,
    ComplianceCheckRequest,
    ComplianceCheckResponse,
    ComplianceViolation,
    CreateSessionRequest,
    ExtractTextRequest,
    ExtractTextResponse,
    FillFormRequest,
    FillFormResponse,
    ForensicAnalyzeRequest,
    ForensicAnalyzeResponse,
    ForensicFinding,
    HealthResponse,
    JobRecord,
    JobResultResponse,
    JobStatus,
    JobStatusResponse,
    JobSubmitRequest,
    JobSubmitResponse,
    MergeRequest,
    MergeResponse,
    OptimizeRequest,
    OptimizeResponse,
    RedactRequest,
    RedactResponse,
    RenderRequest,
    RenderResponse,
    SessionOperationResponse,
    SessionRecord,
    SessionRenderRequest,
    SessionRenderResponse,
    SessionResponse,
    SetFontRequest,
    SignRequest,
    SignResponse,
    SplitRequest,
    SplitResponse,
    Tier,
)


class RemoteBackend:
    """PdfBackend implementation backed by the NextPDF Connect HTTP API.

    Uses a single persistent ``httpx.AsyncClient`` for connection pooling.
    Must be used as an async context manager **or** explicitly closed via
    :meth:`close` to release underlying connections.
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

        self._base_url: str = base_url.rstrip("/")
        self._api_key: str = api_key
        self._api_version: str = api_version
        self._http: httpx.AsyncClient = httpx.AsyncClient(
            headers=build_request_headers(api_key),
            timeout=DEFAULT_TIMEOUT,
        )

    # -- lifecycle ------------------------------------------------------------

    async def __aenter__(self) -> RemoteBackend:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying HTTP client and release connections."""
        await self._http.aclose()

    # -- helpers --------------------------------------------------------------

    @staticmethod
    def _parse_meta(data: dict[str, Any]) -> AstNodeMeta:
        """Extract ``_meta`` block from response data."""
        raw = data.get("_meta", {})
        if not isinstance(raw, dict):
            return AstNodeMeta()
        return AstNodeMeta(
            etag=raw.get("etag"),  # pyright: ignore[reportUnknownArgumentType,reportUnknownMemberType]
            pages_processed=raw.get("pages_processed"),  # pyright: ignore[reportUnknownArgumentType,reportUnknownMemberType]
        )

    # -- PdfBackend protocol methods ------------------------------------------

    async def get_document_ast(
        self,
        pdf_data: bytes,
        *,
        page_range_start: int | None = None,
        page_range_end: int | None = None,
        token_budget: int | None = None,
    ) -> AstDocument:
        """Build a Semantic AST from PDF bytes."""
        payload: dict[str, object] = {
            "pdf_data": base64.b64encode(pdf_data).decode(),
        }
        if page_range_start is not None:
            payload["page_range_start"] = page_range_start
        if page_range_end is not None:
            payload["page_range_end"] = page_range_end
        if token_budget is not None:
            payload["token_budget"] = token_budget

        response = await self._http.post(
            f"{self._base_url}/v1/ast/document",
            json=payload,
        )
        raise_for_error_response(response)
        return AstDocument.model_validate(response.json())

    async def extract_cited_text(
        self,
        pdf_data: bytes,
        *,
        page_index: int | None = None,
        headings_only: bool = False,
    ) -> list[CitedTextBlock]:
        """Extract text blocks with citation anchors."""
        payload: dict[str, object] = {
            "pdf_data": base64.b64encode(pdf_data).decode(),
        }
        if page_index is not None:
            payload["page_index"] = page_index
        if headings_only:
            payload["headings_only"] = True

        response = await self._http.post(
            f"{self._base_url}/v1/ast/extract-cited-text",
            json=payload,
        )
        raise_for_error_response(response)
        data: dict[str, list[dict[str, object]]] = response.json()
        return [CitedTextBlock.model_validate(block) for block in data.get("blocks", [])]

    async def extract_cited_tables(
        self,
        pdf_data: bytes,
        *,
        page_range: dict[str, int] | None = None,
    ) -> ExtractCitedTablesResponse:
        """Extract all tables from a PDF with citation anchors."""
        payload: dict[str, object] = {
            "pdf_data": base64.b64encode(pdf_data).decode("ascii"),
        }
        if page_range is not None:
            payload["page_range"] = page_range

        response = await self._http.post(
            f"{self._base_url}/v1/tools/extract_cited_tables",
            json=payload,
        )
        raise_for_error_response(response)
        raw: dict[str, Any] = response.json()
        meta = self._parse_meta(raw)
        return ExtractCitedTablesResponse(
            tables=[CitedTableBlock.model_validate(t) for t in raw.get("tables", [])],
            table_count=raw.get("table_count", 0),
            pages_processed=meta.pages_processed,
        )

    async def search_ast_nodes(
        self,
        pdf_data: bytes,
        *,
        node_type: str | None = None,
        page_index: int | None = None,
        text_query: str | None = None,
        max_results: int = 100,
    ) -> SearchAstNodesResponse:
        """Search AST nodes by type, page, or text content."""
        payload: dict[str, object] = {
            "pdf_data": base64.b64encode(pdf_data).decode(),
            "max_results": max_results,
        }
        if node_type is not None:
            payload["node_type"] = node_type
        if page_index is not None:
            payload["page_index"] = page_index
        if text_query is not None:
            payload["text_query"] = text_query

        response = await self._http.post(
            f"{self._base_url}/v1/ast/search",
            json=payload,
        )
        raise_for_error_response(response)
        raw = response.json()
        return SearchAstNodesResponse.model_validate(
            {
                "nodes": raw.get("nodes", []),
                "total_matches": raw.get("total_matches", 0),
                "truncated": raw.get("truncated", False),
                "meta": self._parse_meta(raw),
            }
        )

    async def get_ast_node(
        self,
        pdf_data: bytes,
        node_id: str,
    ) -> GetAstNodeResponse:
        """Retrieve a single AST node by its node ID."""
        payload: dict[str, object] = {
            "pdf_data": base64.b64encode(pdf_data).decode(),
            "node_id": node_id,
        }

        response = await self._http.post(
            f"{self._base_url}/v1/ast/node",
            json=payload,
        )
        raise_for_error_response(response)
        raw: dict[str, Any] = response.json()
        return GetAstNodeResponse(
            node=AstNode.model_validate(raw["node"]),
            meta=self._parse_meta(raw),
        )

    async def get_ast_diff(
        self,
        original_pdf_data: bytes,
        modified_pdf_data: bytes,
    ) -> GetAstDiffResponse:
        """Compare two PDFs and return structural AST differences."""
        payload: dict[str, object] = {
            "original_pdf_data": base64.b64encode(original_pdf_data).decode("ascii"),
            "modified_pdf_data": base64.b64encode(modified_pdf_data).decode("ascii"),
        }

        response = await self._http.post(
            f"{self._base_url}/v1/tools/get_ast_diff",
            json=payload,
        )
        raise_for_error_response(response)
        raw = response.json()
        meta = self._parse_meta(raw)
        return GetAstDiffResponse(
            original_page_count=raw["original_page_count"],
            modified_page_count=raw["modified_page_count"],
            summary=AstDiffSummary.model_validate(raw["summary"]),
            diff=[AstDiffEntry.model_validate(e) for e in raw.get("diff", [])],
            pages_processed=meta.pages_processed,
        )

    # =========================================================================
    # Server v5.2 endpoints — added Cycle 5 D5
    # =========================================================================

    # -- System / health -------------------------------------------------------

    async def health(self) -> HealthResponse:
        """GET /healthz — liveness probe (no auth required)."""
        response = await self._http.get(f"{self._base_url}/healthz")
        raise_for_error_response(response)
        return HealthResponse.model_validate(response.json())

    async def readyz(self) -> HealthResponse:
        """GET /readyz — readiness probe (no auth required)."""
        response = await self._http.get(f"{self._base_url}/readyz")
        raise_for_error_response(response)
        return HealthResponse.model_validate(response.json())

    # -- Capabilities ----------------------------------------------------------

    async def get_capabilities(self) -> CapabilitiesResponse:
        """GET /api/v1/capabilities — list available server capabilities."""
        response = await self._http.get(f"{self._base_url}/api/v1/capabilities")
        raise_for_error_response(response)
        raw: dict[str, Any] = response.json()
        caps = [
            CapabilityEntry(
                name=c["name"],
                tier=Tier(c["tier"]),
                enabled=c["enabled"],
            )
            for c in raw.get("capabilities", [])
        ]
        return CapabilitiesResponse(
            server_version=raw.get("server_version"),
            capabilities=caps,
        )

    # -- Synchronous render ----------------------------------------------------

    async def render(self, request: RenderRequest) -> RenderResponse:
        """POST /api/v1/render — synchronous PDF render (Core tier)."""
        response = await self._http.post(
            f"{self._base_url}/api/v1/render",
            json=request.model_dump(exclude_none=True),
        )
        raise_for_error_response(response)
        raw = response.json()
        pdf_bytes = base64.b64decode(raw["pdf_data"]) if isinstance(raw.get("pdf_data"), str) else raw["pdf_data"]
        return RenderResponse(
            pdf_data=pdf_bytes,
            page_count=raw["page_count"],
            size_bytes=raw.get("size_bytes", len(pdf_bytes)),
            conformance=raw.get("conformance"),
            rate_limit_remaining=self._int_header(response, "X-RateLimit-Remaining"),
            rate_limit_reset_at=response.headers.get("X-RateLimit-Reset"),
        )

    # -- Async jobs ------------------------------------------------------------

    async def submit_job(self, request: JobSubmitRequest) -> JobSubmitResponse:
        """POST /api/v1/jobs — submit an async render job (Core tier)."""
        response = await self._http.post(
            f"{self._base_url}/api/v1/jobs",
            json=request.model_dump(exclude_none=True),
        )
        raise_for_error_response(response)
        raw: dict[str, Any] = response.json()
        return JobSubmitResponse(
            job_id=raw["job_id"],
            status=JobStatus(raw["status"]),
            poll_url=raw.get("poll_url", f"{self._base_url}/api/v1/jobs/{raw['job_id']}"),
        )

    async def get_job_status(self, job_id: str) -> JobStatusResponse:
        """GET /api/v1/jobs/{id} — poll job status (Core tier)."""
        response = await self._http.get(f"{self._base_url}/api/v1/jobs/{job_id}")
        raise_for_error_response(response)
        raw: dict[str, Any] = response.json()
        return JobStatusResponse(
            job=JobRecord.model_validate(raw["job"] if "job" in raw else raw),
            rate_limit_remaining=self._int_header(response, "X-RateLimit-Remaining"),
        )

    async def get_job_result(self, job_id: str) -> JobResultResponse:
        """GET /api/v1/jobs/{id}/result — download completed PDF (Core tier)."""
        response = await self._http.get(f"{self._base_url}/api/v1/jobs/{job_id}/result")
        raise_for_error_response(response)
        # Server may return raw PDF bytes (content-type: application/pdf)
        # or a JSON envelope with base64 pdf_data.
        content_type = response.headers.get("content-type", "")
        if "application/pdf" in content_type:
            pdf_bytes = response.content
            return JobResultResponse(
                pdf_data=pdf_bytes,
                page_count=int(response.headers.get("X-Page-Count", 0)),
                size_bytes=len(pdf_bytes),
                conformance=response.headers.get("X-Conformance"),
            )
        raw: dict[str, Any] = response.json()
        pdf_bytes = base64.b64decode(raw["pdf_data"]) if isinstance(raw.get("pdf_data"), str) else raw["pdf_data"]
        return JobResultResponse(
            pdf_data=pdf_bytes,
            page_count=raw.get("page_count", 0),
            size_bytes=raw.get("size_bytes", len(pdf_bytes)),
            conformance=raw.get("conformance"),
        )

    async def cancel_job(self, job_id: str) -> None:
        """DELETE /api/v1/jobs/{id} — cancel or delete a job (Core tier)."""
        response = await self._http.delete(f"{self._base_url}/api/v1/jobs/{job_id}")
        raise_for_error_response(response)

    # -- Core document operations ----------------------------------------------

    async def extract_text(self, request: ExtractTextRequest) -> ExtractTextResponse:
        """POST /api/v1/extract-text — plain text extraction (Core tier)."""
        payload: dict[str, object] = {
            "pdf_data": base64.b64encode(request.pdf_data).decode(),
            "include_formatting": request.include_formatting,
        }
        if request.page_index is not None:
            payload["page_index"] = request.page_index

        response = await self._http.post(
            f"{self._base_url}/api/v1/extract-text",
            json=payload,
        )
        raise_for_error_response(response)
        raw: dict[str, Any] = response.json()
        return ExtractTextResponse(
            text=raw["text"],
            page_count=raw.get("page_count", 0),
            pages_processed=raw.get("pages_processed", 0),
        )

    async def merge(self, request: MergeRequest) -> MergeResponse:
        """POST /api/v1/merge — merge multiple PDFs (Core tier)."""
        payload: dict[str, object] = {
            "pdf_files": [base64.b64encode(f).decode() for f in request.pdf_files],
            "output_config": request.output_config.model_dump(exclude_none=True),
        }

        response = await self._http.post(
            f"{self._base_url}/api/v1/merge",
            json=payload,
        )
        raise_for_error_response(response)
        raw: dict[str, Any] = response.json()
        pdf_bytes = base64.b64decode(raw["pdf_data"]) if isinstance(raw.get("pdf_data"), str) else raw["pdf_data"]
        return MergeResponse(
            pdf_data=pdf_bytes,
            page_count=raw.get("page_count", 0),
            size_bytes=raw.get("size_bytes", len(pdf_bytes)),
        )

    async def split(self, request: SplitRequest) -> SplitResponse:
        """POST /api/v1/split — split PDF into chunks (Core tier)."""
        payload: dict[str, object] = {
            "pdf_data": base64.b64encode(request.pdf_data).decode(),
            "split_at_pages": request.split_at_pages,
        }
        if request.max_pages_per_chunk is not None:
            payload["max_pages_per_chunk"] = request.max_pages_per_chunk

        response = await self._http.post(
            f"{self._base_url}/api/v1/split",
            json=payload,
        )
        raise_for_error_response(response)
        raw: dict[str, Any] = response.json()
        chunks = [
            base64.b64decode(c) if isinstance(c, str) else c
            for c in raw.get("chunks", [])
        ]
        return SplitResponse(
            chunks=chunks,
            chunk_page_counts=raw.get("chunk_page_counts", []),
        )

    # -- Sessions --------------------------------------------------------------

    async def create_session(self, request: CreateSessionRequest) -> SessionResponse:
        """POST /api/v1/sessions — create a new document session (Core tier)."""
        response = await self._http.post(
            f"{self._base_url}/api/v1/sessions",
            json=request.model_dump(exclude_none=True),
        )
        raise_for_error_response(response)
        raw: dict[str, Any] = response.json()
        return SessionResponse(
            session=SessionRecord.model_validate(raw.get("session", raw)),
        )

    async def get_session(self, session_id: str) -> SessionResponse:
        """GET /api/v1/sessions/{id} — get session metadata (Core tier)."""
        response = await self._http.get(f"{self._base_url}/api/v1/sessions/{session_id}")
        raise_for_error_response(response)
        raw: dict[str, Any] = response.json()
        return SessionResponse(
            session=SessionRecord.model_validate(raw.get("session", raw)),
        )

    async def destroy_session(self, session_id: str) -> None:
        """DELETE /api/v1/sessions/{id} — destroy session (Core tier)."""
        response = await self._http.delete(f"{self._base_url}/api/v1/sessions/{session_id}")
        raise_for_error_response(response)

    async def session_add_page(
        self,
        session_id: str,
        request: AddPageRequest,
    ) -> SessionOperationResponse:
        """POST /api/v1/sessions/{id}/pages — add a page to a session."""
        response = await self._http.post(
            f"{self._base_url}/api/v1/sessions/{session_id}/pages",
            json=request.model_dump(exclude_none=True),
        )
        raise_for_error_response(response)
        return SessionOperationResponse.model_validate(response.json())

    async def session_add_text(
        self,
        session_id: str,
        request: AddTextRequest,
    ) -> SessionOperationResponse:
        """POST /api/v1/sessions/{id}/text — add text to a session."""
        response = await self._http.post(
            f"{self._base_url}/api/v1/sessions/{session_id}/text",
            json=request.model_dump(exclude_none=True),
        )
        raise_for_error_response(response)
        return SessionOperationResponse.model_validate(response.json())

    async def session_add_image(
        self,
        session_id: str,
        request: AddImageRequest,
    ) -> SessionOperationResponse:
        """POST /api/v1/sessions/{id}/images — add an image to a session."""
        payload: dict[str, object] = {
            "image_data": base64.b64encode(request.image_data).decode(),
            "x": request.x,
            "y": request.y,
        }
        if request.width is not None:
            payload["width"] = request.width
        if request.height is not None:
            payload["height"] = request.height
        if request.page_number is not None:
            payload["page_number"] = request.page_number

        response = await self._http.post(
            f"{self._base_url}/api/v1/sessions/{session_id}/images",
            json=payload,
        )
        raise_for_error_response(response)
        return SessionOperationResponse.model_validate(response.json())

    async def session_add_table(
        self,
        session_id: str,
        request: AddTableRequest,
    ) -> SessionOperationResponse:
        """POST /api/v1/sessions/{id}/tables — add a table to a session."""
        response = await self._http.post(
            f"{self._base_url}/api/v1/sessions/{session_id}/tables",
            json=request.model_dump(exclude_none=True),
        )
        raise_for_error_response(response)
        return SessionOperationResponse.model_validate(response.json())

    async def session_add_html(
        self,
        session_id: str,
        request: AddHtmlRequest,
    ) -> SessionOperationResponse:
        """POST /api/v1/sessions/{id}/html — add an HTML block to a session."""
        response = await self._http.post(
            f"{self._base_url}/api/v1/sessions/{session_id}/html",
            json=request.model_dump(exclude_none=True),
        )
        raise_for_error_response(response)
        return SessionOperationResponse.model_validate(response.json())

    async def session_set_font(
        self,
        session_id: str,
        request: SetFontRequest,
    ) -> SessionOperationResponse:
        """PUT /api/v1/sessions/{id}/font — set font for a session."""
        response = await self._http.put(
            f"{self._base_url}/api/v1/sessions/{session_id}/font",
            json=request.model_dump(exclude_none=True),
        )
        raise_for_error_response(response)
        return SessionOperationResponse.model_validate(response.json())

    async def session_render(
        self,
        session_id: str,
        request: SessionRenderRequest,
    ) -> SessionRenderResponse:
        """POST /api/v1/sessions/{id}/render — finalize and render session to PDF."""
        response = await self._http.post(
            f"{self._base_url}/api/v1/sessions/{session_id}/render",
            json=request.model_dump(exclude_none=True),
        )
        raise_for_error_response(response)
        raw: dict[str, Any] = response.json()
        pdf_bytes = base64.b64decode(raw["pdf_data"]) if isinstance(raw.get("pdf_data"), str) else raw["pdf_data"]
        return SessionRenderResponse(
            pdf_data=pdf_bytes,
            page_count=raw.get("page_count", 0),
            size_bytes=raw.get("size_bytes", len(pdf_bytes)),
            conformance=raw.get("conformance"),
        )

    # -- Pro operations --------------------------------------------------------

    async def sign(self, request: SignRequest) -> SignResponse:
        """POST /api/v1/sign — digitally sign a PDF (Pro tier)."""
        payload: dict[str, object] = {
            "pdf_data": base64.b64encode(request.pdf_data).decode(),
            "certificate_pem": request.certificate_pem,
            "private_key_pem": request.private_key_pem,
        }
        if request.reason is not None:
            payload["reason"] = request.reason
        if request.location is not None:
            payload["location"] = request.location
        if request.contact is not None:
            payload["contact"] = request.contact
        if request.timestamp_url is not None:
            payload["timestamp_url"] = request.timestamp_url

        response = await self._http.post(
            f"{self._base_url}/api/v1/sign",
            json=payload,
        )
        raise_for_error_response(response)
        raw: dict[str, Any] = response.json()
        pdf_bytes = base64.b64decode(raw["pdf_data"]) if isinstance(raw.get("pdf_data"), str) else raw["pdf_data"]
        return SignResponse(
            pdf_data=pdf_bytes,
            signature_id=raw["signature_id"],
            signed_at=raw["signed_at"],
        )

    async def fill_form(self, request: FillFormRequest) -> FillFormResponse:
        """POST /api/v1/fill-form — fill PDF form fields (Pro tier)."""
        payload: dict[str, object] = {
            "pdf_data": base64.b64encode(request.pdf_data).decode(),
            "fields": request.fields,
            "flatten": request.flatten,
        }

        response = await self._http.post(
            f"{self._base_url}/api/v1/fill-form",
            json=payload,
        )
        raise_for_error_response(response)
        raw: dict[str, Any] = response.json()
        pdf_bytes = base64.b64decode(raw["pdf_data"]) if isinstance(raw.get("pdf_data"), str) else raw["pdf_data"]
        return FillFormResponse(
            pdf_data=pdf_bytes,
            fields_filled=raw.get("fields_filled", 0),
            flattened=raw.get("flattened", request.flatten),
        )

    async def redact(self, request: RedactRequest) -> RedactResponse:
        """POST /api/v1/redact — redact content from a PDF (Pro tier)."""
        payload: dict[str, object] = {
            "pdf_data": base64.b64encode(request.pdf_data).decode(),
            "patterns": request.patterns,
            "replacement_text": request.replacement_text,
        }
        if request.page_range is not None:
            payload["page_range"] = request.page_range

        response = await self._http.post(
            f"{self._base_url}/api/v1/redact",
            json=payload,
        )
        raise_for_error_response(response)
        raw: dict[str, Any] = response.json()
        pdf_bytes = base64.b64decode(raw["pdf_data"]) if isinstance(raw.get("pdf_data"), str) else raw["pdf_data"]
        return RedactResponse(
            pdf_data=pdf_bytes,
            redaction_count=raw.get("redaction_count", 0),
            pages_processed=raw.get("pages_processed", 0),
        )

    async def compare(self, request: CompareRequest) -> CompareResponse:
        """POST /api/v1/compare — compare two PDFs structurally (Pro tier)."""
        payload: dict[str, object] = {
            "original_pdf_data": base64.b64encode(request.original_pdf_data).decode("ascii"),
            "modified_pdf_data": base64.b64encode(request.modified_pdf_data).decode("ascii"),
            "include_visual_diff": request.include_visual_diff,
        }

        response = await self._http.post(
            f"{self._base_url}/api/v1/compare",
            json=payload,
        )
        raise_for_error_response(response)
        raw: dict[str, Any] = response.json()
        visual_bytes: bytes | None = None
        if raw.get("visual_diff_data"):
            visual_bytes = base64.b64decode(raw["visual_diff_data"])
        return CompareResponse(
            original_page_count=raw.get("original_page_count", 0),
            modified_page_count=raw.get("modified_page_count", 0),
            added_text_count=raw.get("added_text_count", 0),
            removed_text_count=raw.get("removed_text_count", 0),
            changed_text_count=raw.get("changed_text_count", 0),
            visual_diff_data=visual_bytes,
        )

    async def check_accessibility(
        self,
        request: CheckAccessibilityRequest,
    ) -> CheckAccessibilityResponse:
        """POST /api/v1/check-accessibility — PDF/UA accessibility audit (Pro tier)."""
        payload: dict[str, object] = {
            "pdf_data": base64.b64encode(request.pdf_data).decode(),
            "conformance_target": request.conformance_target,
        }

        response = await self._http.post(
            f"{self._base_url}/api/v1/check-accessibility",
            json=payload,
        )
        raise_for_error_response(response)
        raw: dict[str, Any] = response.json()
        issues = [AccessibilityIssue.model_validate(i) for i in raw.get("issues", [])]
        return CheckAccessibilityResponse(
            conformance_target=raw.get("conformance_target", request.conformance_target),
            passed=raw.get("passed", False),
            issues=issues,
            issue_count=raw.get("issue_count", len(issues)),
        )

    async def optimize(self, request: OptimizeRequest) -> OptimizeResponse:
        """POST /api/v1/optimize — optimize PDF for target use-case (Pro tier)."""
        payload: dict[str, object] = {
            "pdf_data": base64.b64encode(request.pdf_data).decode(),
            "target": request.target,
            "remove_metadata": request.remove_metadata,
        }
        if request.max_image_dpi is not None:
            payload["max_image_dpi"] = request.max_image_dpi

        response = await self._http.post(
            f"{self._base_url}/api/v1/optimize",
            json=payload,
        )
        raise_for_error_response(response)
        raw: dict[str, Any] = response.json()
        pdf_bytes = base64.b64decode(raw["pdf_data"]) if isinstance(raw.get("pdf_data"), str) else raw["pdf_data"]
        orig_size = raw.get("original_size_bytes", len(request.pdf_data))
        return OptimizeResponse(
            pdf_data=pdf_bytes,
            original_size_bytes=orig_size,
            optimized_size_bytes=raw.get("optimized_size_bytes", len(pdf_bytes)),
            reduction_percent=raw.get("reduction_percent", 0.0),
        )

    # -- Enterprise operations -------------------------------------------------

    async def compliance_check(
        self,
        request: ComplianceCheckRequest,
    ) -> ComplianceCheckResponse:
        """POST /api/v1/compliance-check — multi-standard compliance audit (Enterprise tier)."""
        payload: dict[str, object] = {
            "pdf_data": base64.b64encode(request.pdf_data).decode(),
            "standards": request.standards,
        }

        response = await self._http.post(
            f"{self._base_url}/api/v1/compliance-check",
            json=payload,
        )
        raise_for_error_response(response)
        raw: dict[str, Any] = response.json()
        violations = [ComplianceViolation.model_validate(v) for v in raw.get("violations", [])]
        return ComplianceCheckResponse(
            passed=raw.get("passed", False),
            standards_checked=raw.get("standards_checked", request.standards),
            violations=violations,
            violation_count=raw.get("violation_count", len(violations)),
            pages_processed=raw.get("pages_processed", 0),
        )

    async def forensic_analyze(
        self,
        request: ForensicAnalyzeRequest,
    ) -> ForensicAnalyzeResponse:
        """POST /api/v1/forensic-analyze — forensic PDF analysis (Enterprise tier)."""
        payload: dict[str, object] = {
            "pdf_data": base64.b64encode(request.pdf_data).decode(),
            "checks": request.checks,
        }

        response = await self._http.post(
            f"{self._base_url}/api/v1/forensic-analyze",
            json=payload,
        )
        raise_for_error_response(response)
        raw: dict[str, Any] = response.json()
        findings = [ForensicFinding.model_validate(f) for f in raw.get("findings", [])]
        return ForensicAnalyzeResponse(
            risk_score=float(raw.get("risk_score", 0.0)),
            findings=findings,
            finding_count=raw.get("finding_count", len(findings)),
            analyzed_at=raw.get("analyzed_at", ""),
        )

    async def ai_certify(self, request: AiCertifyRequest) -> AiCertifyResponse:
        """POST /api/v1/ai-certify — AI-powered PDF certification (Enterprise tier)."""
        payload: dict[str, object] = {
            "pdf_data": base64.b64encode(request.pdf_data).decode(),
            "certification_level": request.certification_level,
            "metadata": request.metadata,
        }

        response = await self._http.post(
            f"{self._base_url}/api/v1/ai-certify",
            json=payload,
        )
        raise_for_error_response(response)
        raw: dict[str, Any] = response.json()
        pdf_bytes = base64.b64decode(raw["pdf_data"]) if isinstance(raw.get("pdf_data"), str) else raw["pdf_data"]
        return AiCertifyResponse(
            certificate_id=raw["certificate_id"],
            certified_at=raw["certified_at"],
            certification_level=raw.get("certification_level", request.certification_level),
            pdf_data=pdf_bytes,
            certificate_fingerprint=raw["certificate_fingerprint"],
        )

    # -- Internal helpers ------------------------------------------------------

    @staticmethod
    def _int_header(response: httpx.Response, header_name: str) -> int | None:
        """Extract an integer HTTP response header, returning None if absent or invalid."""
        val = response.headers.get(header_name)
        if val is not None and val.isdigit():
            return int(val)
        return None
