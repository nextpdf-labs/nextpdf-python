"""Type stubs for nextpdf.models.connect — server v5.2 endpoint models."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel

class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class Tier(str, Enum):
    CORE = "core"
    PRO = "pro"
    ENTERPRISE = "enterprise"

class OperationStatus(str, Enum):
    OK = "ok"
    ERROR = "error"

class HealthResponse(BaseModel):
    status: str
    version: str | None
    uptime_seconds: float | None

class CapabilityEntry(BaseModel):
    name: str
    tier: Tier
    enabled: bool

class CapabilitiesResponse(BaseModel):
    server_version: str | None
    capabilities: list[CapabilityEntry]

class OutputConfig(BaseModel):
    conformance: str | None
    compress: bool
    linearize: bool
    metadata: dict[str, str]

class RenderRequest(BaseModel):
    source: str
    output_config: OutputConfig
    idempotency_key: str | None

class RenderResponse(BaseModel):
    pdf_data: bytes
    page_count: int
    size_bytes: int
    conformance: str | None
    rate_limit_remaining: int | None
    rate_limit_reset_at: str | None

class JobSubmitRequest(BaseModel):
    source: str
    output_config: OutputConfig
    idempotency_key: str | None
    webhook_url: str | None

class JobRecord(BaseModel):
    job_id: str
    status: JobStatus
    created_at: str
    updated_at: str | None
    completed_at: str | None
    page_count: int | None
    error_message: str | None

class JobSubmitResponse(BaseModel):
    job_id: str
    status: JobStatus
    poll_url: str

class JobStatusResponse(BaseModel):
    job: JobRecord
    rate_limit_remaining: int | None

class JobResultResponse(BaseModel):
    pdf_data: bytes
    page_count: int
    size_bytes: int
    conformance: str | None

class CreateSessionRequest(BaseModel):
    output_config: OutputConfig
    ttl_seconds: int

class SessionRecord(BaseModel):
    session_id: str
    created_at: str
    expires_at: str
    page_count: int
    status: str

class SessionResponse(BaseModel):
    session: SessionRecord

class AddPageRequest(BaseModel):
    source: str
    page_number: int | None

class AddTextRequest(BaseModel):
    text: str
    font_size: float | None
    font_family: str | None
    x: float | None
    y: float | None
    page_number: int | None

class AddImageRequest(BaseModel):
    image_data: bytes
    x: float
    y: float
    width: float | None
    height: float | None
    page_number: int | None

class AddTableRequest(BaseModel):
    headers: list[str]
    rows: list[list[str]]
    x: float | None
    y: float | None
    page_number: int | None

class AddHtmlRequest(BaseModel):
    html: str
    page_number: int | None

class SetFontRequest(BaseModel):
    family: str
    size: float | None
    bold: bool
    italic: bool

class SessionOperationResponse(BaseModel):
    status: OperationStatus
    session_id: str
    page_count: int

class SessionRenderRequest(BaseModel):
    output_config: OutputConfig

class SessionRenderResponse(BaseModel):
    pdf_data: bytes
    page_count: int
    size_bytes: int
    conformance: str | None

class ExtractTextRequest(BaseModel):
    pdf_data: bytes
    page_index: int | None
    include_formatting: bool

class ExtractTextResponse(BaseModel):
    text: str
    page_count: int
    pages_processed: int

class MergeRequest(BaseModel):
    pdf_files: list[bytes]
    output_config: OutputConfig

class MergeResponse(BaseModel):
    pdf_data: bytes
    page_count: int
    size_bytes: int

class SplitRequest(BaseModel):
    pdf_data: bytes
    split_at_pages: list[int]
    max_pages_per_chunk: int | None

class SplitResponse(BaseModel):
    chunks: list[bytes]
    chunk_page_counts: list[int]

class SignRequest(BaseModel):
    pdf_data: bytes
    certificate_pem: str
    private_key_pem: str
    reason: str | None
    location: str | None
    contact: str | None
    timestamp_url: str | None

class SignResponse(BaseModel):
    pdf_data: bytes
    signature_id: str
    signed_at: str

class FillFormRequest(BaseModel):
    pdf_data: bytes
    fields: dict[str, str | bool | int | float]
    flatten: bool

class FillFormResponse(BaseModel):
    pdf_data: bytes
    fields_filled: int
    flattened: bool

class RedactRequest(BaseModel):
    pdf_data: bytes
    patterns: list[str]
    replacement_text: str
    page_range: dict[str, int] | None

class RedactResponse(BaseModel):
    pdf_data: bytes
    redaction_count: int
    pages_processed: int

class CompareRequest(BaseModel):
    original_pdf_data: bytes
    modified_pdf_data: bytes
    include_visual_diff: bool

class CompareResponse(BaseModel):
    original_page_count: int
    modified_page_count: int
    added_text_count: int
    removed_text_count: int
    changed_text_count: int
    visual_diff_data: bytes | None

class AccessibilityIssue(BaseModel):
    rule_id: str
    severity: str
    page_index: int | None
    description: str
    wcag_criteria: str | None

class CheckAccessibilityRequest(BaseModel):
    pdf_data: bytes
    conformance_target: str

class CheckAccessibilityResponse(BaseModel):
    conformance_target: str
    passed: bool
    issues: list[AccessibilityIssue]
    issue_count: int

class OptimizeRequest(BaseModel):
    pdf_data: bytes
    target: str
    max_image_dpi: int | None
    remove_metadata: bool

class OptimizeResponse(BaseModel):
    pdf_data: bytes
    original_size_bytes: int
    optimized_size_bytes: int
    reduction_percent: float

class ComplianceViolation(BaseModel):
    rule_id: str
    severity: str
    page_index: int | None
    description: str
    standard: str | None

class ComplianceCheckRequest(BaseModel):
    pdf_data: bytes
    standards: list[str]

class ComplianceCheckResponse(BaseModel):
    passed: bool
    standards_checked: list[str]
    violations: list[ComplianceViolation]
    violation_count: int
    pages_processed: int

class ForensicFinding(BaseModel):
    finding_id: str
    category: str
    severity: str
    description: str
    evidence: dict[str, Any]

class ForensicAnalyzeRequest(BaseModel):
    pdf_data: bytes
    checks: list[str]

class ForensicAnalyzeResponse(BaseModel):
    risk_score: float
    findings: list[ForensicFinding]
    finding_count: int
    analyzed_at: str

class AiCertifyRequest(BaseModel):
    pdf_data: bytes
    certification_level: str
    metadata: dict[str, str]

class AiCertifyResponse(BaseModel):
    certificate_id: str
    certified_at: str
    certification_level: str
    pdf_data: bytes
    certificate_fingerprint: str
