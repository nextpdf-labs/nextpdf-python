"""Tests for get_ast_node and search_ast_nodes (Phase 1.x)."""

from __future__ import annotations

import base64
import inspect
import json

import httpx
import pytest
import respx

from nextpdf import AsyncNextPDF, NextPDF
from nextpdf.models.ast import NodeType

BASE_URL = "https://api.nextpdf.test"
API_KEY = "test-key-phase1x"

PDF_BYTES = b"%PDF-1.4 fake content"

GET_NODE_RESPONSE = {
    "node": {
        "id": "ast:abc123:0:1",
        "type": "heading",
        "page_index": 0,
        "bbox": None,
        "text_content": "Introduction",
        "attributes": {"level": 1},
        "children": [],
    },
    "_meta": {"etag": "deadbeef", "pages_processed": 3},
}

SEARCH_NODES_RESPONSE = {
    "nodes": [
        {
            "id": "ast:abc123:0:2",
            "type": "heading",
            "page_index": 0,
            "bbox": None,
            "text_content": "Chapter 1",
            "attributes": {},
            "children_count": 0,
        }
    ],
    "total_matches": 1,
    "truncated": False,
}


class TestGetAstNodeAsync:
    @respx.mock
    @pytest.mark.asyncio
    async def test_sends_pdf_data_and_node_id(self) -> None:
        """get_ast_node encodes PDF and includes node_id in the request body."""
        route = respx.post(f"{BASE_URL}/v1/ast/node").mock(
            return_value=httpx.Response(200, json=GET_NODE_RESPONSE)
        )

        async with AsyncNextPDF(base_url=BASE_URL, api_key=API_KEY) as client:
            await client.ast.get_ast_node(PDF_BYTES, "ast:abc123:0:1")

        assert route.called
        body = json.loads(route.calls.last.request.content)
        assert body["pdf_data"] == base64.b64encode(PDF_BYTES).decode()
        assert body["node_id"] == "ast:abc123:0:1"

    @respx.mock
    @pytest.mark.asyncio
    async def test_returns_correct_node_type(self) -> None:
        """get_ast_node parses the node type enum correctly."""
        respx.post(f"{BASE_URL}/v1/ast/node").mock(
            return_value=httpx.Response(200, json=GET_NODE_RESPONSE)
        )

        async with AsyncNextPDF(base_url=BASE_URL, api_key=API_KEY) as client:
            result = await client.ast.get_ast_node(PDF_BYTES, "ast:abc123:0:1")

        assert result.node.type == NodeType.HEADING
        assert result.node.id == "ast:abc123:0:1"
        assert result.node.text_content == "Introduction"

    @respx.mock
    @pytest.mark.asyncio
    async def test_parses_meta_etag_and_pages_processed(self) -> None:
        """get_ast_node populates meta from _meta block."""
        respx.post(f"{BASE_URL}/v1/ast/node").mock(
            return_value=httpx.Response(200, json=GET_NODE_RESPONSE)
        )

        async with AsyncNextPDF(base_url=BASE_URL, api_key=API_KEY) as client:
            result = await client.ast.get_ast_node(PDF_BYTES, "ast:abc123:0:1")

        assert result.meta.etag == "deadbeef"
        assert result.meta.pages_processed == 3

    @respx.mock
    @pytest.mark.asyncio
    async def test_meta_defaults_when_no_meta_block(self) -> None:
        """get_ast_node returns default AstNodeMeta when _meta absent."""
        payload_no_meta = {k: v for k, v in GET_NODE_RESPONSE.items() if k != "_meta"}
        respx.post(f"{BASE_URL}/v1/ast/node").mock(
            return_value=httpx.Response(200, json=payload_no_meta)
        )

        async with AsyncNextPDF(base_url=BASE_URL, api_key=API_KEY) as client:
            result = await client.ast.get_ast_node(PDF_BYTES, "ast:abc123:0:1")

        assert result.meta.etag is None
        assert result.meta.pages_processed is None


