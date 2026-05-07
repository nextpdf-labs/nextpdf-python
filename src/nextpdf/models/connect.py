"""Pydantic v2 models for NextPDF Connect API v5.2 server endpoints.

Covers:
  - Core:       /api/v1/render, /api/v1/jobs/*, /api/v1/capabilities
  - Sessions:   /api/v1/sessions/*
  - Pro:        /api/v1/sign, /api/v1/fill-form, /api/v1/redact,
                /api/v1/compare, /api/v1/check-accessibility, /api/v1/optimize
  - Enterprise: /api/v1/compliance-check, /api/v1/forensic-analyze,
                /api/v1/ai-certify
  - System:     GET /healthz, GET /readyz

RAG anchors (D5 Cycle 5):
  cyclonedx_1_7_json_reference#x1.x65.x8.p24  — version MUST semver
  owasp_top10_2025#x3.p24                      — rate limit API access
  php_manual#x10252.p34                        — json_encode cross-language

OWASP A05 guidance: all tier fields default to None; caller must validate
before assuming capability availability (no insecure default assumption).
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Shared enumerations
# ---------------------------------------------------------------------------


class JobStatus(str, Enum):
    """Status of an async render job."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Tier(str, Enum):
    """Server capability tier."""

    CORE = "core"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class OperationStatus(str, Enum):
    """Status of an operation response."""

    OK = "ok"
    ERROR = "error"


# ---------------------------------------------------------------------------
# Health endpoints  GET /healthz  GET /readyz
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    """Response from GET /healthz or GET /readyz."""

    model_config = ConfigDict(frozen=True)

    status: str
    version: str | None = None
    uptime_seconds: float | None = None


# ---------------------------------------------------------------------------
# Capabilities  GET /api/v1/capabilities
# ---------------------------------------------------------------------------


class CapabilityEntry(BaseModel):
    """A single server capability descriptor."""

    model_config = ConfigDict(frozen=True)

    name: str
    tier: Tier
    enabled: bool


class CapabilitiesResponse(BaseModel):
    """Response from GET /api/v1/capabilities."""

    model_config = ConfigDict(frozen=True)

    server_version: str | None = None
    capabilities: list[CapabilityEntry] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Render  POST /api/v1/render
# ---------------------------------------------------------------------------


class OutputConfig(BaseModel):
    """PDF output configuration for render requests."""

    model_config = ConfigDict(frozen=True)

    conformance: str | None = None
    """PDF/A or PDF/UA conformance level, e.g. 'PDF/A-3b'."""
    compress: bool = True
    linearize: bool = False
    metadata: dict[str, str] = Field(default_factory=dict)


class RenderRequest(BaseModel):
    """Request body for POST /api/v1/render (synchronous render)."""

    source: str
    """HTML or Markdown source content to render."""
    output_config: OutputConfig = Field(default_factory=OutputConfig)
    idempotency_key: str | None = None


class RenderResponse(BaseModel):
    """Response from POST /api/v1/render."""

    model_config = ConfigDict(frozen=True)

    pdf_data: bytes
    """Raw PDF bytes (base64-decoded from response)."""
    page_count: int
    size_bytes: int
    conformance: str | None = None
    rate_limit_remaining: int | None = None
    rate_limit_reset_at: str | None = None


# ---------------------------------------------------------------------------
# Async Jobs  POST/GET/DELETE /api/v1/jobs/*
# ---------------------------------------------------------------------------


class JobSubmitRequest(BaseModel):
    """Request body for POST /api/v1/jobs (submit async render job)."""

    source: str
    output_config: OutputConfig = Field(default_factory=OutputConfig)
    idempotency_key: str | None = None
    webhook_url: str | None = None


class JobRecord(BaseModel):
    """Metadata record for an async render job."""

    model_config = ConfigDict(frozen=True)

    job_id: str
    status: JobStatus
    created_at: str
    updated_at: str | None = None
    completed_at: str | None = None
    page_count: int | None = None
    error_message: str | None = None


class JobSubmitResponse(BaseModel):
    """Response from POST /api/v1/jobs."""

    model_config = ConfigDict(frozen=True)

    job_id: str
    status: JobStatus
    poll_url: str


class JobStatusResponse(BaseModel):
    """Response from GET /api/v1/jobs/{id}."""

    model_config = ConfigDict(frozen=True)

    job: JobRecord
    rate_limit_remaining: int | None = None


class JobResultResponse(BaseModel):
    """Response from GET /api/v1/jobs/{id}/result."""

    model_config = ConfigDict(frozen=True)

    pdf_data: bytes
    page_count: int
    size_bytes: int
    conformance: str | None = None


# ---------------------------------------------------------------------------
# Sessions  POST/GET/DELETE /api/v1/sessions/*
# ---------------------------------------------------------------------------


