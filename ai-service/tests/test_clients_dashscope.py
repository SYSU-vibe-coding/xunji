"""DashScope client unit tests using httpx.MockTransport (no real network)."""

import json

import httpx
import pytest
from app.clients.dashscope import DashScopeClient


def _embedding_response(vectors: list[list[float]]) -> httpx.Response:
    body = {
        "output": {
            "embeddings": [
                {"text_index": idx, "embedding": vec} for idx, vec in enumerate(vectors)
            ]
        },
        "usage": {"total_tokens": 1},
    }
    return httpx.Response(200, content=json.dumps(body))


def _vl_response(text: str) -> httpx.Response:
    body = {
        "output": {
            "choices": [{"message": {"role": "assistant", "content": [{"text": text}]}}]
        }
    }
    return httpx.Response(200, content=json.dumps(body))


@pytest.mark.asyncio
async def test_disabled_when_no_api_key() -> None:
    client = DashScopeClient(api_key="")
    try:
        assert client.enabled is False
        assert await client.text_embedding(["hi"]) is None
        assert await client.vl_understand("http://x", "p") is None
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_text_embedding_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/text-embedding")
        return _embedding_response([[0.1, 0.2], [0.3, 0.4]])

    client = DashScopeClient(api_key="fake", transport=httpx.MockTransport(handler))
    try:
        vecs = await client.text_embedding(["a", "b"])
        assert vecs == [[0.1, 0.2], [0.3, 0.4]]
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_text_embedding_5xx_returns_none() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, content="boom")

    client = DashScopeClient(api_key="fake", transport=httpx.MockTransport(handler))
    try:
        assert await client.text_embedding(["x"]) is None
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_text_embedding_count_mismatch_returns_none() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _embedding_response([[0.1]])  # only 1 vector for 2 inputs

    client = DashScopeClient(api_key="fake", transport=httpx.MockTransport(handler))
    try:
        assert await client.text_embedding(["a", "b"]) is None
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_vl_understand_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _vl_response("CERT")

    client = DashScopeClient(api_key="fake", transport=httpx.MockTransport(handler))
    try:
        reply = await client.vl_understand("http://img", "classify please")
        assert reply == "CERT"
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_vl_understand_string_content() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = {"output": {"choices": [{"message": {"content": "ELECTRONIC"}}]}}
        return httpx.Response(200, content=json.dumps(body))

    client = DashScopeClient(api_key="fake", transport=httpx.MockTransport(handler))
    try:
        assert await client.vl_understand("http://img", "?") == "ELECTRONIC"
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_vl_understand_timeout_returns_none() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("simulated", request=request)

    client = DashScopeClient(api_key="fake", transport=httpx.MockTransport(handler))
    try:
        assert await client.vl_understand("http://img", "?") is None
    finally:
        await client.aclose()