class TestSearchAstNodesAsync:
    @respx.mock
    @pytest.mark.asyncio
    async def test_sends_pdf_data_and_node_type_filter(self) -> None:
        """search_ast_nodes encodes PDF and sends node_type filter."""
        route = respx.post(f"{BASE_URL}/v1/ast/search").mock(
            return_value=httpx.Response(200, json=SEARCH_NODES_RESPONSE)
        )

        async with AsyncNextPDF(base_url=BASE_URL, api_key=API_KEY) as client:
            await client.ast.search_ast_nodes(PDF_BYTES, node_type="heading")

        assert route.called
        body = json.loads(route.calls.last.request.content)
        assert body["pdf_data"] == base64.b64encode(PDF_BYTES).decode()
        assert body["node_type"] == "heading"

    @respx.mock
    @pytest.mark.asyncio
    async def test_returns_nodes_and_total_matches(self) -> None:
        """search_ast_nodes parses nodes list and total_matches."""
        respx.post(f"{BASE_URL}/v1/ast/search").mock(
            return_value=httpx.Response(200, json=SEARCH_NODES_RESPONSE)
        )

        async with AsyncNextPDF(base_url=BASE_URL, api_key=API_KEY) as client:
            result = await client.ast.search_ast_nodes(PDF_BYTES, node_type="heading")

        assert len(result.nodes) == 1
        assert result.total_matches == 1
        assert result.truncated is False
        assert result.nodes[0].text_content == "Chapter 1"
        assert result.nodes[0].type == NodeType.HEADING

    @respx.mock
    @pytest.mark.asyncio
    async def test_sends_page_index_filter(self) -> None:
        """search_ast_nodes includes page_index when provided."""
        route = respx.post(f"{BASE_URL}/v1/ast/search").mock(
            return_value=httpx.Response(200, json=SEARCH_NODES_RESPONSE)
        )

        async with AsyncNextPDF(base_url=BASE_URL, api_key=API_KEY) as client:
            await client.ast.search_ast_nodes(PDF_BYTES, page_index=2)

        body = json.loads(route.calls.last.request.content)
        assert body["page_index"] == 2
        assert "node_type" not in body

    @respx.mock
    @pytest.mark.asyncio
    async def test_sends_text_query_filter(self) -> None:
        """search_ast_nodes includes text_query when provided."""
        route = respx.post(f"{BASE_URL}/v1/ast/search").mock(
            return_value=httpx.Response(200, json=SEARCH_NODES_RESPONSE)
        )

        async with AsyncNextPDF(base_url=BASE_URL, api_key=API_KEY) as client:
            await client.ast.search_ast_nodes(PDF_BYTES, text_query="introduction")

        body = json.loads(route.calls.last.request.content)
        assert body["text_query"] == "introduction"

    @respx.mock
    @pytest.mark.asyncio
    async def test_sends_max_results(self) -> None:
        """search_ast_nodes sends max_results in payload."""
        route = respx.post(f"{BASE_URL}/v1/ast/search").mock(
            return_value=httpx.Response(200, json=SEARCH_NODES_RESPONSE)
        )

        async with AsyncNextPDF(base_url=BASE_URL, api_key=API_KEY) as client:
            await client.ast.search_ast_nodes(PDF_BYTES, max_results=50)

        body = json.loads(route.calls.last.request.content)
        assert body["max_results"] == 50

    @respx.mock
    @pytest.mark.asyncio
    async def test_meta_parsed_when_present(self) -> None:
        """search_ast_nodes parses _meta when server includes it."""
        payload_with_meta = {
            **SEARCH_NODES_RESPONSE,
            "_meta": {"etag": "cafe", "pages_processed": 1},
        }
        respx.post(f"{BASE_URL}/v1/ast/search").mock(
            return_value=httpx.Response(200, json=payload_with_meta)
        )

        async with AsyncNextPDF(base_url=BASE_URL, api_key=API_KEY) as client:
            result = await client.ast.search_ast_nodes(PDF_BYTES)

        assert result.meta.etag == "cafe"
        assert result.meta.pages_processed == 1

    @respx.mock
    @pytest.mark.asyncio
    async def test_meta_defaults_when_no_meta_block(self) -> None:
        """search_ast_nodes has null meta fields when _meta absent."""
        respx.post(f"{BASE_URL}/v1/ast/search").mock(
            return_value=httpx.Response(200, json=SEARCH_NODES_RESPONSE)
        )

        async with AsyncNextPDF(base_url=BASE_URL, api_key=API_KEY) as client:
            result = await client.ast.search_ast_nodes(PDF_BYTES)

        assert result.meta.etag is None
        assert result.meta.pages_processed is None


class TestGetAstNodeSync:
    @respx.mock
    def test_sync_get_ast_node_returns_correct_node(self) -> None:
        """Sync get_ast_node delegates correctly and returns node."""
        respx.post(f"{BASE_URL}/v1/ast/node").mock(
            return_value=httpx.Response(200, json=GET_NODE_RESPONSE)
        )

        client = NextPDF(base_url=BASE_URL, api_key=API_KEY)
        result = client.ast.get_ast_node(PDF_BYTES, "ast:abc123:0:1")

        assert result.node.type == NodeType.HEADING
        assert result.meta.etag == "deadbeef"


class TestSearchAstNodesSync:
    @respx.mock
    def test_sync_search_ast_nodes_returns_results(self) -> None:
        """Sync search_ast_nodes delegates correctly and returns nodes."""
        respx.post(f"{BASE_URL}/v1/ast/search").mock(
            return_value=httpx.Response(200, json=SEARCH_NODES_RESPONSE)
        )

        client = NextPDF(base_url=BASE_URL, api_key=API_KEY)
        result = client.ast.search_ast_nodes(PDF_BYTES, node_type="heading")

        assert len(result.nodes) == 1
        assert result.nodes[0].text_content == "Chapter 1"

    def test_search_defaults_max_results_100(self) -> None:
        """Default max_results is 100 in the method signature."""
        client = NextPDF(base_url="https://x.test", api_key="key")
        sig = inspect.signature(client.ast.search_ast_nodes)
        assert sig.parameters["max_results"].default == 100
