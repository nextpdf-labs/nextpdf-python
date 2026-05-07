"""Test: RemoteBackend has a method for every server v5.2 endpoint.

Endpoint inventory sourced from server src/Http/Router/:
  CoreRoutes.php    — GET /healthz, GET /readyz,
                      GET /api/v1/capabilities,
                      POST /api/v1/render,
                      POST /api/v1/jobs, GET /api/v1/jobs/{id},
                      GET /api/v1/jobs/{id}/result, DELETE /api/v1/jobs/{id}
  CapabilityRoutes  — POST /api/v1/extract-text, /api/v1/merge, /api/v1/split (core)
                      POST /api/v1/sign, /api/v1/fill-form, /api/v1/redact,
                           /api/v1/compare, /api/v1/check-accessibility,
                           /api/v1/optimize (pro)
                      POST /api/v1/compliance-check, /api/v1/forensic-analyze,
                           /api/v1/ai-certify (enterprise)
  SessionRoutes.php — POST /api/v1/sessions,
                      GET  /api/v1/sessions/{id},
                      DELETE /api/v1/sessions/{id},
                      POST /api/v1/sessions/{id}/pages,
                      POST /api/v1/sessions/{id}/text,
                      POST /api/v1/sessions/{id}/images,
                      POST /api/v1/sessions/{id}/tables,
                      POST /api/v1/sessions/{id}/html,
                      PUT  /api/v1/sessions/{id}/font,
                      POST /api/v1/sessions/{id}/render
  MCP/gRPC — not part of HTTP REST surface; no SDK method required.
"""

import inspect

import pytest

from nextpdf.backends.remote import RemoteBackend


# The full set of RemoteBackend method names we require for v5.2 coverage.
REQUIRED_METHODS: list[str] = [
    # --- AST legacy (v1 endpoints) ---
    "get_document_ast",
    "extract_cited_text",
    "extract_cited_tables",
    "search_ast_nodes",
    "get_ast_node",
    "get_ast_diff",
    # --- System ---
    "health",
    "readyz",
    # --- Capabilities ---
    "get_capabilities",
    # --- Core: render ---
    "render",
    # --- Core: async jobs ---
    "submit_job",
    "get_job_status",
    "get_job_result",
    "cancel_job",
    # --- Core: document operations ---
    "extract_text",
    "merge",
    "split",
    # --- Sessions ---
    "create_session",
    "get_session",
    "destroy_session",
    "session_add_page",
    "session_add_text",
    "session_add_image",
    "session_add_table",
    "session_add_html",
    "session_set_font",
    "session_render",
    # --- Pro operations ---
    "sign",
    "fill_form",
    "redact",
    "compare",
    "check_accessibility",
    "optimize",
    # --- Enterprise operations ---
    "compliance_check",
    "forensic_analyze",
    "ai_certify",
]


@pytest.mark.parametrize("method_name", REQUIRED_METHODS)
def test_remote_backend_has_method(method_name: str) -> None:
    """RemoteBackend must have a callable method for each v5.2 server endpoint."""
    assert hasattr(RemoteBackend, method_name), (
        f"RemoteBackend missing method '{method_name}' — server v5.2 endpoint not covered"
    )
    method = getattr(RemoteBackend, method_name)
    assert callable(method), f"RemoteBackend.{method_name} is not callable"


def test_all_v52_methods_are_coroutines() -> None:
    """All v5.2 endpoint methods on RemoteBackend must be async coroutines."""
    for method_name in REQUIRED_METHODS:
        # Skip lifecycle methods that are intentionally sync
        if method_name in ("close",):
            continue
        method = getattr(RemoteBackend, method_name, None)
        if method is None:
            continue
        assert inspect.iscoroutinefunction(method), (
            f"RemoteBackend.{method_name} should be an async def coroutine"
        )


def test_method_count_at_least_required() -> None:
    """RemoteBackend must expose at least as many public methods as REQUIRED_METHODS."""
    public_methods = [
        name
        for name, m in inspect.getmembers(RemoteBackend, predicate=inspect.isfunction)
        if not name.startswith("_")
    ]
    assert len(public_methods) >= len(REQUIRED_METHODS), (
        f"Expected >= {len(REQUIRED_METHODS)} public methods, found {len(public_methods)}"
    )
