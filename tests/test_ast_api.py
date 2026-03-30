from __future__ import annotations

import base64
import json

import httpx
import pytest
import respx

from nextpdf import AsyncNextPDF, NextPDF
from nextpdf.models.errors import (
    AstBuildTimeoutError,
    AstNoStructTreeError,
    NextPDFLicenseError,
    QuotaExceededError,
)

BASE_URL = "https://api.nextpdf.test"
API_KEY = "test-key-abc"

AST_RESPONSE = {
    "schemaVersion": "1.0",
    "sourceHash": "deadbeef",
    "pageCount": 1,
    "root": {
        "id": "root",
        "type": "document",
        "page_index": 0,
        "text_content": "Hello PDF world",
        "attributes": {},
        "children": [],
    },
}

CITED_TEXT_RESPONSE = {
    "blocks": [
        {
            "text": "First heading",
            "citation": {
                "node_id": "n-1",
                "page_index": 0,
                "bbox": {"x": 0.1, "y": 0.1, "width": 0.8, "height": 0.05},
                "confidence": 0.9,
            },
            "node_type": "heading",
            "depth": 1,
        }
    ]
}


@pytest.fixture
def pdf_bytes(minimal_pdf_bytes: bytes) -> bytes:
    return minimal_pdf_bytes


@respx.mock
@pytest.mark.asyncio
async def test_get_document_ast_sends_correct_post(pdf_bytes: bytes) -> None:
    route = respx.post(f"{BASE_URL}/v1/ast/document").mock(
        return_value=httpx.Response(200, json=AST_RESPONSE)
    )

    async with AsyncNextPDF(base_url=BASE_URL, api_key=API_KEY) as client:
        doc = await client.ast.get_document_ast(pdf_bytes)

    assert route.called
    request_body = json.loads(route.calls.last.request.content)
    assert request_body["pdf_data"] == base64.b64encode(pdf_bytes).decode()
    assert doc.schema_version == "1.0"
    assert doc.page_count == 1


@respx.mock
@pytest.mark.asyncio
async def test_get_document_ast_with_page_range(pdf_bytes: bytes) -> None:
    route = respx.post(f"{BASE_URL}/v1/ast/document").mock(
        return_value=httpx.Response(200, json=AST_RESPONSE)
    )

    async with AsyncNextPDF(base_url=BASE_URL, api_key=API_KEY) as client:
        await client.ast.get_document_ast(pdf_bytes, page_range_start=0, page_range_end=5)

    request_body = json.loads(route.calls.last.request.content)
    assert request_body["page_range_start"] == 0
    assert request_body["page_range_end"] == 5


@respx.mock
@pytest.mark.asyncio
async def test_extract_cited_text_sends_correct_post(pdf_bytes: bytes) -> None:
    route = respx.post(f"{BASE_URL}/v1/ast/extract-cited-text").mock(
        return_value=httpx.Response(200, json=CITED_TEXT_RESPONSE)
    )

    async with AsyncNextPDF(base_url=BASE_URL, api_key=API_KEY) as client:
        blocks = await client.ast.extract_cited_text(pdf_bytes)

    assert route.called
    assert len(blocks) == 1
    assert blocks[0].text == "First heading"


@respx.mock
@pytest.mark.asyncio
async def test_extract_cited_text_headings_only(pdf_bytes: bytes) -> None:
    route = respx.post(f"{BASE_URL}/v1/ast/extract-cited-text").mock(
        return_value=httpx.Response(200, json=CITED_TEXT_RESPONSE)
    )

    async with AsyncNextPDF(base_url=BASE_URL, api_key=API_KEY) as client:
        await client.ast.extract_cited_text(pdf_bytes, headings_only=True)

    request_body = json.loads(route.calls.last.request.content)
    assert request_body["headings_only"] is True


@respx.mock
@pytest.mark.asyncio
async def test_402_raises_license_error(pdf_bytes: bytes) -> None:
    respx.post(f"{BASE_URL}/v1/ast/document").mock(
        return_value=httpx.Response(
            402,
            json={"message": "Pro tier required", "code": "license/tier-required"},
        )
    )

    with pytest.raises(NextPDFLicenseError) as exc_info:
        async with AsyncNextPDF(base_url=BASE_URL, api_key=API_KEY) as client:
            await client.ast.get_document_ast(pdf_bytes)

    assert exc_info.value.status_code == 402


@respx.mock
@pytest.mark.asyncio
async def test_429_raises_quota_exceeded_with_retry_after(pdf_bytes: bytes) -> None:
    respx.post(f"{BASE_URL}/v1/ast/document").mock(
        return_value=httpx.Response(
            429,
            headers={"Retry-After": "60"},
            json={"message": "Quota exceeded"},
        )
    )

    with pytest.raises(QuotaExceededError) as exc_info:
        async with AsyncNextPDF(base_url=BASE_URL, api_key=API_KEY) as client:
            await client.ast.get_document_ast(pdf_bytes)

    assert exc_info.value.status_code == 429
    assert exc_info.value.retry_after == 60


@respx.mock
@pytest.mark.asyncio
async def test_422_no_struct_tree_raises_typed_error(pdf_bytes: bytes) -> None:
    respx.post(f"{BASE_URL}/v1/ast/document").mock(
        return_value=httpx.Response(
            422,
            json={"message": "No struct tree", "code": "ast/no-struct-tree"},
        )
    )

    with pytest.raises(AstNoStructTreeError) as exc_info:
        async with AsyncNextPDF(base_url=BASE_URL, api_key=API_KEY) as client:
            await client.ast.get_document_ast(pdf_bytes)

    assert exc_info.value.status_code == 422


@respx.mock
@pytest.mark.asyncio
async def test_504_build_timeout_raises_typed_error(pdf_bytes: bytes) -> None:
    respx.post(f"{BASE_URL}/v1/ast/document").mock(
        return_value=httpx.Response(
            504,
            json={"message": "Timeout", "code": "ast/build-timeout"},
        )
    )

    with pytest.raises(AstBuildTimeoutError) as exc_info:
        async with AsyncNextPDF(base_url=BASE_URL, api_key=API_KEY) as client:
            await client.ast.get_document_ast(pdf_bytes)

    assert exc_info.value.status_code == 504


@respx.mock
def test_sync_client_get_document_ast(pdf_bytes: bytes) -> None:
    respx.post(f"{BASE_URL}/v1/ast/document").mock(
        return_value=httpx.Response(200, json=AST_RESPONSE)
    )

    client = NextPDF(base_url=BASE_URL, api_key=API_KEY)
    doc = client.ast.get_document_ast(pdf_bytes)
    assert doc.page_count == 1
    assert doc.schema_version == "1.0"


@respx.mock
def test_sync_client_extract_cited_text(pdf_bytes: bytes) -> None:
    respx.post(f"{BASE_URL}/v1/ast/extract-cited-text").mock(
        return_value=httpx.Response(200, json=CITED_TEXT_RESPONSE)
    )

    client = NextPDF(base_url=BASE_URL, api_key=API_KEY)
    blocks = client.ast.extract_cited_text(pdf_bytes)
    assert len(blocks) == 1
    assert blocks[0].citation.node_id == "n-1"