class CreateSessionRequest(BaseModel):
    """Request body for POST /api/v1/sessions."""

    output_config: OutputConfig = Field(default_factory=OutputConfig)
    ttl_seconds: int = Field(default=3600, ge=60, le=86400)


class SessionRecord(BaseModel):
    """Session metadata record."""

    model_config = ConfigDict(frozen=True)

    session_id: str
    created_at: str
    expires_at: str
    page_count: int = 0
    status: str = "active"


class SessionResponse(BaseModel):
    """Response from POST /api/v1/sessions or GET /api/v1/sessions/{id}."""

    model_config = ConfigDict(frozen=True)

    session: SessionRecord


class AddPageRequest(BaseModel):
    """Request body for POST /api/v1/sessions/{id}/pages."""

    source: str
    page_number: int | None = None


class AddTextRequest(BaseModel):
    """Request body for POST /api/v1/sessions/{id}/text."""

    text: str
    font_size: float | None = None
    font_family: str | None = None
    x: float | None = None
    y: float | None = None
    page_number: int | None = None


class AddImageRequest(BaseModel):
    """Request body for POST /api/v1/sessions/{id}/images."""

    image_data: bytes
    x: float = 0.0
    y: float = 0.0
    width: float | None = None
    height: float | None = None
    page_number: int | None = None


class AddTableRequest(BaseModel):
    """Request body for POST /api/v1/sessions/{id}/tables."""

    headers: list[str]
    rows: list[list[str]]
    x: float | None = None
    y: float | None = None
    page_number: int | None = None


class AddHtmlRequest(BaseModel):
    """Request body for POST /api/v1/sessions/{id}/html."""

    html: str
    page_number: int | None = None


class SetFontRequest(BaseModel):
    """Request body for PUT /api/v1/sessions/{id}/font."""

    family: str
    size: float | None = None
    bold: bool = False
    italic: bool = False


class SessionOperationResponse(BaseModel):
    """Generic response for session mutation operations."""

    model_config = ConfigDict(frozen=True)

    status: OperationStatus
    session_id: str
    page_count: int


class SessionRenderRequest(BaseModel):
    """Request body for POST /api/v1/sessions/{id}/render."""

    output_config: OutputConfig = Field(default_factory=OutputConfig)


class SessionRenderResponse(BaseModel):
    """Response from POST /api/v1/sessions/{id}/render."""

    model_config = ConfigDict(frozen=True)

    pdf_data: bytes
    page_count: int
    size_bytes: int
    conformance: str | None = None


# ---------------------------------------------------------------------------
# Core operations
# ---------------------------------------------------------------------------


class ExtractTextRequest(BaseModel):
    """Request body for POST /api/v1/extract-text."""

    pdf_data: bytes
    page_index: int | None = None
    include_formatting: bool = False


class ExtractTextResponse(BaseModel):
    """Response from POST /api/v1/extract-text."""

    model_config = ConfigDict(frozen=True)

    text: str
    page_count: int
    pages_processed: int


class MergeRequest(BaseModel):
    """Request body for POST /api/v1/merge."""

    pdf_files: list[bytes]
    output_config: OutputConfig = Field(default_factory=OutputConfig)


class MergeResponse(BaseModel):
    """Response from POST /api/v1/merge."""

    model_config = ConfigDict(frozen=True)

    pdf_data: bytes
    page_count: int
    size_bytes: int


class SplitRequest(BaseModel):
    """Request body for POST /api/v1/split."""

    pdf_data: bytes
    split_at_pages: list[int] = Field(default_factory=list)
    """0-based page indices at which to split. Empty = split every page."""
    max_pages_per_chunk: int | None = None


class SplitResponse(BaseModel):
    """Response from POST /api/v1/split."""

    model_config = ConfigDict(frozen=True)

    chunks: list[bytes]
    chunk_page_counts: list[int]


# ---------------------------------------------------------------------------
# Pro operations (tier=pro)
# ---------------------------------------------------------------------------


class SignRequest(BaseModel):
    """Request body for POST /api/v1/sign (Pro tier)."""

    pdf_data: bytes
    certificate_pem: str
    private_key_pem: str
    reason: str | None = None
    location: str | None = None
    contact: str | None = None
    timestamp_url: str | None = None


class SignResponse(BaseModel):
    """Response from POST /api/v1/sign."""

    model_config = ConfigDict(frozen=True)

    pdf_data: bytes
    signature_id: str
    signed_at: str


class FillFormRequest(BaseModel):
    """Request body for POST /api/v1/fill-form (Pro tier)."""

    pdf_data: bytes
    fields: dict[str, str | bool | int | float]
    flatten: bool = False


class FillFormResponse(BaseModel):
    """Response from POST /api/v1/fill-form."""

    model_config = ConfigDict(frozen=True)

    pdf_data: bytes
    fields_filled: int
    flattened: bool


class RedactRequest(BaseModel):
    """Request body for POST /api/v1/redact (Pro tier)."""

    pdf_data: bytes
    patterns: list[str]
    """Regex patterns or literal strings to redact."""
    replacement_text: str = "[REDACTED]"
    page_range: dict[str, int] | None = None


class RedactResponse(BaseModel):
    """Response from POST /api/v1/redact."""

    model_config = ConfigDict(frozen=True)

    pdf_data: bytes
    redaction_count: int
    pages_processed: int


class CompareRequest(BaseModel):
    """Request body for POST /api/v1/compare (Pro tier)."""

    original_pdf_data: bytes
    modified_pdf_data: bytes
    include_visual_diff: bool = False


class CompareResponse(BaseModel):
    """Response from POST /api/v1/compare."""

    model_config = ConfigDict(frozen=True)

    original_page_count: int
    modified_page_count: int
    added_text_count: int
    removed_text_count: int
    changed_text_count: int
    visual_diff_data: bytes | None = None


class AccessibilityIssue(BaseModel):
    """A single accessibility finding."""

    model_config = ConfigDict(frozen=True)

    rule_id: str
    severity: str
    page_index: int | None = None
    description: str
    wcag_criteria: str | None = None


class CheckAccessibilityRequest(BaseModel):
    """Request body for POST /api/v1/check-accessibility (Pro tier)."""

    pdf_data: bytes
    conformance_target: str = "PDF/UA-1"


class CheckAccessibilityResponse(BaseModel):
    """Response from POST /api/v1/check-accessibility."""

    model_config = ConfigDict(frozen=True)

    conformance_target: str
    passed: bool
    issues: list[AccessibilityIssue] = Field(default_factory=list)
    issue_count: int


class OptimizeRequest(BaseModel):
    """Request body for POST /api/v1/optimize (Pro tier)."""

    pdf_data: bytes
    target: str = "web"
    """Optimization target: 'web', 'print', 'archive'."""
    max_image_dpi: int | None = None
    remove_metadata: bool = False


class OptimizeResponse(BaseModel):
    """Response from POST /api/v1/optimize."""

    model_config = ConfigDict(frozen=True)

    pdf_data: bytes
    original_size_bytes: int
    optimized_size_bytes: int
    reduction_percent: float


# ---------------------------------------------------------------------------
# Enterprise operations (tier=enterprise)
# ---------------------------------------------------------------------------


class ComplianceViolation(BaseModel):
    """A single compliance finding."""

    model_config = ConfigDict(frozen=True)

    rule_id: str
    severity: str
    page_index: int | None = None
    description: str
    standard: str | None = None


class ComplianceCheckRequest(BaseModel):
    """Request body for POST /api/v1/compliance-check (Enterprise tier)."""

    pdf_data: bytes
    standards: list[str] = Field(default_factory=lambda: ["PDF/A-3b"])
    """Standards to check against, e.g. ['PDF/A-3b', 'WCAG-2.1']."""


class ComplianceCheckResponse(BaseModel):
    """Response from POST /api/v1/compliance-check."""

    model_config = ConfigDict(frozen=True)

    passed: bool
    standards_checked: list[str]
    violations: list[ComplianceViolation] = Field(default_factory=list)
    violation_count: int
    pages_processed: int


class ForensicFinding(BaseModel):
    """A single forensic analysis finding."""

    model_config = ConfigDict(frozen=True)

    finding_id: str
    category: str
    severity: str
    description: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class ForensicAnalyzeRequest(BaseModel):
    """Request body for POST /api/v1/forensic-analyze (Enterprise tier)."""

    pdf_data: bytes
    checks: list[str] = Field(default_factory=lambda: ["metadata", "javascript", "embedded_files"])


class ForensicAnalyzeResponse(BaseModel):
    """Response from POST /api/v1/forensic-analyze."""

    model_config = ConfigDict(frozen=True)

    risk_score: float = Field(ge=0.0, le=1.0)
    findings: list[ForensicFinding] = Field(default_factory=list)
    finding_count: int
    analyzed_at: str


class AiCertifyRequest(BaseModel):
    """Request body for POST /api/v1/ai-certify (Enterprise tier)."""

    pdf_data: bytes
    certification_level: str = "standard"
    """Certification level: 'standard', 'enhanced', 'premium'."""
    metadata: dict[str, str] = Field(default_factory=dict)


class AiCertifyResponse(BaseModel):
    """Response from POST /api/v1/ai-certify."""

    model_config = ConfigDict(frozen=True)

    certificate_id: str
    certified_at: str
    certification_level: str
    pdf_data: bytes
    """PDF with embedded certification."""
    certificate_fingerprint: str
